#!/usr/bin/env python3
from __future__ import annotations

"""라이브 콘텐츠 파이프라인 오케스트레이션"""

import argparse
import json
from pathlib import Path

try:
    from .live_blog_writer import write_hugo_draft
    from .live_content_analysis import analyze_transcript
    from .live_pipeline_config import DEFAULT_RECORDINGS_DIR, REQUIRED_STABLE_POLLS
    from .live_pipeline_media import extract_audio_track, scan_recordings
    from .live_pipeline_models import merge_recording_with_manifest
    from .live_pipeline_storage import (
        ensure_live_pipeline_dirs,
        find_recording_entry,
        load_manifest,
        load_transcript_payload,
        manifest_path,
        save_analysis_payload,
        save_blog_artifact,
        save_manifest,
        save_shorts_candidates,
        save_transcript_payload,
        update_recording_entry,
        update_recording_status,
        upsert_recording_entry,
    )
    from .live_shorts_pipeline import build_srt_from_words, generate_tts_voiceover, render_short
    from .live_transcribe_elevenlabs import transcribe_with_elevenlabs
except ImportError:
    from live_blog_writer import write_hugo_draft
    from live_content_analysis import analyze_transcript
    from live_pipeline_config import DEFAULT_RECORDINGS_DIR, REQUIRED_STABLE_POLLS
    from live_pipeline_media import extract_audio_track, scan_recordings
    from live_pipeline_models import merge_recording_with_manifest
    from live_pipeline_storage import (
        ensure_live_pipeline_dirs,
        find_recording_entry,
        load_manifest,
        load_transcript_payload,
        manifest_path,
        save_analysis_payload,
        save_blog_artifact,
        save_manifest,
        save_shorts_candidates,
        save_transcript_payload,
        update_recording_entry,
        update_recording_status,
        upsert_recording_entry,
    )
    from live_shorts_pipeline import build_srt_from_words, generate_tts_voiceover, render_short
    from live_transcribe_elevenlabs import transcribe_with_elevenlabs


def _sync_manifest() -> dict:
    recordings = scan_recordings(DEFAULT_RECORDINGS_DIR)
    path = manifest_path()
    manifest = load_manifest(path)
    old_entries = {entry.get("recording_id"): entry for entry in manifest.get("recordings", [])}
    next_entries: list[dict] = []
    for recording in recordings:
        entry = old_entries.get(recording["recording_id"], {})
        merged = {
            **recording,
            "status": entry.get("status", {}),
            "artifacts": entry.get("artifacts", {}),
            "errors": entry.get("errors", {}),
            "title_candidates": entry.get("title_candidates", []),
            "topics": entry.get("topics", []),
            "shorts_candidates": entry.get("shorts_candidates", []),
        }
        next_entries.append(merged)
    manifest["recordings"] = next_entries
    save_manifest(path, manifest)
    return manifest


def get_dashboard_recordings() -> list[dict]:
    manifest = _sync_manifest()
    return [
        merge_recording_with_manifest(entry, entry)
        for entry in manifest.get("recordings", [])
    ]


def get_recording_entry(recording_id: str) -> dict:
    manifest = _sync_manifest()
    entry = find_recording_entry(manifest, recording_id)
    if entry is None:
        raise FileNotFoundError(f"녹화본을 찾지 못했습니다: {recording_id}")
    return entry


def should_skip_auto_pipeline(recording: dict) -> bool:
    transcript_status = str(recording.get("status", {}).get("transcript", "pending"))
    return transcript_status in {"queued", "running", "succeeded"}


