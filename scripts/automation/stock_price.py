#!/usr/bin/env python3
"""
태스크2/2-1: 종목 가격 변동 알림
- 한국장: 장중 5분마다, 전일 종가 대비 3% 이상 변동 시 알림
- 미국장: 새벽 1회, 전일 종가 대비 3% 이상 변동 시 알림
"""

import argparse
import html
import json
import urllib.request
from datetime import datetime

from config.loader import load_config
from notify import send_telegram


def get_kr_stock_price(symbol: str) -> dict | None:
    """한국 주식 현재가 조회 (네이버 금융 비공식 API)"""
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


def get_us_stock_price(symbol: str) -> dict | None:
    """미국 주식 현재가 조회 (Yahoo Finance 비공식 API)"""
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


def check_stocks(market: str) -> list[dict]:
    """설정 파일에서 종목 목록을 읽고 가격 변동 체크"""
    config = load_config()
    threshold = config["stock_price"]["threshold_pct"]

    if market == "kr":
        stocks = config["stock_price"]["kr_stocks"]
        get_price = get_kr_stock_price
    else:
        stocks = config["stock_price"]["us_stocks"]
        get_price = get_us_stock_price

    alerts = []
    for stock in stocks:
        data = get_price(stock["symbol"])
        if data is None:
            continue

        pct = data["change_pct"]
        if abs(pct) >= threshold:
            alerts.append({
                "name": stock["name"],
                "symbol": stock["symbol"],
                "price": data["price"],
                "change_pct": pct,
            })
            print(f"[ALERT] {stock['name']} ({stock['symbol']}): {pct:+.2f}%")
        else:
            print(f"[OK] {stock['name']} ({stock['symbol']}): {pct:+.2f}%")

    return alerts


def build_message(market: str, alerts: list[dict]) -> str:
    """알림 메시지 생성"""
    market_label = "🇰🇷 한국장" if market == "kr" else "🇺🇸 미국장"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [f"<b>🚨 {market_label} 가격 변동 알림</b> ({now})\n"]

    for a in alerts:
        emoji = "📈" if a["change_pct"] > 0 else "📉"
        lines.append(
            f"{emoji} <b>{html.escape(a['name'])}</b> ({html.escape(a['symbol'])})\n"
            f"   현재가: {a['price']:,.0f} | 변동: {a['change_pct']:+.2f}%"
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
