#!/usr/bin/env python3
from __future__ import annotations

"""
태스크1: 관심 종목 뉴스 모니터링
- watchlist 기반으로 종목별 뉴스 수집
- Marketaux 공식 API로 최근 금융 뉴스를 조회
- 매 2시간마다 실행 (08~22시 KST)
- 텔레그램으로 발송
"""

import html
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from config.loader import load_config
from notify import send_telegram
from watchlist import get_news_watchlist

KST = timezone(timedelta(hours=9))
MARKETAUX_API_TOKEN = os.environ["MARKETAUX_API_TOKEN"]


def fetch_marketaux_news(symbol: str, country: str = "", language: str = "en", limit: int = 3) -> list[dict]:
    """Marketaux 뉴스 조회"""
    config = load_config()
    lookback_hours = int(config.get("stock_news", {}).get("lookback_hours", 3))
    published_after = (
        datetime.now(KST) - timedelta(hours=lookback_hours)
    ).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "api_token": MARKETAUX_API_TOKEN,
        "symbols": symbol,
        "filter_entities": "true",
        "language": language or "en",
        "limit": str(limit),
        "published_after": published_after,
    }
    if country:
        params["countries"] = country

    url = "https://api.marketaux.com/v1/news/all?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        return data.get("data", [])


def shorten_text(text: str, limit: int = 100) -> str:
    """뉴스 설명 축약"""
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def build_message(results: dict[str, list]) -> str:
    """텔레그램 발송 메시지 생성"""
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    lines = [f"<b>📰 관심 종목 뉴스</b> ({now})\n"]

    has_news = False
    for name, articles in results.items():
        if not articles:
            continue

        has_news = True
        lines.append(f"<b>▸ {html.escape(name)}</b>")
        for article in articles[:3]:
            title = html.escape(article.get("title", "제목 없음"))
            safe_link = html.escape(article.get("url", ""), quote=True)
            lines.append(f"  • <a href=\"{safe_link}\">{title}</a>")

            description = article.get("description") or article.get("snippet") or ""
            if description:
                lines.append(f"    → {html.escape(shorten_text(description))}")
        lines.append("")

    if not has_news:
        return ""

    return "\n".join(lines).rstrip()


def main():
    watchlist = get_news_watchlist()
    results = {}

    for item in watchlist:
        provider = item["news_provider"]
        if provider != "marketaux":
            print(f"[{item['name']}] 지원하지 않는 뉴스 provider: {provider}")
            continue

        try:
            articles = fetch_marketaux_news(
                symbol=item["news_symbol"],
                country=item["countries"],
                language=item["language"],
            )
            results[item["name"]] = articles
            print(f"[{item['name']}] {len(articles)}건")
        except Exception as e:
            print(f"[{item['name']}] 뉴스 조회 실패: {e}")
            results[item["name"]] = []

    message = build_message(results)
    if message:
        send_telegram(message)
        print("뉴스 알림 발송 완료")
    else:
        print("새 뉴스 없음, 발송 건너뜀")


if __name__ == "__main__":
    main()
