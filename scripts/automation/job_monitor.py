#!/usr/bin/env python3
"""
태스크7: 채용공고 모니터링
- 원티드 API로 AI/ML 관련 채용공고 검색
- 매일 10:00 KST 발송
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

from config.loader import load_config
from notify import send_telegram

KST = timezone(timedelta(hours=9))


def search_wanted_jobs(keyword: str, limit: int = 5) -> list[dict]:
    """원티드 채용공고 검색 (비공식 API)"""
    url = "https://www.wanted.co.kr/api/v4/jobs?" + urllib.parse.urlencode({
        "query": keyword,
        "limit": limit,
        "offset": 0,
        "country": "kr",
    })

    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            jobs = []
            for item in data.get("data", []):
                jobs.append({
                    "title": item.get("position", ""),
                    "company": item.get("company", {}).get("name", ""),
                    "link": f"https://www.wanted.co.kr/wd/{item.get('id', '')}",
                })
            return jobs
    except Exception as e:
        print(f"원티드 검색 실패 [{keyword}]: {e}")
        return []


def build_message(results: dict[str, list]) -> str:
    """텔레그램 메시지 생성"""
    now = datetime.now(KST).strftime("%Y-%m-%d")
    lines = [f"<b>💼 채용공고 모니터링</b> ({now})\n"]

    has_jobs = False
    for keyword, jobs in results.items():
        if not jobs:
            continue
        has_jobs = True
        lines.append(f"<b>▸ {keyword}</b>")
        for j in jobs:
            lines.append(
                f"  • <a href=\"{j['link']}\">{j['title']}</a>\n"
                f"    🏢 {j['company']}"
            )
        lines.append("")

    if not has_jobs:
        return ""

    return "\n".join(lines)


def main():
    config = load_config()
    sources = config["job_monitor"]["sources"]

    results = {}
    for src in sources:
        for kw in src.get("keywords", []):
            jobs = search_wanted_jobs(kw)
            results[kw] = jobs
            print(f"[{kw}] {len(jobs)}건")

    message = build_message(results)
    if message:
        send_telegram(message)
        print("채용공고 알림 발송 완료")
    else:
        print("새 채용공고 없음")


if __name__ == "__main__":
    main()
