#!/usr/bin/env python3
from __future__ import annotations

"""
태스크5: Todoist 일정 알림
- Todoist REST API v2로 오늘부터 7일 뒤까지의 일정 조회
- 평일 아침 08:30 KST 텔레그램 발송
"""

import html
import json
import os
import urllib.request
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from notify import send_telegram

KST = timezone(timedelta(hours=9))
TODOIST_API_TOKEN = os.environ["TODOIST_API_TOKEN"]
API_BASE = "https://api.todoist.com/rest/v2"
WINDOW_DAYS = 7
WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]


def todoist_get(endpoint: str) -> list | dict:
    """Todoist REST API GET 요청"""
    req = urllib.request.Request(f"{API_BASE}/{endpoint}")
    req.add_header("Authorization", f"Bearer {TODOIST_API_TOKEN}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def parse_due(task: dict) -> dict | None:
    """Todoist due 정보를 파싱해 KST 기준 일정 정보로 변환"""
    due = task.get("due") or {}
    due_date_str = due.get("date")
    if not due_date_str:
        return None

    due_datetime = None
    due_datetime_str = due.get("datetime")
    parsed_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()

    if due_datetime_str:
        try:
            due_datetime = datetime.fromisoformat(
                due_datetime_str.replace("Z", "+00:00")
            ).astimezone(KST)
            parsed_date = due_datetime.date()
        except ValueError:
            due_datetime = None

    return {
        "due_date": parsed_date,
        "due_datetime": due_datetime,
        "is_all_day": due_datetime is None,
    }


def normalize_task(task: dict) -> dict | None:
    """메시지 생성에 필요한 태스크 정보만 추출"""
    parsed_due = parse_due(task)
    if parsed_due is None:
        return None

    return {
        "content": task.get("content", ""),
        "description": task.get("description", ""),
        "priority": task.get("priority", 1),
        "project_id": task.get("project_id", ""),
        **parsed_due,
    }


def get_tasks_for_window(window_days: int = WINDOW_DAYS) -> tuple[list[dict], list[dict]]:
    """오늘부터 지정 기간까지의 일정과 기한 지난 태스크를 조회"""
    tasks = todoist_get("tasks")
    today = datetime.now(KST).date()
    cutoff = today + timedelta(days=window_days)

    upcoming = []
    overdue = []

    for task in tasks:
        normalized = normalize_task(task)
        if normalized is None:
            continue

        if normalized["due_date"] < today:
            overdue.append(normalized)
        elif normalized["due_date"] <= cutoff:
            upcoming.append(normalized)

    overdue.sort(key=lambda x: (x["due_date"], -x["priority"], x["content"].lower()))
    upcoming.sort(
        key=lambda x: (
            x["due_date"],
            x["is_all_day"],
            x["due_datetime"] or datetime.combine(x["due_date"], time.max, tzinfo=KST),
            -x["priority"],
            x["content"].lower(),
        )
    )
    return upcoming, overdue


def format_priority(priority: int) -> str:
    """Todoist 우선순위를 이모지로"""
    return {4: "🔴", 3: "🟠", 2: "🔵"}.get(priority, "⚪")


def format_time(task: dict) -> str:
    """마감 시간 포맷"""
    if task["due_datetime"] is None:
        return "종일"
    return task["due_datetime"].strftime("%H:%M")


def collapse_text(text: str, limit: int = 90) -> str:
    """여러 줄 텍스트를 한 줄 요약으로 축약"""
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def format_day_heading(target_date: date, today: date) -> str:
    """날짜 헤더 포맷"""
    delta = (target_date - today).days
    suffix = "오늘" if delta == 0 else "내일" if delta == 1 else f"D-{delta}"
    return (
        f"{target_date.strftime('%m-%d')} "
        f"({WEEKDAY_LABELS[target_date.weekday()]}) · {suffix}"
    )


def build_message(upcoming_tasks: list[dict], overdue_tasks: list[dict]) -> str:
    """텔레그램 메시지 생성"""
    today = datetime.now(KST).date()
    cutoff = today + timedelta(days=WINDOW_DAYS)
    lines = [
        f"<b>📅 Todoist 일정 알림</b> "
        f"({today.strftime('%Y-%m-%d')} ~ {cutoff.strftime('%Y-%m-%d')})\n"
    ]

    if overdue_tasks:
        lines.append(f"<b>⚠️ 미해결 지난 일정 ({len(overdue_tasks)}건)</b>")
        for task in overdue_tasks[:5]:
            lines.append(
                "  "
                f"{format_priority(task['priority'])} "
                f"{task['due_date'].strftime('%m-%d')} "
                f"{html.escape(task['content'])}"
            )
        lines.append("")

    if not upcoming_tasks:
        lines.append("향후 7일 내 예정된 Todoist 일정이 없습니다. ☀️")
        return "\n".join(lines)

    grouped_tasks: dict[date, list[dict]] = defaultdict(list)
    for task in upcoming_tasks:
        grouped_tasks[task["due_date"]].append(task)

    lines.append(f"<b>▸ 향후 7일 일정 ({len(upcoming_tasks)}건)</b>")
    for due_date in sorted(grouped_tasks):
        lines.append(f"<b>{format_day_heading(due_date, today)}</b>")
        for task in grouped_tasks[due_date]:
            lines.append(
                "  "
                f"{format_priority(task['priority'])} "
                f"<b>{format_time(task)}</b> "
                f"{html.escape(task['content'])}"
            )
            if task["description"]:
                lines.append(
                    f"      {html.escape(collapse_text(task['description']))}"
                )
        lines.append("")

    return "\n".join(lines).rstrip()


def main():
    print("Todoist 향후 7일 일정 조회 중...")
    upcoming_tasks, overdue_tasks = get_tasks_for_window()
    print(f"향후 일정: {len(upcoming_tasks)}건, 기한 지남: {len(overdue_tasks)}건")

    message = build_message(upcoming_tasks, overdue_tasks)
    send_telegram(message)
    print("일정 알림 발송 완료")


if __name__ == "__main__":
    main()
