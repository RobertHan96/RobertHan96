#!/usr/bin/env python3
from __future__ import annotations

"""라이브 콘텐츠 파이프라인 표시용 모델/헬퍼"""

from datetime import datetime
from typing import Any


def format_bytes(num_bytes: int | float) -> str:
    value = float(num_bytes or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)}{unit}"
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{int(num_bytes)}B"


def format_duration(seconds: int | float | None) -> str:
    total = int(seconds or 0)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def merge_recording_with_manifest(recording: dict[str, Any], manifest_entry: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(recording)
    manifest_entry = manifest_entry or {}
    merged["status"] = manifest_entry.get("status", {})
    merged["artifacts"] = manifest_entry.get("artifacts", {})
    merged["errors"] = manifest_entry.get("errors", {})
    merged["title_candidates"] = manifest_entry.get("title_candidates", [])
    merged["topics"] = manifest_entry.get("topics", [])
    merged["shorts_candidates"] = manifest_entry.get("shorts_candidates", [])
    merged["updated_at"] = manifest_entry.get("updated_at", "")
    merged["formatted_size"] = format_bytes(merged.get("size_bytes", 0))
    merged["formatted_duration"] = format_duration(merged.get("duration_seconds"))
    return merged


def current_status(entry: dict[str, Any], key: str) -> str:
    return str(entry.get("status", {}).get(key, "pending"))


def iso_now() -> str:
    return datetime.now().astimezone().isoformat()
