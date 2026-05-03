#!/usr/bin/env python3
from __future__ import annotations

"""ElevenLabs STT 연동"""

import os
from pathlib import Path
from typing import Any

import requests

try:
    from .live_pipeline_config import DEFAULT_STT_MODEL
except ImportError:
    from live_pipeline_config import DEFAULT_STT_MODEL


def transcribe_with_elevenlabs(audio_path: Path) -> dict[str, Any]:
    api_key = os.environ["ELEVENLABS_API_KEY"]
    model_id = os.environ.get("LIVE_PIPELINE_STT_MODEL", DEFAULT_STT_MODEL)
    keyterms = os.environ.get("LIVE_PIPELINE_STT_KEYTERMS", "").strip()
    data: dict[str, Any] = {"model_id": model_id}
    if keyterms:
        data["keyterms"] = keyterms

    with open(audio_path, "rb") as handle:
        response = requests.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": api_key},
            files={"file": (audio_path.name, handle, "audio/mpeg")},
            data=data,
            timeout=300,
        )
    response.raise_for_status()
    payload = response.json()
    payload.setdefault("text", "")
    payload.setdefault("words", [])
    return payload
