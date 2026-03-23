#!/usr/bin/env python3
from __future__ import annotations

"""
태스크6: 생일 알림
- Todoist 태스크 제목에 '생일' 키워드가 포함된 항목을 생일로 판단
- due date 기준 오늘부터 7일 뒤까지 생일 확인
- 매일 아침 08:00 KST 발송
"""

import html
from datetime import date, datetime, timedelta, timezone

from notify import send_telegram
from runtime import get_required_env, request_json

KST = timezone(timedelta(hours=9))
WINDOW_DAYS = 7
WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]
API_BASE = "https://api.todoist.com/rest/v2"
BIRTHDAY_KEYWORD = "생일"


def todoist_get(endpoint: str) -> list | dict:
    """Todoist REST API GET 요청"""
    return request_json(
        f"{API_BASE}/{endpoint}",
        headers={"Authorization": f"Bearer {get_required_env('TODOIST_API_TOKEN')}"},
        timeout=10,
        label=f"Todoist API 요청 [{endpoint}]",
    )


def parse_due_date(task: dict) -> date | None:
    """Todoist 태스크의 due date를 KST 기준 날짜로 변환"""
    due = task.get("due") or {}
    due_date_str = due.get("date")
    if not due_date_str:
        return None

    due_datetime_str = due.get("datetime")
    if due_datetime_str:
        try:
            due_datetime = datetime.fromisoformat(
                due_datetime_str.replace("Z", "+00:00")
            ).astimezone(KST)
            return due_datetime.date()
        except ValueError:
            return None

    try:
        return datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def is_birthday_task(task: dict) -> bool:
    """태스크 제목에 생일 키워드가 포함되어 있는지 확인"""
    content = task.get("content", "") or ""
    return BIRTHDAY_KEYWORD in content


def get_upcoming_birthdays(window_days: int = WINDOW_DAYS) -> list[dict]:
    """Todoist에서 향후 생일 태스크 조회"""
    today = datetime.now(KST).date()
    cutoff = today + timedelta(days=window_days)
    tasks = todoist_get("tasks")
    results = []

    for task in tasks:
        if not is_birthday_task(task):
            continue

        due_date = parse_due_date(task)
        if due_date is None or not (today <= due_date <= cutoff):
            continue

        results.append({
            "title": task.get("content", ""),
            "note": task.get("description", ""),
            "event_date": due_date,
            "days_left": (due_date - today).days,
        })

    results.sort(key=lambda x: (x["event_date"], x["title"]))
    return results


def format_day_heading(target_date: date, today: date) -> str:
    """날짜 헤더 포맷"""
    delta = (target_date - today).days
    suffix = "오늘" if delta == 0 else "내일" if delta == 1 else f"D-{delta}"
    return (
        f"{target_date.strftime('%m-%d')} "
        f"({WEEKDAY_LABELS[target_date.weekday()]}) · {suffix}"
    )


def collapse_text(text: str, limit: int = 90) -> str:
    """설명 텍스트 한 줄 축약"""
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def build_message(upcoming_birthdays: list[dict]) -> str:
    """텔레그램 메시지 생성"""
    if not upcoming_birthdays:
        return ""

    today = datetime.now(KST).date()
    cutoff = today + timedelta(days=WINDOW_DAYS)
    lines = [
        f"<b>🎂 생일 알림</b> "
        f"({today.strftime('%Y-%m-%d')} ~ {cutoff.strftime('%Y-%m-%d')})\n"
    ]

    current_date = None
    for birthday in upcoming_birthdays:
        if birthday["event_date"] != current_date:
            current_date = birthday["event_date"]
            lines.append(f"<b>{format_day_heading(current_date, today)}</b>")

        icon = "🎉" if birthday["days_left"] == 0 else "🔔"
        lines.append(f"  {icon} {html.escape(birthday['title'])}")
        if birthday["note"]:
            lines.append(f"      {html.escape(collapse_text(birthday['note']))}")
        if birthday["days_left"] == 0:
            lines.append("      오늘 챙기기")
        elif birthday["days_left"] == 1:
            lines.append("      내일 미리 챙기기")
        else:
            lines.append(f"      {birthday['days_left']}일 남음")
        lines.append("")

    return "\n".join(lines).rstrip()


def main():
    upcoming_birthdays = get_upcoming_birthdays()
    print(f"Todoist 기반 향후 7일 생일: {len(upcoming_birthdays)}건")

    message = build_message(upcoming_birthdays)
    if message:
        send_telegram(message)
        print("생일 알림 발송 완료")
    else:
        print("향후 7일 생일 태스크 없음")


if __name__ == "__main__":
    main()
