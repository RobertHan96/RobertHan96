#!/usr/bin/env python3
from __future__ import annotations

"""BTC 역프리미엄을 확인하고 조건 진입 시 한 번만 알린다."""

import argparse
import json
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

try:
    from .config.loader import load_config
    from .notify import send_telegram
    from .runtime import get_required_env, request_json
except ImportError:
    from config.loader import load_config
    from notify import send_telegram
    from runtime import get_required_env, request_json

UPBIT_URL = "https://api.upbit.com/v1/ticker?markets=KRW-BTC"
BINANCE_URL = "https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT&type=MINI"
FX_URL = "https://api.coinbase.com/v2/exchange-rates?currency=USD"
STATE_KEY = "crypto-premium/btc-upbit-binance/v1"
KST = timezone(timedelta(hours=9))


def positive_decimal(value, label: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label}: 올바른 숫자가 아닙니다.") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{label}: 유한한 양수여야 합니다.")
    return number


@dataclass(frozen=True)
class PremiumSnapshot:
    upbit_krw: Decimal
    binance_usdt: Decimal
    usd_krw: Decimal
    usd_usdt: Decimal
    observed_at: datetime

    @property
    def overseas_krw(self) -> Decimal:
        # Coinbase는 1 USD당 USDT를 반환하므로 역수로 USDT/USD를 환산한다.
        return self.binance_usdt / self.usd_usdt * self.usd_krw

    @property
    def premium_pct(self) -> Decimal:
        return (self.upbit_krw / self.overseas_krw - 1) * 100

    def to_record(self) -> dict:
        return {
            "observed_at": self.observed_at.isoformat(),
            "upbit_krw": str(self.upbit_krw),
            "binance_usdt": str(self.binance_usdt),
            "usd_krw": str(self.usd_krw),
            "usdt_usd": str(1 / self.usd_usdt),
            "overseas_krw": str(self.overseas_krw),
            "premium_pct": str(self.premium_pct),
        }


def fetch_json(url: str, label: str):
    for attempt in range(2):
        try:
            return request_json(
                url, timeout=10, label=label,
                headers={"User-Agent": "RH96-premium-monitor/1.0", "Accept": "application/json"},
            )
        except (RuntimeError, OSError) as exc:
            cause = exc.__cause__ or exc
            if isinstance(cause, urllib.error.HTTPError) and cause.code not in {429, 500, 502, 503, 504}:
                raise
            if attempt == 1:
                raise
            time.sleep(1)


def collect_snapshot(now: datetime | None = None, max_age_seconds: int = 180) -> PremiumSnapshot:
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(fetch_json, url, label) for url, label in (
            (UPBIT_URL, "업비트 BTC 시세"),
            (BINANCE_URL, "바이낸스 BTC 시세"),
            (FX_URL, "Coinbase 기준환율"),
        )]
        domestic, overseas, fx = [future.result() for future in futures]

    observed_at = now or datetime.now(timezone.utc)
    try:
        quote = domestic[0]
        if quote["market"] != "KRW-BTC" or overseas["symbol"] != "BTCUSDT" or fx["data"]["currency"] != "USD":
            raise ValueError("요청한 통화쌍과 API 응답이 다릅니다.")
        timestamps = [
            positive_decimal(quote["timestamp"], "업비트 시각"),
            positive_decimal(overseas["closeTime"], "바이낸스 시각"),
        ]
        now_ms = Decimal(str(observed_at.timestamp())) * 1000
        if any(not -30000 <= now_ms - stamp <= max_age_seconds * 1000 for stamp in timestamps):
            raise ValueError("시세가 오래되었거나 미래 시각을 포함합니다.")
        if abs(timestamps[0] - timestamps[1]) > 60000:
            raise ValueError("거래소 시세 조회 시각 차이가 60초를 넘습니다.")
        rates = fx["data"]["rates"]
        return PremiumSnapshot(
            upbit_krw=positive_decimal(quote["trade_price"], "업비트 가격"),
            binance_usdt=positive_decimal(overseas["lastPrice"], "바이낸스 가격"),
            usd_krw=positive_decimal(rates["KRW"], "USD/KRW"),
            usd_usdt=positive_decimal(rates["USDT"], "USD/USDT"),
            observed_at=observed_at,
        )
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("시세 또는 환율 API 응답에 필수 데이터가 없습니다.") from exc


