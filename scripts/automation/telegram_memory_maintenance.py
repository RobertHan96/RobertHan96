#!/usr/bin/env python3
from __future__ import annotations

"""텔레그램 메모리 일일 요약/유지보수"""

import argparse
from datetime import date, datetime, timedelta, timezone

from telegram_memory import save_daily_memory_summary

KST = timezone(timedelta(hours=9))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="대상 날짜 (YYYY-MM-DD)")
    parser.add_argument("--yesterday", action="store_true", help="어제 날짜 요약")
    return parser.parse_args()


def resolve_target_date(args: argparse.Namespace) -> date:
    if args.date:
        return date.fromisoformat(args.date)
    if args.yesterday:
        return (datetime.now(KST) - timedelta(days=1)).date()
    return datetime.now(KST).date()


def main() -> None:
    args = parse_args()
    target_date = resolve_target_date(args)
    result = save_daily_memory_summary(target_date)
    if result:
        print(f"텔레그램 메모리 요약 저장 완료: {result['path']}")
    else:
        print(f"요약할 텔레그램 메모리 로그가 없습니다: {target_date.isoformat()}")


if __name__ == "__main__":
    main()
