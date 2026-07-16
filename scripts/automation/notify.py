"""텔레그램 알림 공통 모듈"""

import json
import os
import time
import urllib.parse
import urllib.request

try:
    from .runtime import get_required_env
except ImportError:
    from runtime import get_required_env

TELEGRAM_MESSAGE_LIMIT = 3800


def maybe_log_outgoing_message(message: str, parse_mode: str) -> None:
    """발송 메시지를 메모리 브리지 또는 로컬 메모리에 적재"""
    source = os.environ.get("TELEGRAM_MEMORY_SOURCE", "").strip() or "telegram-alert"
    try:
        try:
            from .telegram_memory import log_outgoing_message, log_outgoing_message_to_bridge
        except ImportError:
            from telegram_memory import log_outgoing_message, log_outgoing_message_to_bridge

        bridge_url = os.environ.get("TELEGRAM_MEMORY_BRIDGE_URL", "").strip()
        bridge_token = os.environ.get("TELEGRAM_MEMORY_BRIDGE_TOKEN", "").strip()
        if bridge_url and bridge_token:
            log_outgoing_message_to_bridge(source, message, parse_mode=parse_mode)
            return

        enabled = os.environ.get("TELEGRAM_MEMORY_ENABLED", "").strip().lower()
        if enabled in {"1", "true", "yes", "on"}:
            log_outgoing_message(source, message, parse_mode=parse_mode)
    except Exception as exc:
        print(f"텔레그램 메모리 로깅 실패: {exc}")


def split_message_lines(message: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """텔레그램 길이 제한을 넘지 않도록 메시지 분할"""
    chunks = []
    current = ""

    for section in message.split("\n\n"):
        candidate = section if not current else f"{current}\n\n{section}"
        if len(candidate) <= limit:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(section) <= limit:
            current = section
            continue

        line_buffer = ""
        for line in section.splitlines():
            line_candidate = line if not line_buffer else f"{line_buffer}\n{line}"
            if len(line_candidate) <= limit:
                line_buffer = line_candidate
                continue

            if line_buffer:
                chunks.append(line_buffer)
            line_buffer = line

        if line_buffer:
            current = line_buffer

    if current:
        chunks.append(current)

    return chunks or [message]


def _send_single_telegram(
    message: str,
    parse_mode: str,
    fail_on_error: bool,
) -> bool:
    """단일 텔레그램 메시지 발송"""
    token = get_required_env("TELEGRAM_BOT_TOKEN")
    chat_id = get_required_env("TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": "true",
    }).encode()

    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read() or b"{}")
            ok = resp.status == 200 and body.get("ok", True)
            if not ok:
                raise RuntimeError(f"텔레그램 응답 오류: {body}")
            return True
    except Exception as e:
        print(f"텔레그램 발송 실패: {e}")
        if fail_on_error:
            raise
        return False


def send_telegram(
    message: str,
    parse_mode: str = "HTML",
    fail_on_error: bool = True,
    retry_count: int = 2,
    retry_delay_seconds: float = 1.5,
) -> bool:
    """텔레그램 메시지 발송"""
    chunks = split_message_lines(message)
    for chunk in chunks:
        sent = False
        for attempt in range(retry_count + 1):
            sent = _send_single_telegram(
                message=chunk,
                parse_mode=parse_mode,
                fail_on_error=False,
            )
            if sent:
                break
            if attempt < retry_count:
                print(f"텔레그램 발송 재시도 {attempt + 1}/{retry_count}")
                time.sleep(retry_delay_seconds)
        if not sent:
            attempts = retry_count + 1
            if fail_on_error:
                raise RuntimeError(f"텔레그램 발송이 {attempts}회 모두 실패했습니다.")
            return False
    maybe_log_outgoing_message(message, parse_mode)
    return True
