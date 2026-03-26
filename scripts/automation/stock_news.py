#!/usr/bin/env python3
from __future__ import annotations

"""
태스크1: 관심 종목 뉴스 모니터링
- watchlist 기반으로 종목별 뉴스 수집
- Marketaux 공식 API로 최근 금융 뉴스를 조회
- 매일 3회 실행 (08/13/18시 KST)
- 텔레그램으로 발송
"""

import html
from collections import defaultdict
from html.parser import HTMLParser
import re
import urllib.parse
from datetime import datetime, timedelta, timezone

from config.loader import load_config
from notify import send_telegram
from runtime import get_required_env, request_json
from tech_news import FETCHERS as TECH_FETCHERS
from tech_news import summarize_with_openai
from watchlist import get_news_watchlist

KST = timezone(timedelta(hours=9))


class TextExtractor(HTMLParser):
    """HTML 본문에서 텍스트만 추출"""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str):
        cleaned = data.strip()
        if cleaned:
            self.parts.append(cleaned)

    def get_text(self) -> str:
        return " ".join(self.parts)


def chunked(items: list[str], size: int) -> list[list[str]]:
    """리스트를 고정 크기 묶음으로 분할"""
    return [items[index:index + size] for index in range(0, len(items), size)]


def html_to_text(raw_html: str) -> str:
    extractor = TextExtractor()
    extractor.feed(raw_html or "")
    return extractor.get_text()


def format_marketaux_datetime(target: datetime) -> str:
    """Marketaux가 지원하는 naive datetime 문자열로 변환"""
    return target.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def get_scheduled_lookback_hours(
    config: dict,
    *,
    default_hours: float,
    now: datetime | None = None,
) -> float:
    """실행 스케줄 기준으로 이전 실행 시점부터의 조회 범위를 계산"""
    now = now or datetime.now(KST)
    stock_config = config.get("stock_news", {})
    schedule_hours = sorted({
        int(hour)
        for hour in stock_config.get("schedule_hours_kst", [8, 13, 18])
    })
    if not schedule_hours:
        return default_hours

    overlap_minutes = int(stock_config.get("schedule_overlap_minutes", 30))
    trigger_grace_minutes = int(stock_config.get("schedule_trigger_grace_minutes", 60))
    today = now.date()
    latest_slot = None

    for hour in reversed(schedule_hours):
        candidate = datetime(today.year, today.month, today.day, hour, tzinfo=KST)
        if candidate <= now:
            latest_slot = candidate
            break

    if latest_slot is None:
        previous_day = today - timedelta(days=1)
        latest_slot = datetime(
            previous_day.year,
            previous_day.month,
            previous_day.day,
            schedule_hours[-1],
            tzinfo=KST,
        )

    if now - latest_slot <= timedelta(minutes=trigger_grace_minutes):
        reference_time = latest_slot - timedelta(seconds=1)
        previous_run = None
        reference_day = reference_time.date()
        for hour in reversed(schedule_hours):
            candidate = datetime(
                reference_day.year,
                reference_day.month,
                reference_day.day,
                hour,
                tzinfo=KST,
            )
            if candidate <= reference_time:
                previous_run = candidate
                break
        if previous_run is None:
            previous_day = reference_day - timedelta(days=1)
            previous_run = datetime(
                previous_day.year,
                previous_day.month,
                previous_day.day,
                schedule_hours[-1],
                tzinfo=KST,
            )
    else:
        previous_run = latest_slot

    delta_hours = (now - previous_run).total_seconds() / 3600
    return max(default_hours, delta_hours + (overlap_minutes / 60))


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
    lookback_hours = get_scheduled_lookback_hours(
        config,
        default_hours=float(config.get("stock_news", {}).get("lookback_hours", 3)),
    )
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


def build_keyword_aliases(item: dict) -> list[str]:
    """키워드 기반 소스에서 종목 매칭에 쓸 별칭 후보"""
    aliases = []
    for value in [item.get("name", ""), item.get("symbol", ""), item.get("news_symbol", "")]:
        normalized = (value or "").strip()
        if normalized and normalized not in aliases:
            aliases.append(normalized)
        compact = normalized.replace(" ", "")
        if compact and compact not in aliases:
            aliases.append(compact)
    return aliases


