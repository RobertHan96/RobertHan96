#!/usr/bin/env python3
"""
태스크5: 오늘의 할일 알림 (Todoist)
- Todoist REST API v2로 당일 태스크 조회
- 평일 아침 08:30 KST 텔레그램 발송
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

from notify import send_telegram

KST = timezone(timedelta(hours=9))
TODOIST_API_TOKEN = os.environ["TODOIST_API_TOKEN"]
API_BASE = "https://api.todoist.com/rest/v2"


def todoist_get(endpoint: str) -> list | dict:
    """Todoist REST API GET 요청"""
    req = urllib.request.Request(f"{API_BASE}/{endpoint}")
    req.add_header("Authorization", f"Bearer {TODOIST_API_TOKEN}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def get_today_tasks() -> list[dict]:
    """오늘 마감인 태스크 조회"""
    today_str = datetime.now(KST).strftime("%Y-%m-%d")

    # filter로 오늘 마감 태스크 조회
    filter_param = urllib.parse.quote(f"due: {today_str}")
    tasks = todoist_get(f"tasks?filter={filter_param}")

    results = []
    for task in tasks:
        due = task.get("due", {}) or {}
        results.append({
            "content": task.get("content", ""),
            "description": task.get("description", ""),
            "priority": task.get("priority", 1),
            "due_time": due.get("datetime", due.get("date", "")),
            "project_id": task.get("project_id", ""),
        })

    # 우선순위 높은 순 (Todoist: 4=urgent, 1=normal)
    results.sort(key=lambda x: x["priority"], reverse=True)
    return results


import urllib.parse


def get_overdue_tasks() -> list[dict]:
    """기한 지난 미완료 태스크 조회"""
    filter_param = urllib.parse.quote("overdue")
    tasks = todoist_get(f"tasks?filter={filter_param}")

    results = []
    for task in tasks:
        due = task.get("due", {}) or {}
        results.append({
            "content": task.get("content", ""),
            "due_time": due.get("date", ""),
            "priority": task.get("priority", 1),
        })
    return results


def format_priority(p: int) -> str:
    """Todoist 우선순위를 이모지로"""
    return {4: "🔴", 3: "🟠", 2: "🔵"}.get(p, "⚪")


def format_time(due_time: str) -> str:
    """마감 시간 포맷"""
    if not due_time or len(due_time) <= 10:
        return "종일"
    try:
        dt = datetime.fromisoformat(due_time)
        return dt.astimezone(KST).strftime("%H:%M")
    except (ValueError, TypeError):
        return "종일"


def build_message(today_tasks: list[dict], overdue_tasks: list[dict]) -> str:
    """텔레그램 메시지 생성"""
    today = datetime.now(KST).strftime("%Y-%m-%d (%a)")
    lines = [f"<b>📋 오늘의 할일</b> ({today})\n"]

    if overdue_tasks:
        lines.append(f"<b>⚠️ 기한 지난 태스크 ({len(overdue_tasks)}건)</b>")
        for t in overdue_tasks[:5]:
            pri = format_priority(t["priority"])
            lines.append(f"  {pri} {t['content']} (마감: {t['due_time']})")
        lines.append("")

    if today_tasks:
        lines.append(f"<b>▸ 오늘 할일 ({len(today_tasks)}건)</b>")
        for t in today_tasks:
            pri = format_priority(t["priority"])
            time_str = format_time(t["due_time"])
            lines.append(f"  {pri} <b>{time_str}</b> {t['content']}")
            if t["description"]:
                lines.append(f"      {t['description'][:80]}")
    else:
        lines.append("오늘 예정된 할일이 없습니다. ☀️")

    return "\n".join(lines)


def main():
    print("Todoist 당일 태스크 조회 중...")
    today_tasks = get_today_tasks()
    overdue_tasks = get_overdue_tasks()
    print(f"오늘 할일: {len(today_tasks)}건, 기한 지남: {len(overdue_tasks)}건")

    message = build_message(today_tasks, overdue_tasks)
    send_telegram(message)
    print("할일 알림 발송 완료")


if __name__ == "__main__":
    main()
