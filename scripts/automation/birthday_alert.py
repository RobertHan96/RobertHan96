#!/usr/bin/env python3
"""
태스크6: 생일 알림
- data/birthdays.yaml에서 오늘/내일 생일자 확인
- 매일 아침 08:00 KST 발송
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from notify import send_telegram

KST = timezone(timedelta(hours=9))


def load_birthdays() -> list[dict]:
    """생일 목록 로드"""
    path = Path(__file__).resolve().parent.parent.parent / "data" / "birthdays.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def find_birthdays(target_date: str, birthdays: list[dict]) -> list[dict]:
    """MM-DD 기준으로 생일자 찾기"""
    return [b for b in birthdays if b.get("date") == target_date]


def build_message(today_list: list, tomorrow_list: list) -> str:
    """텔레그램 메시지 생성"""
    if not today_list and not tomorrow_list:
        return ""

    now = datetime.now(KST).strftime("%Y-%m-%d")
    lines = [f"<b>🎂 생일 알림</b> ({now})\n"]

    if today_list:
        lines.append("<b>오늘 생일</b>")
        for b in today_list:
            note = f" - {b['note']}" if b.get("note") else ""
            lines.append(f"  🎉 {b['name']}{note}")
        lines.append("")

    if tomorrow_list:
        lines.append("<b>내일 생일</b>")
        for b in tomorrow_list:
            note = f" - {b['note']}" if b.get("note") else ""
            lines.append(f"  🔔 {b['name']}{note}")

    return "\n".join(lines)


def main():
    now = datetime.now(KST)
    today = now.strftime("%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%m-%d")

    birthdays = load_birthdays()
    today_list = find_birthdays(today, birthdays)
    tomorrow_list = find_birthdays(tomorrow, birthdays)

    print(f"오늘({today}) 생일: {len(today_list)}명, 내일({tomorrow}): {len(tomorrow_list)}명")

    message = build_message(today_list, tomorrow_list)
    if message:
        send_telegram(message)
        print("생일 알림 발송 완료")
    else:
        print("오늘/내일 생일자 없음")


if __name__ == "__main__":
    main()