def contains_alias(text: str, alias: str) -> bool:
    """본문에 종목 별칭이 포함되는지 검사"""
    normalized_alias = (alias or "").strip().lower()
    if not normalized_alias:
        return False

    if re.fullmatch(r"[a-z0-9._-]+", normalized_alias):
        if len(normalized_alias) < 3:
            return False
        pattern = rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])"
        return re.search(pattern, text) is not None

    pattern = rf"(?<![0-9a-z가-힣]){re.escape(normalized_alias)}(?![0-9a-z가-힣])"
    return re.search(pattern, text) is not None


def fetch_hada_news(*, hours: int = 24, limit: int = 30) -> list[dict]:
    """GeekNews RSS에서 최근 글을 읽어 stock news 보조 소스로 사용"""
    import feedparser
    import time

    feed = feedparser.parse("https://news.hada.io/rss/news")
    cutoff = time.time() - (hours * 3600)

    entries = []
    for entry in feed.entries[:limit]:
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            entry_time = time.mktime(published)
            if entry_time < cutoff:
                continue

        description = entry.get("summary", "") or entry.get("description", "")
        entries.append({
            "title": entry.get("title", "제목 없음"),
            "url": entry.get("link", ""),
            "description": html_to_text(description),
            "source": "GeekNews",
            "published_at": entry.get("published", "") or entry.get("updated", ""),
        })

    return entries


def map_keyword_articles_to_symbols(
    items: list[dict],
    articles: list[dict],
    per_symbol_limit: int,
) -> dict[str, list[dict]]:
    """키워드 기반 소스를 watchlist 종목별로 재분배"""
    results: dict[str, list[dict]] = {item["name"]: [] for item in items}
    seen_by_name: dict[str, set[str]] = defaultdict(set)

    sorted_articles = sorted(
        articles,
        key=lambda article: article.get("published_at") or "",
        reverse=True,
    )

    for article in sorted_articles:
        article_id = article.get("url") or article.get("title", "")
        haystack = " ".join([
            article.get("title", ""),
            article.get("description", ""),
            article.get("content", ""),
        ]).lower()

        for item in items:
            name = item["name"]
            if len(results[name]) >= per_symbol_limit:
                continue
            if article_id in seen_by_name[name]:
                continue

            aliases = build_keyword_aliases(item)
            if not any(contains_alias(haystack, alias) for alias in aliases):
                continue

            results[name].append(article)
            seen_by_name[name].add(article_id)

    return results


def build_stock_news_section(results: dict[str, list]) -> list[str]:
    """관심 종목 뉴스 섹션 생성"""
    lines: list[str] = []
    for name, articles in results.items():
        if not articles:
            continue

        lines.append(f"<b>▸ {html.escape(name)}</b>")
        for article in articles[:3]:
            title = html.escape(article.get("title", "제목 없음"))
            safe_link = html.escape(article.get("url", ""), quote=True)
            source = article.get("source", "")
            source_suffix = f" <i>({html.escape(source)})</i>" if source else ""
            lines.append(f"  • <a href=\"{safe_link}\">{title}</a>{source_suffix}")

            description = article.get("description") or article.get("snippet") or ""
            if description:
                lines.append(f"    → {html.escape(shorten_text(description))}")
        lines.append("")

    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def should_include_tech_news(config: dict, now: datetime) -> bool:
    """기술 뉴스 섹션 포함 여부 판단"""
    merge_config = config.get("tech_news", {}).get("merge_into_stock_task", {})
    if not merge_config.get("enabled", False):
        return False
    dispatch_hour = int(merge_config.get("dispatch_hour_kst", 8))
    return now.hour == dispatch_hour


def fetch_tech_news_results(config: dict) -> tuple[dict[str, list[dict]], int]:
    """기술 뉴스 결과 조회 및 요약"""
    results: dict[str, list[dict]] = {}
    failures = 0
    for src in config.get("tech_news", {}).get("sources", []):
        name = src["name"]
        fetcher = TECH_FETCHERS.get(name)
        if not fetcher:
            print(f"[{name}] 알 수 없는 기술 뉴스 소스, 건너뜀")
            failures += 1
            continue

        try:
            entries = fetcher()
            entries = summarize_with_openai(entries)
            results[name] = entries
            print(f"[{name}] {len(entries)}건 수집 + 요약 완료")
        except Exception as e:
            print(f"[{name}] 기술 뉴스 수집 실패: {e}")
            results[name] = []
            failures += 1
    return results, failures


