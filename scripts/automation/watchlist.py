#!/usr/bin/env python3
from __future__ import annotations

"""주식/뉴스 워치리스트 로더"""

import csv
import io
import os
import urllib.request
from pathlib import Path

try:
    from .config.loader import load_config
except ImportError:
    from config.loader import load_config

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_WATCHLIST_PATH = ROOT_DIR / "data" / "watchlist.csv"


def parse_bool(value: str | bool | None, default: bool = True) -> bool:
    """문자열/불리언 값을 bool로 정규화"""
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def parse_float(value: str | None, default: float) -> float:
    """실수값 정규화"""
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def load_watchlist_csv() -> str:
    """watchlist CSV 원문 로드"""
    config = load_config()
    watchlist_config = config.get("watchlist", {})
    source_type = watchlist_config.get("source_type", "published_csv")
    source_path = watchlist_config.get("local_csv_path", "data/watchlist.csv")
    local_path = ROOT_DIR / source_path

    def load_local_csv() -> str:
        if not local_path.exists():
            raise FileNotFoundError(f"watchlist CSV를 찾을 수 없습니다: {local_path}")
        return local_path.read_text(encoding="utf-8-sig")

    if source_type == "published_csv":
        env_var_name = watchlist_config.get(
            "published_csv_env_var",
            "WATCHLIST_PUBLISHED_CSV_URL",
        )
        source_url = os.environ.get(env_var_name, "").strip()
        if not source_url:
            source_url = watchlist_config.get("published_csv_url", "").strip()
        if not source_url:
            print(
                f"watchlist published CSV URL이 없어 로컬 CSV로 fallback 합니다: {local_path}"
            )
            return load_local_csv()

        req = urllib.request.Request(source_url)
        req.add_header("User-Agent", "Mozilla/5.0")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8-sig")
        except Exception as exc:
            print(
                f"watchlist published CSV 조회 실패로 로컬 CSV fallback 합니다: {exc}"
            )
            return load_local_csv()

    return load_local_csv()


def load_watchlist() -> list[dict]:
    """워치리스트 CSV를 구조화된 dict 목록으로 변환"""
    config = load_config()
    default_threshold = float(config.get("stock_price", {}).get("default_threshold_pct", 3.0))
    csv_text = load_watchlist_csv()
    reader = csv.DictReader(io.StringIO(csv_text))

    items = []
    for row in reader:
        symbol = (row.get("symbol") or "").strip()
        if not symbol:
            continue

        price_symbol = (row.get("price_symbol") or symbol).strip()
        news_symbol = (row.get("news_symbol") or symbol).strip()
        item = {
            "symbol": symbol,
            "name": (row.get("name") or symbol).strip(),
            "market": (row.get("market") or "us").strip().lower(),
            "enabled": parse_bool(row.get("enabled"), True),
            "price_enabled": parse_bool(row.get("price_enabled"), True),
            "news_enabled": parse_bool(row.get("news_enabled"), True),
            "price_threshold_pct": parse_float(row.get("price_threshold_pct"), default_threshold),
            "price_provider": (row.get("price_provider") or "twelvedata").strip().lower(),
            "price_symbol": price_symbol,
            "news_provider": (row.get("news_provider") or "marketaux").strip().lower(),
            "news_symbol": news_symbol,
            "countries": (row.get("countries") or "").strip(),
            "language": (row.get("language") or "en").strip(),
        }
        items.append(item)

    return items


def get_price_watchlist(market: str) -> list[dict]:
    """가격 모니터링 대상 필터"""
    return [
        item
        for item in load_watchlist()
        if item["enabled"] and item["price_enabled"] and item["market"] == market
    ]


def get_news_watchlist() -> list[dict]:
    """뉴스 모니터링 대상 필터"""
    return [
        item
        for item in load_watchlist()
        if item["enabled"] and item["news_enabled"]
    ]
