#!/usr/bin/env python3
from __future__ import annotations

"""라이브 콘텐츠 파이프라인 상태/산출물 저장"""

import json
from pathlib import Path
from typing import Any

try:
    from .live_pipeline_config import get_output_root
    from .live_pipeline_models import iso_now
except ImportError:
    from live_pipeline_config import get_output_root
    from live_pipeline_models import iso_now


def ensure_live_pipeline_dirs() -> dict[str, Path]:
    root = get_output_root()
    paths = {
        "root": root,
        "recordings": root / "recordings",
        "transcripts": root / "transcripts",
        "analysis": root / "analysis",
        "blog_drafts": root / "blog_drafts",
        "shorts": root / "shorts",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def manifest_path() -> Path:
    return ensure_live_pipeline_dirs()["recordings"] / "manifest.json"


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    target = path or manifest_path()
    if not target.exists():
        return {"recordings": []}
    return json.loads(target.read_text(encoding="utf-8"))


def save_manifest(path: Path | None, payload: dict[str, Any]) -> None:
    target = path or manifest_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_recording_entry(manifest: dict[str, Any], entry: dict[str, Any]) -> None:
    recordings = manifest.setdefault("recordings", [])
    for index, current in enumerate(recordings):
        if current.get("recording_id") == entry.get("recording_id"):
            recordings[index] = entry
            return
    recordings.append(entry)


def find_recording_entry(manifest: dict[str, Any], recording_id: str) -> dict[str, Any] | None:
    for entry in manifest.get("recordings", []):
        if entry.get("recording_id") == recording_id:
            return entry
    return None


def update_recording_entry(recording_id: str, mutator) -> dict[str, Any]:
    path = manifest_path()
    manifest = load_manifest(path)
    entry = find_recording_entry(manifest, recording_id)
    if entry is None:
        entry = {"recording_id": recording_id, "status": {}, "artifacts": {}, "errors": {}}
        manifest.setdefault("recordings", []).append(entry)
    mutator(entry)
    entry["updated_at"] = iso_now()
    save_manifest(path, manifest)
    return entry


def update_recording_status(recording_id: str, key: str, value: str, *, error: str = "") -> dict[str, Any]:
    def _mutator(entry: dict[str, Any]) -> None:
        entry.setdefault("status", {})[key] = value
        entry.setdefault("errors", {})
        if error:
            entry["errors"][key] = error
        else:
            entry["errors"].pop(key, None)

    return update_recording_entry(recording_id, _mutator)


def save_transcript_payload(root: Path, recording_id: str, payload: dict[str, Any]) -> dict[str, Path]:
    transcripts_dir = root / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    json_path = transcripts_dir / f"{recording_id}.json"
    text_path = transcripts_dir / f"{recording_id}.txt"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    text_path.write_text(str(payload.get("text", "")).strip() + "\n", encoding="utf-8")
    return {"json_path": json_path, "text_path": text_path}


def load_transcript_payload(root: Path, recording_id: str) -> dict[str, Any]:
    path = root / "transcripts" / f"{recording_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Transcript not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_analysis_payload(root: Path, recording_id: str, payload: dict[str, Any]) -> Path:
    analysis_dir = root / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    path = analysis_dir / f"{recording_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_analysis_payload(root: Path, recording_id: str) -> dict[str, Any]:
    path = root / "analysis" / f"{recording_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Analysis not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_blog_artifact(root: Path, recording_id: str, markdown: str) -> Path:
    drafts_dir = root / "blog_drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    path = drafts_dir / f"{recording_id}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def save_shorts_candidates(root: Path, recording_id: str, payload: dict[str, Any]) -> Path:
    shorts_dir = root / "shorts" / recording_id
    shorts_dir.mkdir(parents=True, exist_ok=True)
    path = shorts_dir / "candidates.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
