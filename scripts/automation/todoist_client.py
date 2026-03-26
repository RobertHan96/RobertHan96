#!/usr/bin/env python3
from __future__ import annotations

"""Todoist API v1 공통 클라이언트"""

from datetime import date, datetime, timezone
from urllib.parse import urlencode

from runtime import get_required_env, request_json

API_BASE = "https://api.todoist.com/api/v1"
DEFAULT_LIMIT = 200


def parse_due_datetime(value: str, *, default_timezone: timezone) -> datetime:
    """Todoist due 문자열을 datetime으로 파싱"""
    normalized = (value or "").strip()
    if normalized.endswith("Z"):
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    else:
        parsed = datetime.fromisoformat(normalized)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=default_timezone)
    return parsed.astimezone(default_timezone)


def parse_task_due(
    task: dict,
    *,
    default_timezone: timezone,
) -> dict | None:
    """Todoist task의 due object를 날짜/시간 정보로 정규화"""
    due = task.get("due") or {}
    due_date_str = due.get("date")
    due_datetime_str = due.get("datetime")

    if due_datetime_str:
        parsed_datetime = parse_due_datetime(
            due_datetime_str,
            default_timezone=default_timezone,
        )
        return {
            "due_date": parsed_datetime.date(),
            "due_datetime": parsed_datetime,
            "is_all_day": False,
        }

    if not due_date_str:
        return None

    try:
        if "T" in due_date_str:
            parsed_datetime = parse_due_datetime(
                due_date_str,
                default_timezone=default_timezone,
            )
            return {
                "due_date": parsed_datetime.date(),
                "due_datetime": parsed_datetime,
                "is_all_day": False,
            }

        parsed_date = date.fromisoformat(due_date_str)
        return {
            "due_date": parsed_date,
            "due_datetime": None,
            "is_all_day": True,
        }
    except ValueError:
        return None


def todoist_request(path: str, query: dict[str, str] | None = None) -> dict | list:
    """Todoist API v1 요청"""
    url = f"{API_BASE}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{urlencode(query)}"

    return request_json(
        url,
        headers={"Authorization": f"Bearer {get_required_env('TODOIST_API_TOKEN')}"},
        timeout=10,
        label=f"Todoist API 요청 [{path}]",
    )


def get_active_tasks(limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Todoist의 모든 활성 태스크를 페이지네이션으로 조회"""
    results: list[dict] = []
    cursor: str | None = None

    while True:
        query = {"limit": str(limit)}
        if cursor:
            query["cursor"] = cursor

        data = todoist_request("tasks", query=query)
        if isinstance(data, list):
            results.extend(data)
            break

        page_results = data.get("results", [])
        if isinstance(page_results, list):
            results.extend(page_results)

        cursor = data.get("next_cursor")
        if not cursor:
            break

    return results