class BridgeState:
    """KV 조회 실패 시 초기 상태로 대체하지 않아 반복 발송을 막는다."""

    def __init__(self):
        self.base_url = get_required_env("TELEGRAM_MEMORY_BRIDGE_URL").rstrip("/")
        self.token = get_required_env("TELEGRAM_MEMORY_BRIDGE_TOKEN")

    def request(self, path: str, payload: dict) -> dict:
        response = request_json(
            self.base_url + path, method="POST", timeout=15,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            data=json.dumps(payload).encode("utf-8"), label="프리미엄 상태 저장소",
        )
        if not isinstance(response, dict) or response.get("ok") is not True:
            raise RuntimeError("프리미엄 상태 저장소 요청에 실패했습니다.")
        return response

    def get(self) -> dict:
        response = self.request("/state/get", {"key": STATE_KEY})
        if response.get("found") is False:
            return {"active": False}
        if response.get("found") is not True:
            raise RuntimeError("프리미엄 상태 저장소 응답이 올바르지 않습니다.")
        return response.get("value")

    def put(self, state: dict) -> None:
        self.request("/state/put", {"key": STATE_KEY, "value": state})


def build_message(snapshot: PremiumSnapshot, threshold: Decimal) -> str:
    return (
        f"<b>BTC 역프리미엄 알림</b> ({snapshot.observed_at.astimezone(KST):%m/%d %H:%M KST})\n\n"
        f"김치 프리미엄: <b>{snapshot.premium_pct:+.2f}%</b> (기준 {threshold:.2f}% 이하)\n"
        f"업비트: {snapshot.upbit_krw:,.0f}원\n"
        f"바이낸스: {snapshot.binance_usdt:,.2f} USDT\n"
        f"해외 원화 환산: {snapshot.overseas_krw:,.0f}원\n"
        f"Coinbase 기준환율: 1 USD = {snapshot.usd_krw:,.2f}원\n"
        f"USDT 환산: 1 USDT = {1 / snapshot.usd_usdt:.6f} USD\n\n"
        "체결가 비교이며 거래·환전·출금 수수료는 반영하지 않았습니다."
    )


def process_snapshot(snapshot: PremiumSnapshot, config: dict, backend: BridgeState, sender) -> bool:
    threshold = Decimal(str(config.get("threshold_pct", -1)))
    recovery = Decimal(str(config.get("recovery_pct", -0.5)))
    if not threshold.is_finite() or not recovery.is_finite() or recovery <= threshold:
        raise ValueError("회복 기준은 알림 기준보다 커야 하며 유한한 숫자여야 합니다.")
    state = backend.get()
    if not isinstance(state, dict) or type(state.get("active")) is not bool:
        raise ValueError("프리미엄 알림 상태가 올바르지 않습니다.")
    if state["active"]:
        if snapshot.premium_pct >= recovery:
            backend.put({"active": False, "recovered_at": snapshot.observed_at.isoformat()})
            print("역프리미엄 회복: 다음 조건 진입부터 다시 알립니다.")
        return False
    if snapshot.premium_pct > threshold:
        return False
    if not sender(build_message(snapshot, threshold)):
        raise RuntimeError("역프리미엄 텔레그램 전송에 실패했습니다.")
    backend.put({"active": True, "last_alert": snapshot.to_record()})
    return True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="BTC 역프리미엄 텔레그램 모니터")
    parser.add_argument("--dry-run", action="store_true", help="시세만 확인하고 상태 저장·발송 생략")
    args = parser.parse_args(argv)
    config = load_config().get("crypto_premium", {})
    snapshot = collect_snapshot(max_age_seconds=int(config.get("max_quote_age_seconds", 180)))
    print(json.dumps(snapshot.to_record(), ensure_ascii=False, indent=2))
    if args.dry_run:
        print("dry-run: 텔레그램 전송 및 상태 저장 생략")
        return
    sent = process_snapshot(snapshot, config, BridgeState(), send_telegram)
    print("역프리미엄 알림 발송 완료" if sent else "신규 조건 진입 없음: 알림 생략")


if __name__ == "__main__":
    main()
