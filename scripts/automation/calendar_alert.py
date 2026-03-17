#!/usr/bin/env python3
"""
태스크5: 캘린더 일정 알림
- Google Calendar API로 당일 일정 조회
- 평일 아침 08:30 KST 발송
"""

import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

from notify import send_telegram

KST = timezone(timedelta(hours=9))


def get_today_events() -> list[dict]:
    """Google Calendar API로 당일 일정 조회"""
    api_key = os.environ["GOOGLE_CALENDAR_API_KEY"]
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")

    now = datetime.now(KST)
    time_min = now.replace(hour=0, minute=0, second=0).isoformat()
    time_max = now.replace(hour=23, minute=59, second=59).isoformat()

    params = urllib.parse.urlencode({
        "key": api_key,
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
    })

    url = (
        f"https://www.googleapis.com/calendar/v3/calendars/"
        f"{urllib.parse.quote(calendar_id)}/events?{params}"
    )

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())

    events = []
    for item in data.get("items", []):
        start = item.get("start", {})
        start_time = start.get("dateTime", start.get("date", ""))
        events.append({
            "summary": item.get("summary", "(제목 없음)"),
            "start": start_time,
            "location": item.get("location", ""),
        })

    return events


def format_time(iso_str: str) -> str:
    """ISO 시간 문자열을 HH:MM 형식으로"""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%H:%M")
    except (ValueError, TypeError):
        return "종일"


def build_message(events: list[dict]) -> str:
    """텔레그램 메시지 생성"""
    today = datetime.now(KST).strftime("%Y-%m-%d (%a)")
    lines = [f"<b>📅 오늘의 일정</b> ({today})\n"]

    if not events:
        lines.append("오늘 예정된 일정이 없습니다. ☀️")
        return "\n".join(lines)

    for e in events:
        time_str = format_time(e["start"])
        lines.append(f"  • <b>{time_str}</b> {e['summary']}")
        if e["location"]:
            lines.append(f"    📍 {e['location']}")

    lines.append(f"\n총 {len(events)}건")
    return "\n".join(lines)


def main():
    print("Google Calendar 당일 일정 조회 중...")
    events = get_today_events()
    print(f"오늘 일정: {len(events)}건")

    message = build_message(events)
    send_telegram(message)
    print("캘린더 알림 발송 완료")


if __name__ == "__main__":
    main()
