#!/usr/bin/env python3
from __future__ import annotations

"""숏츠 후보 렌더/TTS 헬퍼"""

import os
import subprocess
from pathlib import Path
from typing import Any

import requests

try:
    from .live_pipeline_config import DEFAULT_TTS_MODEL, DEFAULT_VOICE_ID
except ImportError:
    from live_pipeline_config import DEFAULT_TTS_MODEL, DEFAULT_VOICE_ID

try:
    from .live_pipeline_media import resolve_ffmpeg_executable
except ImportError:
    from live_pipeline_media import resolve_ffmpeg_executable


def build_shorts_ffmpeg_command(
    input_path: str,
    output_path: str,
    start_seconds: int,
    end_seconds: int,
    subtitle_path: str | None = None,
) -> list[str]:
    video_filter = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    if subtitle_path:
        escaped = subtitle_path.replace("\\", "\\\\").replace(":", "\\:")
        video_filter += f",subtitles={escaped}"
    return [
        resolve_ffmpeg_executable(),
        "-y",
        "-ss",
        str(start_seconds),
        "-to",
        str(end_seconds),
        "-i",
        input_path,
        "-vf",
        video_filter,
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]


def generate_tts_voiceover(text: str, output_path: Path, voice_id: str | None = None) -> Path:
    api_key = os.environ["ELEVENLABS_API_KEY"]
    selected_voice_id = voice_id or os.environ.get("LIVE_PIPELINE_DEFAULT_VOICE_ID", "").strip() or DEFAULT_VOICE_ID
    if not selected_voice_id:
        raise RuntimeError("LIVE_PIPELINE_DEFAULT_VOICE_ID 환경변수가 비어 있습니다.")

    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice_id}",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        params={"output_format": "mp3_44100_128"},
        json={
            "text": text,
            "model_id": os.environ.get("LIVE_PIPELINE_TTS_MODEL", DEFAULT_TTS_MODEL),
        },
        timeout=120,
    )
    response.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path


def build_srt_from_words(words: list[dict[str, Any]], start_seconds: int, end_seconds: int) -> str:
    relevant = [
        word for word in words
        if float(word.get("start", 0)) >= start_seconds and float(word.get("end", 0)) <= end_seconds
    ]
    if not relevant:
        return ""

    lines: list[str] = []
    chunk: list[str] = []
    chunk_start = float(relevant[0].get("start", start_seconds))
    chunk_end = chunk_start
    index = 1
    for word in relevant:
        text = str(word.get("text", "")).strip()
        if not text:
            continue
        chunk.append(text)
        chunk_end = float(word.get("end", chunk_end))
        if len(chunk) >= 6 or (chunk_end - chunk_start) >= 3.0:
            lines.append(_render_srt_block(index, chunk_start, chunk_end, " ".join(chunk)))
            index += 1
            chunk = []
            chunk_start = chunk_end
    if chunk:
        lines.append(_render_srt_block(index, chunk_start, chunk_end, " ".join(chunk)))
    return "\n".join(lines).strip() + "\n"


def _render_srt_block(index: int, start: float, end: float, text: str) -> str:
    return f"{index}\n{_format_srt_time(start)} --> {_format_srt_time(end)}\n{text}\n"


def _format_srt_time(value: float) -> str:
    millis = int(round(value * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, remainder = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{remainder:03d}"


def render_short(
    video_path: Path,
    output_path: Path,
    start_seconds: int,
    end_seconds: int,
    subtitle_path: Path | None = None,
) -> Path:
    command = build_shorts_ffmpeg_command(
        input_path=str(video_path),
        output_path=str(output_path),
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        subtitle_path=str(subtitle_path) if subtitle_path else None,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(command, check=True, capture_output=True, text=True)
    return output_path
