#!/usr/bin/env python3
from __future__ import annotations

"""라이브 콘텐츠 파이프라인 공통 설정"""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONTENT_POSTS_DIR = ROOT_DIR / "content" / "posts"
LIVE_PIPELINE_DIR = ROOT_DIR / "data" / "live_pipeline"
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".m4v", ".webm"}


def load_local_env() -> None:
    """프로젝트 루트의 .env를 읽어 비어 있는 환경변수만 채운다."""
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        cleaned = value.strip().strip("'").strip('"')
        os.environ[key] = cleaned


load_local_env()

DEFAULT_RECORDINGS_DIR = Path(
    os.environ.get("LIVE_PIPELINE_RECORDINGS_DIR", str(Path.home() / "Movies" / "LiveRecordings"))
).expanduser()
DEFAULT_VOICE_ID = os.environ.get("LIVE_PIPELINE_DEFAULT_VOICE_ID", "").strip()
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_STT_MODEL = os.environ.get("LIVE_PIPELINE_STT_MODEL", "scribe_v2").strip() or "scribe_v2"
DEFAULT_TTS_MODEL = os.environ.get("LIVE_PIPELINE_TTS_MODEL", "eleven_multilingual_v2").strip() or "eleven_multilingual_v2"
WATCH_POLL_SECONDS = max(5, int(os.environ.get("LIVE_PIPELINE_WATCH_POLL_SECONDS", "20")))
REQUIRED_STABLE_POLLS = max(2, int(os.environ.get("LIVE_PIPELINE_REQUIRED_STABLE_POLLS", "2")))


def get_output_root() -> Path:
    return Path(
        os.environ.get("LIVE_PIPELINE_OUTPUT_DIR", str(LIVE_PIPELINE_DIR))
    ).expanduser()


def resolve_openai_model() -> str:
    return (
        os.environ.get("OPENAI_MODEL", "").strip()
        or os.environ.get("LIVE_PIPELINE_OPENAI_MODEL", "").strip()
        or DEFAULT_OPENAI_MODEL
    )
