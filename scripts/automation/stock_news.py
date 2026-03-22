#!/usr/bin/env python3
"""
태스크1: 관심 종목 뉴스 모니터링
- 네이버 뉴스 검색 API로 관심 종목 키워드 뉴스 수집
- 매 2시간마다 실행 (08~22시 KST)
- 텔레그램으로 발송
"""

import html
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime

from config.loader import load_config
from notify import send_telegram


def search_naver_news(keyword: str, display: int = 3) -> list[dict]:
    """네이버 뉴스 검색 API (최신순)"""
    client_id = os.environ["NAVER_CLIENT_ID"]
    client_secret = os.environ["NAVER_CLIENT_SECRET"]

    url = "https://openapi.naver.com/v1/search/news.json?" + urllib.parse.urlencode({
        "query": keyword,
        "display": display,
        "sort": "date",
    })

    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", client_id)
    req.add_header("X-Naver-Client-Secret", client_secret)

    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        return data.get("items", [])


def clean_html(text: str) -> str:
    """HTML 태그 및 엔티티 제거"""
    import re
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    return text.strip()


def build_message(results: dict[str, list]) -> str:
    """텔레그램 발송 메시지 생성"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"<b>📰 관심 종목 뉴스</b> ({now})\n"]

    for keyword, articles in results.items():
        if not articles:
            continue
        lines.append(f"<b>▸ {html.escape(keyword)}</b>")
        for a in articles:
            title = html.escape(clean_html(a["title"]))
            link = a["originallink"] or a["link"]
            safe_link = html.escape(link, quote=True)
            lines.append(f"  • <a href=\"{safe_link}\">{title}</a>")
        lines.append("")

    if len(lines) <= 1:
        return ""  # 뉴스 없음

    return "\n".join(lines)


def main():
    config = load_config()
    keywords = config["stock_news"]["keywords"]

    results = {}
    for kw in keywords:
        try:
            articles = search_naver_news(kw)
            results[kw] = articles
        except Exception as e:
            print(f"[{kw}] 검색 실패: {e}")
            results[kw] = []

    message = build_message(results)
    if message:
        send_telegram(message)
        print("뉴스 알림 발송 완료")
    else:
        print("새 뉴스 없음, 발송 건너뜀")


if __name__ == "__main__":
    main()
