"""텔레그램 알림 공통 모듈"""

import os
import urllib.request
import urllib.parse
import json


def send_telegram(message: str, parse_mode: str = "HTML") -> bool:
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
            return resp.status == 200
    except Exception as e:
        print(f"텔레그램 발송 실패: {e}")
        return False
