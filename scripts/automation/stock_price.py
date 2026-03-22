#!/usr/bin/env python3
from __future__ import annotations

"""
태스크2/2-1: 종목 가격 변동 알림
- watchlist 기반으로 종목 목록을 읽음
- Twelve Data 공식 API를 기본 price provider로 사용
- 한국 종목은 기존 네이버 금융 비공식 API fallback 유지
"""

import argparse
import html
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from notify import send_telegram
from watchlist import get_price_watchlist

KST = timezone(timedelta(hours=9))
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY", "")


def get_legacy_kr_stock_price(symbol: str) -> dict | None:
    """한국 주식 현재가 조회 (네이버 금융 비공식 API fallback)"""
    url = f"https://m.stock.naver.com/api/stock/{symbol}/basic"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return {
                "price": float(data.get("closePrice", "0").replace(",", "")),
                "prev_close": float(data.get("compareToPreviousClosePrice", "0").replace(",", "")),
                "change_pct": float(data.get("fluctuationsRatio", "0")),
            }
    except Exception as e:
        print(f"[KR:{symbol}] 조회 실패: {e}")
        return None


def get_legacy_us_stock_price(symbol: str) -> dict | None:
    """미국 주식 현재가 조회 (Yahoo Finance 비공식 API fallback)"""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?interval=1d&range=2d"
    )
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            result = data["chart"]["result"][0]
            meta = result["meta"]
            price = meta["regularMarketPrice"]
            prev_close = meta["previousClose"]
            change_pct = ((price - prev_close) / prev_close) * 100
            return {
                "price": price,
                "prev_close": prev_close,
                "change_pct": round(change_pct, 2),
            }
    except Exception as e:
        print(f"[US:{symbol}] 조회 실패: {e}")
        return None


def get_twelvedata_stock_price(symbol: str) -> dict | None:
    """Twelve Data 공식 quote API 조회"""
    if not TWELVE_DATA_API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY 가 설정되지 않았습니다.")

    url = (
        "https://api.twelvedata.com/quote?"
        + urllib.parse.urlencode({
            "symbol": symbol,
            "apikey": TWELVE_DATA_API_KEY,
        })
    )
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if "code" in data:
                raise RuntimeError(f"{data.get('code')}: {data.get('message')}")
            return {
                "price": float(data["close"]),
                "prev_close": float(data["previous_close"]),
                "change_pct": round(float(data["percent_change"]), 2),
            }
    except Exception as e:
        print(f"[TD:{symbol}] 조회 실패: {e}")
        return None


PRICE_PROVIDERS = {
    "twelvedata": get_twelvedata_stock_price,
    "legacy_naver": get_legacy_kr_stock_price,
    "legacy_yahoo": get_legacy_us_stock_price,
}


def check_stocks(market: str) -> list[dict]:
    """watchlist에서 종목 목록을 읽고 가격 변동 체크"""
    stocks = get_price_watchlist(market)
    alerts = []

    for stock in stocks:
        provider = stock["price_provider"]
        get_price = PRICE_PROVIDERS.get(provider)
        if get_price is None:
            print(f"[{stock['name']}] 지원하지 않는 price provider: {provider}")
            continue

        data = get_price(stock["price_symbol"])
        if data is None:
            continue

        pct = data["change_pct"]
        threshold = stock["price_threshold_pct"]
        if abs(pct) >= threshold:
            alerts.append({
                "name": stock["name"],
                "symbol": stock["symbol"],
                "price": data["price"],
                "change_pct": pct,
                "threshold": threshold,
            })
            print(f"[ALERT] {stock['name']} ({stock['symbol']}): {pct:+.2f}%")
        else:
            print(f"[OK] {stock['name']} ({stock['symbol']}): {pct:+.2f}%")

    return alerts


def build_message(market: str, alerts: list[dict]) -> str:
    """알림 메시지 생성"""
    market_label = "🇰🇷 한국장" if market == "kr" else "🇺🇸 미국장"
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")

    lines = [f"<b>🚨 {market_label} 가격 변동 알림</b> ({now})\n"]

    for alert in alerts:
        emoji = "📈" if alert["change_pct"] > 0 else "📉"
        lines.append(
            f"{emoji} <b>{html.escape(alert['name'])}</b> ({html.escape(alert['symbol'])})\n"
            f"   현재가: {alert['price']:,.2f} | 변동: {alert['change_pct']:+.2f}% "
            f"(기준 {alert['threshold']:.2f}%)"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["kr", "us"], required=True)
    args = parser.parse_args()

    alerts = check_stocks(args.market)
    if alerts:
        message = build_message(args.market, alerts)
        send_telegram(message)
        print(f"{len(alerts)}개 종목 알림 발송")
    else:
        print("변동 기준 미달, 발송 건너뜀")


if __name__ == "__main__":
    main()
