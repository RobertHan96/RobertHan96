#!/usr/bin/env python3
from __future__ import annotations

"""라이브 녹화본 스캔 및 ffmpeg/ffprobe 헬퍼"""

import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from .live_pipeline_config import SUPPORTED_VIDEO_EXTENSIONS
except ImportError:
    from live_pipeline_config import SUPPORTED_VIDEO_EXTENSIONS

try:
    import imageio_ffmpeg
except Exception:  # pragma: no cover
    imageio_ffmpeg = None


def resolve_ffmpeg_executable() -> str:
    if imageio_ffmpeg is not None:
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
    return "ffmpeg"


def resolve_ffprobe_executable() -> str:
    return "ffprobe"


def build_recording_id(path: Path) -> str:
    stat = path.stat()
    payload = f"{path.name}|{int(stat.st_mtime)}|{stat.st_size}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def probe_video_metadata(path: Path) -> dict:
    try:
        result = subprocess.run(
            [
                resolve_ffprobe_executable(),
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout or "{}")
        streams = payload.get("streams", [])
        video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
        duration = float(video_stream.get("duration") or payload.get("format", {}).get("duration") or 0)
        return {
            "duration_seconds": duration,
            "width": int(video_stream.get("width") or 0),
            "height": int(video_stream.get("height") or 0),
        }
    except FileNotFoundError:
        return probe_video_metadata_with_ffmpeg(path)


def probe_video_metadata_with_ffmpeg(path: Path) -> dict:
    ffmpeg_executable = resolve_ffmpeg_executable()
    result = subprocess.run(
        [ffmpeg_executable, "-i", str(path)],
        capture_output=True,
        text=True,
    )
    stderr = result.stderr or ""
    duration_seconds = 0.0
    width = 0
    height = 0

    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if duration_match:
        hours = int(duration_match.group(1))
        minutes = int(duration_match.group(2))
        seconds = float(duration_match.group(3))
        duration_seconds = hours * 3600 + minutes * 60 + seconds

    resolution_match = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", stderr)
    if resolution_match:
        width = int(resolution_match.group(1))
        height = int(resolution_match.group(2))

    return {
        "duration_seconds": duration_seconds,
        "width": width,
        "height": height,
    }


def scan_recordings(root: Path) -> list[dict]:
    items = []
    if not root.exists():
        return items
    for path in sorted(root.iterdir(), key=lambda current: current.stat().st_mtime, reverse=True):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
            continue
        metadata = probe_video_metadata(path)
        items.append({
            "recording_id": build_recording_id(path),
            "filename": path.name,
            "path": str(path),
            "recorded_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "size_bytes": path.stat().st_size,
            **metadata,
        })
    return items


def extract_audio_track(video_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            resolve_ffmpeg_executable(),
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "mp3",
            "-ar",
            "44100",
            "-ac",
            "1",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return output_path