def select_stable_recordings(
    recordings: list[dict],
    stability_cache: dict[str, dict],
    *,
    required_stable_polls: int = REQUIRED_STABLE_POLLS,
) -> list[str]:
    ready: list[str] = []
    current_paths = {str(recording.get("path", "")) for recording in recordings if recording.get("path")}

    for stale_path in list(stability_cache.keys()):
        if stale_path not in current_paths:
            stability_cache.pop(stale_path, None)

    for recording in recordings:
        path = str(recording.get("path", "")).strip()
        if not path or should_skip_auto_pipeline(recording):
            continue

        signature = f"{recording.get('recording_id', '')}|{recording.get('size_bytes', 0)}|{recording.get('recorded_at', '')}"
        cached = stability_cache.get(path, {})
        if cached.get("signature") == signature:
            stable_polls = int(cached.get("stable_polls", 0)) + 1
        else:
            stable_polls = 1

        scheduled = bool(cached.get("scheduled")) and cached.get("signature") == signature
        stability_cache[path] = {
            "signature": signature,
            "stable_polls": stable_polls,
            "scheduled": scheduled,
        }

        if not scheduled and stable_polls >= required_stable_polls:
            stability_cache[path]["scheduled"] = True
            ready.append(str(recording["recording_id"]))

    return ready


def run_recording_transcription(recording_id: str) -> dict:
    root = ensure_live_pipeline_dirs()["root"]
    entry = get_recording_entry(recording_id)
    video_path = Path(entry["path"])
    audio_path = root / "recordings" / f"{recording_id}.mp3"
    try:
        update_recording_status(recording_id, "transcript", "running")
        extract_audio_track(video_path, audio_path)
        transcript = transcribe_with_elevenlabs(audio_path)
        transcript_paths = save_transcript_payload(root, recording_id, transcript)

        def _mutator(current: dict) -> None:
            current.setdefault("artifacts", {})
            current["artifacts"]["audio_path"] = str(audio_path)
            current["artifacts"]["transcript_json_path"] = str(transcript_paths["json_path"])
            current["artifacts"]["transcript_text_path"] = str(transcript_paths["text_path"])

        update_recording_entry(recording_id, _mutator)
        update_recording_status(recording_id, "transcript", "succeeded")
        return transcript
    except Exception as exc:
        update_recording_status(recording_id, "transcript", "failed", error=str(exc))
        raise


def run_recording_full_pipeline(recording_id: str) -> dict:
    transcript = run_recording_transcription(recording_id)
    analysis = analyze_recording_topics(recording_id)
    return {
        "recording_id": recording_id,
        "transcript": transcript,
        "analysis": analysis,
    }


def analyze_recording_topics(recording_id: str) -> dict:
    root = ensure_live_pipeline_dirs()["root"]
    entry = get_recording_entry(recording_id)
    transcript = load_transcript_payload(root, recording_id)
    try:
        update_recording_status(recording_id, "analysis", "running")
        analysis = analyze_transcript(entry, transcript)
        analysis_path = save_analysis_payload(root, recording_id, analysis)
        blog_path = write_hugo_draft(recording_id=recording_id, analysis=analysis)
        blog_markdown = Path(blog_path).read_text(encoding="utf-8")
        artifact_blog_path = save_blog_artifact(root, recording_id, blog_markdown)
        candidates_path = save_shorts_candidates(
            root,
            recording_id,
            {"shorts_candidates": analysis.get("shorts_candidates", [])},
        )

        def _mutator(current: dict) -> None:
            current.setdefault("artifacts", {})
            current["artifacts"]["analysis_json_path"] = str(analysis_path)
            current["artifacts"]["blog_post_path"] = str(blog_path)
            current["artifacts"]["blog_artifact_path"] = str(artifact_blog_path)
            current["artifacts"]["shorts_candidates_path"] = str(candidates_path)
            current["title_candidates"] = analysis.get("title_candidates", [])
            current["topics"] = analysis.get("main_topics", [])
            current["shorts_candidates"] = analysis.get("shorts_candidates", [])
            current.setdefault("status", {})["blog_draft"] = "succeeded"

        update_recording_entry(recording_id, _mutator)
        update_recording_status(recording_id, "analysis", "succeeded")
        return analysis
    except Exception as exc:
        update_recording_status(recording_id, "analysis", "failed", error=str(exc))
        raise


