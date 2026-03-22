#!/usr/bin/env python3
from __future__ import annotations

"""Serverless/Cloud Run 배포용 Telegram RAG webhook 앱"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

import requests
from fastapi import FastAPI, Header, HTTPException, Request

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.automation.investment_rag import (
    SUPPORTED_DIRECT_EXTENSIONS,
    create_temp_markdown,
    extract_file_citations,
    extract_output_text,
    ocr_image_to_markdown,
    query_investment_rag,
    upsert_document,
)

app = FastAPI(title="Investment Telegram RAG")

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_WEBHOOK_SECRET_TOKEN = os.environ["TELEGRAM_WEBHOOK_SECRET_TOKEN"]
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_FILE_BASE = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"


def build_telegram_relative_key(file_unique_id: str, file_name: str, suffix: str) -> str:
    """Telegram 업로드용 상대 경로 생성"""
    safe_name = Path(file_name).name or file_unique_id
    safe_stem = Path(safe_name).stem.replace("/", "-").replace("\\", "-")
    safe_suffix = suffix or Path(safe_name).suffix or ".bin"
    return f"telegram/{file_unique_id}-{safe_stem}{safe_suffix}"


def telegram_api(method: str, payload: dict[str, Any]) -> dict:
    """Telegram Bot API 호출"""
    response = requests.post(f"{TELEGRAM_API_BASE}/{method}", json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


def send_message(chat_id: int | str, text: str) -> None:
    """Telegram 메시지 전송"""
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    })


def get_file_download_url(file_id: str) -> str:
    """Telegram file_id로 다운로드 URL 조회"""
    result = telegram_api("getFile", {"file_id": file_id})
    file_path = result["result"]["file_path"]
    return f"{TELEGRAM_FILE_BASE}/{file_path}"


def download_telegram_file(file_id: str, suffix: str) -> Path:
    """Telegram 파일 다운로드"""
    url = get_file_download_url(file_id)
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temp.write(response.content)
    temp.flush()
    temp.close()
    return Path(temp.name)


def handle_document_message(message: dict) -> str:
    """PDF/문서 메시지 처리"""
    document = message["document"]
    file_name = document.get("file_name") or document["file_unique_id"]
    file_unique_id = document.get("file_unique_id") or "document"
    suffix = Path(file_name).suffix.lower()
    path = download_telegram_file(document["file_id"], suffix or ".bin")

    try:
        if suffix in SUPPORTED_DIRECT_EXTENSIONS:
            result = upsert_document(
                path,
                relative_key=build_telegram_relative_key(
                    file_unique_id=file_unique_id,
                    file_name=file_name,
                    suffix=suffix or ".bin",
                ),
                attributes={
                    "source": "telegram",
                    "telegram_file_unique_id": file_unique_id,
                    "original_filename": file_name,
                },
            )
            return f"자료 적재 완료: {file_name} ({result['status']})"

        return f"지원하지 않는 문서 형식입니다: {file_name}"
    finally:
        path.unlink(missing_ok=True)


def handle_photo_message(message: dict) -> str:
    """사진 메시지 OCR 후 적재"""
    photos = message.get("photo") or []
    if not photos:
        return "이미지를 찾지 못했습니다."

    largest = photos[-1]
    file_unique_id = largest.get("file_unique_id", "photo")
    path = download_telegram_file(largest["file_id"], ".jpg")
    try:
        ocr_text = ocr_image_to_markdown(path)
        temp_markdown = create_temp_markdown(
            file_unique_id,
            f"# Telegram OCR\n\n{ocr_text}\n",
        )
        try:
            result = upsert_document(
                temp_markdown,
                relative_key=build_telegram_relative_key(
                    file_unique_id=file_unique_id,
                    file_name="telegram-photo",
                    suffix=".ocr.md",
                ),
                attributes={
                    "source": "telegram",
                    "source_type": "image_ocr",
                    "telegram_file_unique_id": file_unique_id,
                },
            )
            return f"이미지 OCR 적재 완료 ({result['status']})"
        finally:
            temp_markdown.unlink(missing_ok=True)
    finally:
        path.unlink(missing_ok=True)


def handle_text_message(message: dict) -> str:
    """질문 텍스트 처리"""
    text = (message.get("text") or "").strip()
    if not text:
        return "질문 텍스트를 찾지 못했습니다."
    if text in {"/start", "/help"}:
        return (
            "텍스트 질문, PDF/문서, 이미지 업로드를 지원합니다.\n"
            "- 질문: 자료를 근거로 답변\n"
            "- PDF/문서: Vector Store에 적재\n"
            "- 이미지: OCR 후 적재"
        )

    response = query_investment_rag(text)
    answer = extract_output_text(response) or "관련 자료에서 답을 찾지 못했습니다."
    citations = extract_file_citations(response)
    if citations:
        answer += "\n\n근거 자료:\n" + "\n".join(f"- {name}" for name in citations[:6])
    return answer


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
) -> dict[str, bool]:
    if x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="invalid secret token")

    update = await request.json()
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    try:
        if message.get("document"):
            reply = handle_document_message(message)
        elif message.get("photo"):
            reply = handle_photo_message(message)
        elif message.get("text"):
            reply = handle_text_message(message)
        else:
            reply = "텍스트 질문, PDF/문서, 이미지 업로드를 지원합니다."
    except Exception as exc:
        reply = f"처리 중 오류가 발생했습니다: {exc}"

    send_message(chat_id, reply[:4000])
    return {"ok": True}
