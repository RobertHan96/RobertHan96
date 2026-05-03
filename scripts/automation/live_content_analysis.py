#!/usr/bin/env python3
from __future__ import annotations

"""라이브 transcript 기반 주제/챕터/숏츠 후보 분석"""

import json
import os
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

try:
    from .live_pipeline_config import resolve_openai_model
except ImportError:
    from live_pipeline_config import resolve_openai_model

MAX_TRANSCRIPT_CHARS = 32000


def extract_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", "") or ""
    if output_text:
        return output_text.strip()
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", []) or []:
            if getattr(part, "type", None) == "output_text":
                return getattr(part, "text", "").strip()
    return ""


def _slug_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def build_timeline_chunks(words: list[dict[str, Any]], chunk_seconds: int = 30) -> list[dict[str, Any]]:
    if not words:
        return []
    chunks: list[dict[str, Any]] = []
    current_words: list[str] = []
    chunk_start = int(float(words[0].get("start", 0)))
    chunk_end = chunk_start + chunk_seconds

    for word in words:
        text = str(word.get("text", "")).strip()
        if not text:
            continue
        start = int(float(word.get("start", 0)))
        end = int(float(word.get("end", start)))
        if start >= chunk_end and current_words:
            chunks.append({
                "start_seconds": chunk_start,
                "end_seconds": chunk_end,
                "text": _slug_text(" ".join(current_words)),
            })
            current_words = []
            chunk_start = start
            chunk_end = start + chunk_seconds
        current_words.append(text)
        chunk_end = max(chunk_end, end)

    if current_words:
        chunks.append({
            "start_seconds": chunk_start,
            "end_seconds": chunk_end,
            "text": _slug_text(" ".join(current_words)),
        })
    return chunks


def _extract_json_block(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("분석 응답에서 JSON 본문을 찾지 못했습니다.")
    return json.loads(cleaned[start:end + 1])


def analyze_transcript(recording: dict[str, Any], transcript_payload: dict[str, Any]) -> dict[str, Any]:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = resolve_openai_model()
    words = transcript_payload.get("words") or []
    timeline_chunks = build_timeline_chunks(words)
    transcript_text = str(transcript_payload.get("text", "")).strip()[:MAX_TRANSCRIPT_CHARS]
    timeline_text = "\n".join(
        f"[{chunk['start_seconds']}-{chunk['end_seconds']}] {chunk['text']}"
        for chunk in timeline_chunks[:120]
    )

    prompt = f"""
당신은 AI 엔지니어의 기술 라이브 방송 편집 보조자다.
목표는 방송 내용을 블로그와 숏츠로 재가공하기 쉽게 구조화하는 것이다.

입력 특성:
- 방송 언어는 한국어 위주이며 영어 기술 용어가 섞인다.
- 주제는 AI, 소프트웨어 개발, 라이브러리 실험, 구현 삽질, 문제 해결 경험이다.
- 기술명, 모델명, 라이브러리명은 가능한 한 유지한다.

반드시 JSON만 반환해라.
스키마:
{{
  "title_candidates": ["문자열", "..."],
  "main_topics": ["문자열", "..."],
  "summary": "문자열",
  "chapters": [
    {{"title": "문자열", "start_seconds": 0, "end_seconds": 120, "summary": "문자열"}}
  ],
  "blog_sections": {{
    "배경": "문자열",
    "오늘 다룬 기술": "문자열",
    "구현 흐름": "문자열",
    "막힌 점": "문자열",
    "해결 방법": "문자열",
    "배운 점": "문자열",
    "다음 실험 아이디어": "문자열"
  }},
  "shorts_candidates": [
    {{
      "start_seconds": 0,
      "end_seconds": 45,
      "hook": "문자열",
      "title_candidate": "문자열",
      "summary": "문자열",
      "why_this_clip": "문자열",
      "tts_intro": "문자열"
    }}
  ],
  "keywords": ["문자열", "..."]
}}

녹화 파일명: {recording.get("filename")}
녹화 길이(초): {int(recording.get("duration_seconds") or 0)}

Transcript:
{transcript_text}

Timeline Chunks:
{timeline_text}
"""

    response = client.responses.create(
        model=model,
        input=[{
            "role": "user",
            "content": [{"type": "input_text", "text": prompt}],
        }],
    )
    parsed = _extract_json_block(extract_output_text(response))
    parsed["timeline_chunks"] = timeline_chunks
    return parsed
