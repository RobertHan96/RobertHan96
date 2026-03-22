#!/usr/bin/env python3
from __future__ import annotations

"""
태스크4: Jira 릴리즈 일정 보고
- Jira REST API로 향후 2주 내 릴리즈 일정 조회
- 릴리즈 설명과 fixVersion 연결 이슈 제목 함께 보고
- 평일 아침 09:00 KST 발송
"""

import base64
import html
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

from notify import send_telegram

KST = timezone(timedelta(hours=9))
ISSUE_PREVIEW_LIMIT = 5


def jira_request(path: str, method: str = "GET", payload: dict | None = None) -> list | dict:
    """Jira Cloud REST API 호출"""
    base_url = os.environ["JIRA_BASE_URL"]  # e.g. https://your-domain.atlassian.net
    email = os.environ["JIRA_EMAIL"]
    token = os.environ["JIRA_API_TOKEN"]

    url = f"{base_url}/rest/api/3/{path}"
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    data = json.dumps(payload).encode() if payload is not None else None

    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Basic {credentials}")
    req.add_header("Accept", "application/json")
    if payload is not None:
        req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def escape_jql_value(value: str) -> str:
    """JQL 문자열 리터럴 이스케이프"""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def shorten_text(text: str, limit: int = 120) -> str:
    """긴 설명 축약"""
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def get_version_issues(project_key: str, version_name: str) -> tuple[int, list[dict]]:
    """릴리즈에 연결된 fixVersion 이슈 제목 조회"""
    jql = (
        f'project = {project_key} '
        f'AND fixVersion = "{escape_jql_value(version_name)}" '
        "ORDER BY priority DESC, updated DESC"
    )
    data = jira_request(
        "search",
        method="POST",
        payload={
            "jql": jql,
            "fields": ["summary", "status", "issuetype"],
            "maxResults": ISSUE_PREVIEW_LIMIT,
        },
    )

    issues = []
    for issue in data.get("issues", []):
        fields = issue.get("fields", {}) or {}
        issues.append({
            "key": issue.get("key", ""),
            "summary": fields.get("summary", ""),
            "status": (fields.get("status") or {}).get("name", ""),
            "issue_type": (fields.get("issuetype") or {}).get("name", ""),
        })

    return data.get("total", len(issues)), issues


def get_upcoming_versions(project_key: str) -> list[dict]:
    """프로젝트의 미릴리즈 버전 목록 (릴리즈일 기준 정렬)"""
    data = jira_request(f"project/{project_key}/versions")

    today = datetime.now(KST).date()
    cutoff = today + timedelta(days=14)

    upcoming = []
    for version in data:
        if version.get("released"):
            continue

        release_date_str = version.get("releaseDate")
        if not release_date_str:
            continue

        release_date = datetime.strptime(release_date_str, "%Y-%m-%d").date()
        if not (today <= release_date <= cutoff):
            continue

        issue_total, issues = get_version_issues(project_key, version.get("name", ""))
        upcoming.append({
            "name": version.get("name", ""),
            "release_date": release_date_str,
            "days_left": (release_date - today).days,
            "description": version.get("description", ""),
            "issue_total": issue_total,
            "issues": issues,
        })

    upcoming.sort(key=lambda x: x["release_date"])
    return upcoming


def build_message(project_key: str, versions: list[dict]) -> str:
    """텔레그램 메시지 생성"""
    now = datetime.now(KST).strftime("%Y-%m-%d")
    lines = [f"<b>📋 Jira 릴리즈 일정</b> ({now})\n"]

    if not versions:
        lines.append("향후 2주 내 예정된 릴리즈가 없습니다.")
        return "\n".join(lines)

    for version in versions:
        d_day = version["days_left"]
        urgency = "🔴" if d_day <= 3 else "🟡" if d_day <= 7 else "🟢"
        lines.append(
            f"{urgency} <b>{html.escape(version['name'])}</b>\n"
            f"   릴리즈: {version['release_date']} (D-{d_day})"
        )
        if version["description"]:
            lines.append(
                f"   릴리즈 내용: {html.escape(shorten_text(version['description']))}"
            )

        if version["issues"]:
            lines.append(f"   연결 task ({version['issue_total']}건)")
            for issue in version["issues"]:
                summary = html.escape(shorten_text(issue["summary"], 90))
                lines.append(
                    f"   - {html.escape(issue['key'])} [{html.escape(issue['status'])}] {summary}"
                )
            remaining = version["issue_total"] - len(version["issues"])
            if remaining > 0:
                lines.append(f"   - 외 {remaining}건 더")
        else:
            lines.append("   연결 task 없음")

        lines.append("")

    return "\n".join(lines).rstrip()


def main():
    project_key = os.environ.get("JIRA_PROJECT_KEY", "PROJ")

    print(f"Jira 프로젝트 [{project_key}] 릴리즈 조회 중...")
    versions = get_upcoming_versions(project_key)
    print(f"향후 2주 내 릴리즈: {len(versions)}건")

    message = build_message(project_key, versions)
    send_telegram(message)
    print("Jira 릴리즈 보고 발송 완료")


if __name__ == "__main__":
    main()
