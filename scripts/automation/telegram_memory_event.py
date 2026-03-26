#!/usr/bin/env python3
from __future__ import annotations

"""Cloudflare Worker -> GitHub Actions -> Telegram memory 이벤트 처리"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from telegram_memory import (
    KST,
    SUPPORTED_UPLOAD_EXTENSIONS,
    answer_query,
    extract_text_from_document,
    get_telegram_file_bytes,
    save_temp_bytes,
    send_telegram_message,
    store_document_file,
    store_raw_update,
    store_text_note,
)


def load_github_event_payload() -> dict:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "").strip()
    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH 환경변수가 비어 있습니다.")

    payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    return payload.get("client_payload") or {}


def parse_message_datetime(message: dict) -> str | None:
    timestamp = message.get("date")
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(KST).isoformat()


def build_help_message() -> str:
    return (
        "사용법\n"
        "- 일반 텍스트: 메모로 저장\n"
        "- PDF/txt/md/html/json/docx: RAG 자료로 저장\n"
        "- /ask 질문내용: 저장된 메모/자료를 바탕으로 답변"
    )


def handle_text_message(message: dict) -> str:
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    created_at = parse_message_datetime(message)
    text = (message.get("text") or "").strip()

    if not text:
        return "비어 있는 텍스트는 저장하지 않았습니다."

    if text in {"/start", "/help"}:
        return build_help_message()

    if text.startswith("/ask"):
        query = text[4:].strip()
        if not query:
            return "질문 내용을 함께 보내주세요. 예: /ask 지난주 엔비디아 관련 알림 요약"
        answer, _ = answer_query(query)
        return answer

    stored = store_text_note(
        source="telegram-user",
        title=message.get("caption") or collapse_title(text),
        text=text,
        chat_id=chat_id,
        message_id=message_id,
        created_at=created_at,
    )
    return f"메모 저장 완료: {stored['path']}"


def collapse_title(text: str, limit: int = 60) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact or "Telegram note"
    return compact[: limit - 3].rstrip() + "..."


def handle_document_message(message: dict) -> str:
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    created_at = parse_message_datetime(message)
    document = message["document"]
    file_name = document.get("file_name") or document.get("file_unique_id") or "document"
    suffix = Path(file_name).suffix.lower()

    if suffix not in SUPPORTED_UPLOAD_EXTENSIONS:
        return (
            "지원하지 않는 파일 형식입니다. "
            "현재는 pdf/txt/md/html/json/docx 파일을 저장할 수 있습니다."
        )

    content = get_telegram_file_bytes(document["file_id"])
    temp_path = save_temp_bytes(content, suffix or ".bin")
    try:
        extracted_text = extract_text_from_document(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)

    if not extracted_text.strip():
        return f"파일은 받았지만 텍스트를 추출하지 못했습니다: {file_name}"

    stored = store_document_file(
        source="telegram-user",
        original_name=file_name,
        content=content,
        extracted_text=extracted_text,
        chat_id=chat_id,
        message_id=message_id,
        caption=message.get("caption", ""),
        created_at=created_at,
    )
    return f"자료 저장 완료: {stored['text_path']}"


def main() -> None:
    payload = load_github_event_payload()
    update = payload.get("update") or {}
    if not update:
        raise RuntimeError("repository_dispatch payload에 update가 없습니다.")

    store_raw_update(update)
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    try:
        if message.get("document"):
            reply = handle_document_message(message)
        elif message.get("text"):
            reply = handle_text_message(message)
        else:
            reply = build_help_message()
    except Exception as exc:
        reply = f"처리 중 오류가 발생했습니다: {exc}"

    send_telegram_message(chat_id, reply)


if __name__ == "__main__":
    main()
