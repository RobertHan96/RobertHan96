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
from collections import defaultdict
import urllib.parse
from datetime import datetime, timedelta, timezone

from config.loader import load_config
from notify import send_telegram
from runtime import get_required_env, request_json
from watchlist import get_news_watchlist

KST = timezone(timedelta(hours=9))


def chunked(items: list[str], size: int) -> list[list[str]]:
    """리스트를 고정 크기 묶음으로 분할"""
    return [items[index:index + size] for index in range(0, len(items), size)]


def format_marketaux_datetime(target: datetime) -> str:
    """Marketaux가 지원하는 naive datetime 문자열로 변환"""
    return target.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def fetch_marketaux_news_batch(
    symbols: list[str],
    *,
    country: str = "",
    language: str = "en",
    limit: int = 50,
) -> list[dict]:
    """Marketaux 뉴스 배치 조회"""
    if not symbols:
        return []

    config = load_config()
    lookback_hours = int(config.get("stock_news", {}).get("lookback_hours", 3))
    published_after = format_marketaux_datetime(
        datetime.now(KST) - timedelta(hours=lookback_hours)
    )

    params = {
        "api_token": get_required_env("MARKETAUX_API_TOKEN"),
        "symbols": ",".join(symbols),
        "filter_entities": "true",
        "must_have_entities": "true",
        "language": language or "en",
        "limit": str(limit),
        "published_after": published_after,
    }
    if country:
        params["countries"] = country

    url = "https://api.marketaux.com/v1/news/all?" + urllib.parse.urlencode(params)
    data = request_json(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
        label=f"Marketaux 뉴스 조회 [{','.join(symbols)}]",
    )
    return data.get("data", [])


def map_articles_to_symbols(
    items: list[dict],
    articles: list[dict],
    per_symbol_limit: int,
) -> dict[str, list[dict]]:
    """배치 조회된 기사들을 watchlist 종목별로 재분배"""
    items_by_symbol = {item["news_symbol"]: item for item in items}
    results: dict[str, list[dict]] = {item["name"]: [] for item in items}
    seen_by_name: dict[str, set[str]] = defaultdict(set)

    sorted_articles = sorted(
        articles,
        key=lambda article: article.get("published_at") or "",
        reverse=True,
    )

    for article in sorted_articles:
        article_id = article.get("uuid") or article.get("url") or article.get("title", "")
        matched_symbols = []
        for entity in article.get("entities") or []:
            symbol = entity.get("symbol", "")
            if symbol in items_by_symbol and symbol not in matched_symbols:
                matched_symbols.append(symbol)

        for symbol in matched_symbols:
            item = items_by_symbol[symbol]
            name = item["name"]
            if len(results[name]) >= per_symbol_limit:
                continue
            if article_id in seen_by_name[name]:
                continue
            results[name].append(article)
            seen_by_name[name].add(article_id)

    return results


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
    config = load_config()
    watchlist = get_news_watchlist()
    batch_size = int(config.get("stock_news", {}).get("batch_size", 20))
    per_symbol_limit = int(config.get("stock_news", {}).get("per_symbol_article_limit", 2))
    max_articles_per_batch = int(config.get("stock_news", {}).get("max_articles_per_batch", 50))

    results = {item["name"]: [] for item in watchlist}
    failures = 0
    supported_items = []
    grouped_items: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for item in watchlist:
        provider = item["news_provider"]
        if provider != "marketaux":
            print(f"[{item['name']}] 지원하지 않는 뉴스 provider: {provider}")
            failures += 1
            continue
        supported_items.append(item)
        grouped_items[(item["countries"], item["language"])].append(item)

    stop_due_to_quota = False
    for (country, language), items in grouped_items.items():
        for symbol_batch in chunked([item["news_symbol"] for item in items], batch_size):
            batch_items = [item for item in items if item["news_symbol"] in set(symbol_batch)]
            limit = min(max_articles_per_batch, max(10, len(symbol_batch) * per_symbol_limit))
            try:
                articles = fetch_marketaux_news_batch(
                    symbol_batch,
                    country=country,
                    language=language,
                    limit=limit,
                )
                mapped = map_articles_to_symbols(
                    batch_items,
                    articles,
                    per_symbol_limit=per_symbol_limit,
                )
                for name, matched_articles in mapped.items():
                    results[name].extend(matched_articles)
                print(
                    f"[{country or 'global'}/{language or 'all'}] "
                    f"{len(symbol_batch)}개 종목 / 기사 {len(articles)}건"
                )
            except Exception as e:
                preview = ",".join(symbol_batch[:3])
                suffix = "" if len(symbol_batch) <= 3 else " 외"
                print(f"[{preview}{suffix}] 뉴스 조회 실패: {e}")
                failures += len(symbol_batch)
                if "usage_limit_reached" in str(e):
                    stop_due_to_quota = True
                    break
        if stop_due_to_quota:
            break

    if supported_items and failures >= len(supported_items):
        raise RuntimeError("관심 종목 뉴스 조회가 모두 실패했습니다.")

    message = build_message(results)
    if message:
        send_telegram(message)
        print("뉴스 알림 발송 완료")
    else:
        print("새 뉴스 없음, 발송 건너뜀")


if __name__ == "__main__":
    main()