def build_tech_news_section(config: dict, results: dict[str, list[dict]]) -> list[str]:
    """기술 뉴스 섹션 생성"""
    per_source_limit = int(
        config.get("tech_news", {}).get("merge_into_stock_task", {}).get("per_source_limit", 5)
    )
    lines: list[str] = []
    for source, entries in results.items():
        if not entries:
            continue
        lines.append(f"<b>▸ {html.escape(source)}</b>")
        for entry in entries[:per_source_limit]:
            safe_link = html.escape(entry.get("link", ""), quote=True)
            safe_title = html.escape(entry.get("title", "제목 없음"))
            lines.append(f"  • <a href=\"{safe_link}\">{safe_title}</a>")
            summary = entry.get("summary") or entry.get("content") or ""
            if summary:
                lines.append(f"    → {html.escape(shorten_text(summary, 140))}")
        lines.append("")

    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def build_message(
    config: dict,
    stock_results: dict[str, list[dict]],
    *,
    tech_results: dict[str, list[dict]] | None = None,
    include_tech_news: bool = False,
) -> str:
    """텔레그램 발송 메시지 생성"""
    now = datetime.now(KST)
    stock_lines = build_stock_news_section(stock_results)
    tech_lines: list[str] = []
    if include_tech_news and tech_results:
        tech_lines = build_tech_news_section(config, tech_results)

    if not stock_lines and not tech_lines:
        return ""

    sections: list[str] = []
    if stock_lines:
        sections.append(f"<b>📰 관심 종목 뉴스</b> ({now.strftime('%Y-%m-%d %H:%M')})")
        sections.append("")
        sections.extend(stock_lines)

    if tech_lines:
        if stock_lines:
            sections.append("")
        sections.append(f"<b>🔧 기술 뉴스 브리핑</b> ({now.strftime('%Y-%m-%d')})")
        sections.append("")
        sections.extend(tech_lines)

    while sections and not sections[-1].strip():
        sections.pop()

    return "\n".join(sections).rstrip()


def main():
    config = load_config()
    now = datetime.now(KST)
    watchlist = get_news_watchlist()
    batch_size = int(config.get("stock_news", {}).get("batch_size", 20))
    per_symbol_limit = int(config.get("stock_news", {}).get("per_symbol_article_limit", 2))
    max_articles_per_batch = int(config.get("stock_news", {}).get("max_articles_per_batch", 50))
    hada_enabled = bool(config.get("stock_news", {}).get("hada", {}).get("enabled", False))
    hada_hours = get_scheduled_lookback_hours(
        config,
        default_hours=float(config.get("stock_news", {}).get("hada", {}).get("lookback_hours", 24)),
        now=now,
    )
    hada_limit = int(config.get("stock_news", {}).get("hada", {}).get("max_entries", 30))
    hada_per_symbol_limit = int(
        config.get("stock_news", {}).get("hada", {}).get("per_symbol_article_limit", 1)
    )

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

    include_tech_news = should_include_tech_news(config, now)
    tech_results: dict[str, list[dict]] = {}
    if include_tech_news:
        tech_results, tech_failures = fetch_tech_news_results(config)
        tech_sources = config.get("tech_news", {}).get("sources", [])
        if tech_sources and tech_failures == len(tech_sources):
            raise RuntimeError("기술 뉴스 소스 조회가 모두 실패했습니다.")

    if hada_enabled and watchlist:
        try:
            hada_articles = fetch_hada_news(hours=hada_hours, limit=hada_limit)
            mapped = map_keyword_articles_to_symbols(
                watchlist,
                hada_articles,
                per_symbol_limit=hada_per_symbol_limit,
            )
            matched_count = 0
            for name, matched_articles in mapped.items():
                if matched_articles:
                    matched_count += len(matched_articles)
                    results[name].extend(matched_articles)
            print(f"[hada] 기사 {len(hada_articles)}건 / 종목 매칭 {matched_count}건")
        except Exception as e:
            print(f"[hada] 뉴스 조회 실패: {e}")

    message = build_message(
        config,
        results,
        tech_results=tech_results,
        include_tech_news=include_tech_news,
    )
    if message:
        send_telegram(message)
        print("뉴스 알림 발송 완료")
    else:
        print("새 뉴스 없음, 발송 건너뜀")


if __name__ == "__main__":
    main()
