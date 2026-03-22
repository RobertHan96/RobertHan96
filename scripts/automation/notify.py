"""텔레그램 알림 공통 모듈"""

import json
import os
import urllib.parse
import urllib.request


def send_telegram(
    message: str,
    parse_mode: str = "HTML",
    fail_on_error: bool = True,
) -> bool:
    """텔레그램 메시지 발송"""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

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
