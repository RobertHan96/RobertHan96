#!/usr/bin/env python3
"""
태스크4: Jira 릴리즈 일정 보고
- Jira REST API로 향후 2주 내 릴리즈 일정 조회
- 평일 아침 09:00 KST 발송
"""

import json
import os
import urllib.request
import urllib.parse
import base64
from datetime import datetime, timedelta, timezone

from notify import send_telegram

KST = timezone(timedelta(hours=9))


def jira_request(path: str) -> dict:
    """Jira Cloud REST API 호출"""
    base_url = os.environ["JIRA_BASE_URL"]  # e.g. https://your-domain.atlassian.net
    email = os.environ["JIRA_EMAIL"]
    token = os.environ["JIRA_API_TOKEN"]

    url = f"{base_url}/rest/api/3/{path}"
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {credentials}")
    req.add_header("Accept", "application/json")

    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def get_upcoming_versions(project_key: str) -> list[dict]:
    """프로젝트의 미릴리즈 버전 목록 (릴리즈일 기준 정렬)"""
    data = jira_request(
        f"project/{project_key}/versions"
    )

    today = datetime.now(KST).date()
    cutoff = today + timedelta(days=14)

    upcoming = []
    for v in data:
        if v.get("released"):
            continue
        release_date_str = v.get("releaseDate")
        if not release_date_str:
            continue

        release_date = datetime.strptime(release_date_str, "%Y-%m-%d").date()
        if today <= release_date <= cutoff:
            upcoming.append({
                "name": v["name"],
                "release_date": release_date_str,
                "days_left": (release_date - today).days,
                "description": v.get("description", ""),
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

    for v in versions:
        d_day = v["days_left"]
        urgency = "🔴" if d_day <= 3 else "🟡" if d_day <= 7 else "🟢"
        lines.append(
            f"{urgency} <b>{v['name']}</b>\n"
            f"   릴리즈: {v['release_date']} (D-{d_day})"
        )
        if v["description"]:
            lines.append(f"   {v['description'][:80]}")
        lines.append("")

    return "\n".join(lines)


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
