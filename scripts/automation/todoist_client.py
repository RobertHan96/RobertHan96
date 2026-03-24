#!/usr/bin/env python3
from __future__ import annotations

"""Todoist API v1 공통 클라이언트"""

from urllib.parse import urlencode

from runtime import get_required_env, request_json

API_BASE = "https://api.todoist.com/api/v1"
DEFAULT_LIMIT = 200


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