def render_shorts_candidate(recording_id: str, candidate_index: int = 0, *, with_tts: bool = False) -> dict:
    root = ensure_live_pipeline_dirs()["root"]
    entry = get_recording_entry(recording_id)
    analysis = json.loads((root / "analysis" / f"{recording_id}.json").read_text(encoding="utf-8"))
    transcript = load_transcript_payload(root, recording_id)
    candidates = analysis.get("shorts_candidates") or []
    if candidate_index >= len(candidates):
        raise IndexError("숏츠 후보 인덱스가 범위를 벗어났습니다.")
    candidate = candidates[candidate_index]
    shorts_dir = root / "shorts" / recording_id
    subtitles_dir = shorts_dir / "subtitles"
    renders_dir = shorts_dir / "renders"
    voiceover_dir = shorts_dir / "voiceover"
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    renders_dir.mkdir(parents=True, exist_ok=True)
    voiceover_dir.mkdir(parents=True, exist_ok=True)

    try:
        update_recording_status(recording_id, "shorts", "running")
        subtitle_text = build_srt_from_words(
            transcript.get("words") or [],
            int(candidate.get("start_seconds", 0)),
            int(candidate.get("end_seconds", 0)),
        )
        subtitle_path = subtitles_dir / f"candidate-{candidate_index + 1}.srt"
        subtitle_path.write_text(subtitle_text, encoding="utf-8")

        voiceover_path = None
        if with_tts and candidate.get("tts_intro"):
            voiceover_path = generate_tts_voiceover(
                str(candidate["tts_intro"]).strip(),
                voiceover_dir / f"candidate-{candidate_index + 1}.mp3",
            )

        output_path = renders_dir / f"candidate-{candidate_index + 1}.mp4"
        render_short(
            Path(entry["path"]),
            output_path,
            int(candidate.get("start_seconds", 0)),
            int(candidate.get("end_seconds", 0)),
            subtitle_path=subtitle_path,
        )

        def _mutator(current: dict) -> None:
            current.setdefault("artifacts", {})
            current["artifacts"]["last_short_render_path"] = str(output_path)
            if voiceover_path is not None:
                current["artifacts"]["last_voiceover_path"] = str(voiceover_path)
            current.setdefault("status", {})["shorts"] = "succeeded"

        update_recording_entry(recording_id, _mutator)
        return {
            "render_path": str(output_path),
            "subtitle_path": str(subtitle_path),
            "voiceover_path": str(voiceover_path) if voiceover_path else "",
        }
    except Exception as exc:
        update_recording_status(recording_id, "shorts", "failed", error=str(exc))
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="로컬 라이브 콘텐츠 파이프라인")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scan", help="최근 녹화본 목록 확인")

    transcribe_parser = subparsers.add_parser("transcribe", help="지정 녹화본 STT 실행")
    transcribe_parser.add_argument("recording_id")

    analyze_parser = subparsers.add_parser("analyze", help="지정 녹화본 주제/블로그/숏츠 후보 생성")
    analyze_parser.add_argument("recording_id")

    render_parser = subparsers.add_parser("render-short", help="지정 숏츠 후보 1차 렌더")
    render_parser.add_argument("recording_id")
    render_parser.add_argument("--candidate-index", type=int, default=0)
    render_parser.add_argument("--with-tts", action="store_true")

    args = parser.parse_args()

    if args.command == "scan":
        print(json.dumps(get_dashboard_recordings(), ensure_ascii=False, indent=2))
    elif args.command == "transcribe":
        print(json.dumps(run_recording_transcription(args.recording_id), ensure_ascii=False, indent=2))
    elif args.command == "analyze":
        print(json.dumps(analyze_recording_topics(args.recording_id), ensure_ascii=False, indent=2))
    elif args.command == "render-short":
        print(json.dumps(
            render_shorts_candidate(args.recording_id, args.candidate_index, with_tts=args.with_tts),
            ensure_ascii=False,
            indent=2,
        ))


if __name__ == "__main__":
    main()
