#!/usr/bin/env python3
from __future__ import annotations

"""워치리스트/뉴스 기반 투자 브리프 생성"""

import json
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from .stock_price import PRICE_PROVIDERS
    from .watchlist import get_news_watchlist, get_price_watchlist
except ImportError:
    from stock_price import PRICE_PROVIDERS
    from watchlist import get_news_watchlist, get_price_watchlist

KST = timezone(timedelta(hours=9))
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
GENERATED_DIR = ROOT_DIR / "data" / "investment_rag" / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
MARKETAUX_API_TOKEN = os.environ.get("MARKETAUX_API_TOKEN", "")


def chunked(items: list[str], size: int) -> list[list[str]]:
    """리스트를 고정 크기 묶음으로 분할"""
    return [items[index:index + size] for index in range(0, len(items), size)]


def fetch_marketaux_batch_news(symbols: list[str], country: str, language: str, limit: int = 3) -> list[dict]:
    """국가별 종목 묶음 뉴스 조회"""
    if not MARKETAUX_API_TOKEN or not symbols:
        return []

    published_after = (
        datetime.now(KST) - timedelta(days=1)
    ).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {
        "api_token": MARKETAUX_API_TOKEN,
        "symbols": ",".join(symbols),
        "filter_entities": "true",
        "must_have_entities": "true",
        "limit": str(limit),
        "published_after": published_after,
    }
    if country:
        params["countries"] = country
    if language:
        params["language"] = language

    url = "https://api.marketaux.com/v1/news/all?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        return data.get("data", [])


def build_price_section(market: str, limit: int = 20) -> list[str]:
    """시장별 가격 스냅샷 생성"""
    lines = []
    items = get_price_watchlist(market)[:limit]
    if not items:
        return lines

    market_label = "미국" if market == "us" else "한국"
    lines.append(f"## {market_label} 관심종목 가격 스냅샷")
    for item in items:
        get_price = PRICE_PROVIDERS.get(item["price_provider"])
        if get_price is None:
            continue
        try:
            data = get_price(item["price_symbol"])
        except Exception as exc:
            lines.append(
                f"- {item['name']} ({item['symbol']}): 조회 실패 ({exc})"
            )
            continue
        if not data:
            continue
        lines.append(
            f"- {item['name']} ({item['symbol']}): "
            f"{data['price']:,.2f} / {data['change_pct']:+.2f}%"
        )
    lines.append("")
    return lines


def build_news_section(limit_per_group: int = 3) -> list[str]:
    """국가별 관심종목 뉴스 요약 생성"""
    lines = ["## 관심종목 뉴스 브리프"]
    watchlist = get_news_watchlist()
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in watchlist:
        grouped[(item["countries"], item["language"])].append(item)

    has_news = False
    for (country, language), items in grouped.items():
        symbols = [item["news_symbol"] for item in items]
        aggregated_news_items = []
        for symbol_batch in chunked(symbols, 20):
            try:
                aggregated_news_items.extend(
                    fetch_marketaux_batch_news(
                        symbols=symbol_batch,
                        country=country,
                        language=language,
                        limit=limit_per_group,
                    )
                )
            except Exception as exc:
                lines.append(f"- [{country or 'global'}] 뉴스 조회 실패: {exc}")
                aggregated_news_items = []
                break

        news_items = sorted(
            aggregated_news_items,
            key=lambda article: article.get("published_at") or "",
            reverse=True,
        )[:limit_per_group]

        if not news_items:
            continue

        has_news = True
        lines.append(f"### {country or 'global'} / {language}")
        for article in news_items:
            title = article.get("title", "제목 없음")
            url = article.get("url", "")
            source = (article.get("source") or {}).get("name", "")
            entities = article.get("entities") or []
            entity_symbols = ", ".join(
                entity.get("symbol", "")
                for entity in entities[:4]
                if entity.get("symbol")
            )
            lines.append(f"- {title}")
            if source:
                lines.append(f"  - source: {source}")
            if entity_symbols:
                lines.append(f"  - symbols: {entity_symbols}")
            if url:
                lines.append(f"  - url: {url}")
        lines.append("")

    if not has_news:
        lines.append("- 최근 뉴스 없음")
        lines.append("")
    return lines


def build_digest() -> Path:
    """일일 투자 브리프 markdown 생성"""
    now = datetime.now(KST)
    date_str = now.strftime("%Y-%m-%d")
    path = GENERATED_DIR / f"{date_str}-investment-brief.md"

    lines = [
        f"# Investment Brief ({date_str})",
        "",
        "매일 생성되는 관심종목 가격/뉴스 요약 문서입니다.",
        "",
    ]
    lines.extend(build_price_section("us"))
    lines.extend(build_price_section("kr"))
    lines.extend(build_news_section())

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"브리프 생성 완료: {path}")
    return path


if __name__ == "__main__":
    build_digest()
