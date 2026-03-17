#!/usr/bin/env python3
"""
태스크3: 기술 뉴스 알림 (파이토치, 하다/긱뉴스)
- RSS 피드에서 최근 24시간 이내 글 수집
- 매일 아침 08:00 KST 1회 발송
"""

import time
from datetime import datetime, timezone, timedelta

import feedparser

from config.loader import load_config
from notify import send_telegram

KST = timezone(timedelta(hours=9))


def fetch_recent_entries(feed_url: str, hours: int = 24) -> list[dict]:
    """RSS 피드에서 최근 N시간 이내 글 수집"""
    feed = feedparser.parse(feed_url)
    cutoff = time.time() - (hours * 3600)

    entries = []
    for entry in feed.entries[:20]:
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            entry_time = time.mktime(published)
            if entry_time < cutoff:
                continue

        entries.append({
            "title": entry.get("title", "제목 없음"),
            "link": entry.get("link", ""),
            "published": datetime.fromtimestamp(
                time.mktime(published), tz=KST
            ).strftime("%m/%d %H:%M") if published else "",
        })

    return entries


def build_message(results: dict[str, list]) -> str:
    """텔레그램 발송 메시지 생성"""
    now = datetime.now(KST).strftime("%Y-%m-%d")
    lines = [f"<b>🔧 기술 뉴스 브리핑</b> ({now})\n"]

    has_news = False
    for source, entries in results.items():
        if not entries:
            continue
        has_news = True
        lines.append(f"<b>▸ {source}</b>")
        for e in entries[:5]:
            lines.append(f"  • <a href=\"{e['link']}\">{e['title']}</a>")
        lines.append("")

    if not has_news:
        return ""

    return "\n".join(lines)


def main():
    config = load_config()
    sources = config["tech_news"]["sources"]

    results = {}
    for src in sources:
        try:
            entries = fetch_recent_entries(src["url"])
            results[src["name"]] = entries
            print(f"[{src['name']}] {len(entries)}건 수집")
        except Exception as e:
            print(f"[{src['name']}] RSS 수집 실패: {e}")
            results[src["name"]] = []

    message = build_message(results)
    if message:
        send_telegram(message)
        print("기술 뉴스 알림 발송 완료")
    else:
        print("새 뉴스 없음")


if __name__ == "__main__":
    main()
