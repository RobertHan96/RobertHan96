#!/usr/bin/env python3
from __future__ import annotations

"""로컬 라이브 콘텐츠 파이프라인 대시보드"""

from concurrent.futures import ThreadPoolExecutor
import threading
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.automation.live_content_pipeline import (
    analyze_recording_topics,
    get_dashboard_recordings,
    get_recording_entry,
    render_shorts_candidate,
    run_recording_transcription,
)
from scripts.automation.live_pipeline_storage import update_recording_status

app = FastAPI(title="Live Content Dashboard")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

ACTIVE_STATUSES = {"queued", "running"}
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="live-content-dashboard")
_active_jobs: set[tuple[str, str]] = set()
_active_jobs_lock = threading.Lock()
ARTIFACT_KEY_MAP = {
    "blog-post": "blog_post_path",
    "blog-artifact": "blog_artifact_path",
    "short-render": "last_short_render_path",
    "transcript-text": "transcript_text_path",
    "transcript-json": "transcript_json_path",
    "analysis-json": "analysis_json_path",
    "shorts-candidates": "shorts_candidates_path",
}


def _has_active_jobs(recordings: list[dict[str, Any]]) -> bool:
    return any(
        status in ACTIVE_STATUSES
        for recording in recordings
        for status in recording.get("status", {}).values()
    )


def _task_key(recording_id: str, status_key: str) -> tuple[str, str]:
    return (recording_id, status_key)


def enqueue_pipeline_task(
    recording_id: str,
    status_key: str,
    task: Callable[[], Any],
    *,
    success_message: str,
) -> tuple[bool, str]:
    job_key = _task_key(recording_id, status_key)
    with _active_jobs_lock:
        if job_key in _active_jobs:
            return False, "이미 실행 중인 작업입니다."
        _active_jobs.add(job_key)

    update_recording_status(recording_id, status_key, "queued")

    def _runner() -> None:
        try:
            task()
        except Exception:
            # 각 파이프라인 함수가 상태/에러를 직접 기록하므로 여기서는 중복 처리하지 않는다.
            pass
        finally:
            with _active_jobs_lock:
                _active_jobs.discard(job_key)

    _executor.submit(_runner)
    return True, success_message


def resolve_recording_artifact(recording_id: str, artifact_key: str) -> Path:
    artifact_field = ARTIFACT_KEY_MAP.get(artifact_key)
    if artifact_field is None:
        raise HTTPException(status_code=404, detail="알 수 없는 산출물입니다.")
    entry = get_recording_entry(recording_id)
    path_value = str(entry.get("artifacts", {}).get(artifact_field, "")).strip()
    if not path_value:
        raise HTTPException(status_code=404, detail="아직 생성되지 않은 산출물입니다.")
    path = Path(path_value)
    if not path.exists():
        raise HTTPException(status_code=404, detail="산출물 파일을 찾지 못했습니다.")
    return path


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, flash: str = "", level: str = "info") -> HTMLResponse:
    recordings = get_dashboard_recordings()
    return templates.TemplateResponse(
        request,
        "live_content_dashboard.html",
        {
            "recordings": recordings,
            "flash": flash,
            "level": level,
            "has_active_jobs": _has_active_jobs(recordings),
        },
    )


@app.get("/recordings/{recording_id}/artifacts/{artifact_key}")
async def get_artifact(recording_id: str, artifact_key: str) -> FileResponse:
    path = resolve_recording_artifact(recording_id, artifact_key)
    media_type = None
    if path.suffix.lower() == ".md":
        media_type = "text/markdown; charset=utf-8"
    elif path.suffix.lower() == ".json":
        media_type = "application/json"
    elif path.suffix.lower() == ".txt":
        media_type = "text/plain; charset=utf-8"
    elif path.suffix.lower() == ".srt":
        media_type = "text/plain; charset=utf-8"
    elif path.suffix.lower() == ".mp4":
        media_type = "video/mp4"
    return FileResponse(path, media_type=media_type, filename=path.name)


@app.post("/recordings/{recording_id}/reveal/{artifact_key}")
async def reveal_artifact(recording_id: str, artifact_key: str) -> RedirectResponse:
    try:
        path = resolve_recording_artifact(recording_id, artifact_key)
        subprocess.run(["open", "-R", str(path)], check=False)
        return RedirectResponse(url=f"/?flash={quote('Finder에서 파일 위치를 열었습니다.')}&level=success", status_code=303)
    except Exception as exc:
        return RedirectResponse(url=f"/?flash={quote(str(exc))}&level=error", status_code=303)


@app.post("/recordings/{recording_id}/transcribe")
async def transcribe_recording(recording_id: str) -> RedirectResponse:
    try:
        scheduled, message = enqueue_pipeline_task(
            recording_id,
            "transcript",
            lambda: run_recording_transcription(recording_id),
            success_message="STT 작업을 시작했습니다.",
        )
        level = "success" if scheduled else "info"
        return RedirectResponse(url=f"/?flash={quote(message)}&level={level}", status_code=303)
    except Exception as exc:
        return RedirectResponse(url=f"/?flash={quote(str(exc))}&level=error", status_code=303)


@app.post("/recordings/{recording_id}/analyze")
async def analyze_recording(recording_id: str) -> RedirectResponse:
    try:
        scheduled, message = enqueue_pipeline_task(
            recording_id,
            "analysis",
            lambda: analyze_recording_topics(recording_id),
            success_message="AI 주제 분석을 시작했습니다.",
        )
        level = "success" if scheduled else "info"
        return RedirectResponse(url=f"/?flash={quote(message)}&level={level}", status_code=303)
    except Exception as exc:
        return RedirectResponse(url=f"/?flash={quote(str(exc))}&level=error", status_code=303)


@app.post("/recordings/{recording_id}/render-short/{candidate_index}")
async def render_short(recording_id: str, candidate_index: int) -> RedirectResponse:
    try:
        scheduled, message = enqueue_pipeline_task(
            recording_id,
            "shorts",
            lambda: render_shorts_candidate(recording_id, candidate_index),
            success_message="숏츠 1차 렌더를 시작했습니다.",
        )
        level = "success" if scheduled else "info"
        return RedirectResponse(url=f"/?flash={quote(message)}&level={level}", status_code=303)
    except Exception as exc:
        return RedirectResponse(url=f"/?flash={quote(str(exc))}&level=error", status_code=303)
