#!/usr/bin/env python3
from __future__ import annotations

"""
태스크7: 채용공고 모니터링
- 원티드 API로 AI/ML 관련 채용공고 검색
- 채용공고 본문에서 주요 업무 중심으로 요약해 전달
- 매일 10:00 KST 발송
"""

import html
import urllib.parse
from datetime import datetime, timedelta, timezone

from config.loader import load_config
from notify import send_telegram
from runtime import request_json

KST = timezone(timedelta(hours=9))


def wanted_request(url: str) -> dict:
    """Wanted API 요청"""
    data = request_json(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
        label="Wanted API 요청",
    )
    return data if isinstance(data, dict) else {}


def clean_lines(text: str) -> list[str]:
    """본문 텍스트를 줄 단위로 정리"""
    cleaned = []
    for raw_line in (text or "").splitlines():
        line = " ".join(raw_line.replace("•", " ").replace("-", " ").split())
        if line:
            cleaned.append(line)
    return cleaned


def shorten_text(text: str, limit: int = 120) -> str:
    """긴 텍스트 축약"""
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def summarize_job_detail(job_detail: dict) -> str:
    """채용 본문을 주요 업무 중심으로 요약"""
    detail = job_detail.get("detail") or {}
    task_lines = clean_lines(detail.get("main_tasks", ""))
    requirement_lines = clean_lines(detail.get("requirements", ""))
    intro_lines = clean_lines(detail.get("intro", ""))

    summary_parts = []
    if task_lines:
        summary_parts.append("주요 업무: " + ", ".join(task_lines[:3]))
    if requirement_lines:
        summary_parts.append("요건: " + ", ".join(requirement_lines[:2]))
    elif intro_lines:
        summary_parts.append("설명: " + shorten_text(intro_lines[0], 90))

    if not summary_parts:
        return "본문 요약 정보가 없습니다."

    return shorten_text(" / ".join(summary_parts), 180)


def fetch_wanted_job_detail(job_id: int | str) -> dict:
    """원티드 채용공고 상세 조회"""
    url = f"https://www.wanted.co.kr/api/v4/jobs/{job_id}"

    try:
        data = wanted_request(url)
        return data.get("job", {}) or {}
    except Exception as e:
        print(f"원티드 상세 조회 실패 [{job_id}]: {e}")
        return {}


def search_wanted_jobs(keyword: str, limit: int = 5) -> list[dict]:
    """원티드 채용공고 검색 (비공식 API)"""
    url = "https://www.wanted.co.kr/api/v4/jobs?" + urllib.parse.urlencode({
        "query": keyword,
        "limit": limit,
        "offset": 0,
        "country": "kr",
    })

    data = wanted_request(url)
    jobs = []
    for item in data.get("data", []):
        job_id = item.get("id", "")
        detail = fetch_wanted_job_detail(job_id)
        jobs.append({
            "id": job_id,
            "title": item.get("position", ""),
            "company": item.get("company", {}).get("name", ""),
            "link": f"https://www.wanted.co.kr/wd/{job_id}",
            "summary": summarize_job_detail(detail),
        })
    return jobs


def build_message(results: dict[str, list]) -> str:
    """텔레그램 메시지 생성"""
    now = datetime.now(KST).strftime("%Y-%m-%d")
    lines = [f"<b>💼 채용공고 모니터링</b> ({now})\n"]

    has_jobs = False
    for keyword, jobs in results.items():
        if not jobs:
            continue

        has_jobs = True
        lines.append(f"<b>▸ {html.escape(keyword)}</b>")
        for job in jobs:
            lines.append(
                f"  • <a href=\"{job['link']}\">{html.escape(job['title'])}</a>\n"
                f"    🏢 {html.escape(job['company'])}\n"
                f"    🧩 {html.escape(job['summary'])}"
            )
        lines.append("")

    if not has_jobs:
        return ""

    return "\n".join(lines).rstrip()


def main():
    config = load_config()
    sources = config["job_monitor"]["sources"]

    results = {}
    attempted = 0
    failures = 0
    for src in sources:
        for keyword in src.get("keywords", []):
            attempted += 1
            try:
                jobs = search_wanted_jobs(keyword)
                results[keyword] = jobs
                print(f"[{keyword}] {len(jobs)}건")
            except Exception as e:
                print(f"원티드 검색 실패 [{keyword}]: {e}")
                results[keyword] = []
                failures += 1

    if attempted and failures == attempted:
        raise RuntimeError("채용공고 검색이 모두 실패했습니다.")

    message = build_message(results)
    if message:
        send_telegram(message)
        print("채용공고 알림 발송 완료")
    else:
        print("새 채용공고 없음")


if __name__ == "__main__":
    main()
