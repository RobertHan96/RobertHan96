#!/usr/bin/env python3
"""
기술 뉴스 수집/요약 유틸리티 (GeekNews, PyTorch Korea)
- 태스크1 관심 종목 뉴스 모니터링의 일일 기술 뉴스 섹션에서 재사용
- 필요시 단독 실행도 가능
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from html import escape
from html.parser import HTMLParser

from config.loader import load_config
from notify import send_telegram

KST = timezone(timedelta(hours=9))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TECH_NEWS_MODEL = (
    os.environ.get("OPENAI_MODEL", "").strip()
    or os.environ.get("TECH_NEWS_MODEL", "").strip()
    or "gpt-4o-mini"
)


class TextExtractor(HTMLParser):
    """HTML에서 텍스트만 추출"""

    def __init__(self):
        super().__init__()
        self.texts = []

    def handle_data(self, data):
        self.texts.append(data.strip())

    def get_text(self):
        return " ".join(t for t in self.texts if t)


def html_to_text(html: str) -> str:
    extractor = TextExtractor()
    extractor.feed(html)
    return extractor.get_text()


def fetch_hada_new(hours: int = 24) -> list[dict]:
    """GeekNews (hada.io) /new 페이지에서 최근 글 수집 via RSS"""
    import feedparser

    feed = feedparser.parse("https://news.hada.io/rss/news")
    import time

    cutoff = time.time() - (hours * 3600)

    entries = []
    for entry in feed.entries[:20]:
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            entry_time = time.mktime(published)
            if entry_time < cutoff:
                continue

        description = entry.get("summary", "") or entry.get("description", "")
        entries.append({
            "title": entry.get("title", "제목 없음"),
            "link": entry.get("link", ""),
            "content": html_to_text(description)[:500],
        })

    return entries


def fetch_pytorch_kr(hours: int = 24) -> list[dict]:
    """PyTorch Korea Discourse 포럼에서 최근 뉴스 글 수집 (JSON API)"""
    url = "https://discuss.pytorch.kr/c/news/14.json"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"PyTorch Korea 수집 실패: {e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    entries = []

    for topic in data.get("topic_list", {}).get("topics", [])[:20]:
        created = topic.get("created_at", "")
        if not created:
            continue

        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if created_dt < cutoff:
            continue

        topic_id = topic.get("id", "")
        excerpt = topic.get("excerpt", "") or ""

        entries.append({
            "title": topic.get("title", "제목 없음"),
            "link": f"https://discuss.pytorch.kr/t/{topic.get('slug', '')}/{topic_id}",
            "content": html_to_text(excerpt)[:500],
        })

    return entries


def summarize_with_openai(entries: list[dict]) -> list[dict]:
    """OpenAI GPT로 각 글 한줄 요약"""
    if not OPENAI_API_KEY or not entries:
        return entries

    texts = []
    for i, e in enumerate(entries):
        texts.append(f"[{i+1}] 제목: {e['title']}\n내용: {e['content']}")

    prompt = (
        "아래 기술 뉴스 목록을 각각 한국어 1~2문장으로 핵심만 요약해줘.\n"
        "형식: [번호] 요약내용\n\n"
        + "\n\n".join(texts)
    )

    body = json.dumps({
        "model": TECH_NEWS_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1024,
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]

        summaries = {}
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # [1] 요약... 형태 파싱
            if line.startswith("[") and "]" in line:
                idx_str = line[1:line.index("]")]
                try:
                    idx = int(idx_str) - 1
                    summaries[idx] = line[line.index("]") + 1:].strip()
                except ValueError:
                    pass

        for i, e in enumerate(entries):
            if i in summaries:
                e["summary"] = summaries[i]

    except Exception as e:
        print(f"OpenAI 요약 실패: {e}")

    return entries


def build_message(results: dict[str, list]) -> str:
    """텔레그램 발송 메시지 생성"""
    now = datetime.now(KST).strftime("%Y-%m-%d")
    lines = [f"<b>🔧 기술 뉴스 브리핑</b> ({now})\n"]

    has_news = False
    for source, entries in results.items():
        if not entries:
            continue
        has_news = True
        lines.append(f"<b>▸ {escape(source)}</b>")
        for e in entries[:7]:
            safe_link = escape(e["link"], quote=True)
            safe_title = escape(e["title"])
            title_line = f"  • <a href=\"{safe_link}\">{safe_title}</a>"
            lines.append(title_line)
            summary = e.get("summary", "")
            if summary:
                lines.append(f"    → {escape(summary)}")
        lines.append("")

    if not has_news:
        return ""

    return "\n".join(lines)


FETCHERS = {
    "GeekNews": fetch_hada_new,
    "PyTorch Korea": fetch_pytorch_kr,
}


def main():
    config = load_config()
    sources = config["tech_news"]["sources"]

    results = {}
    failures = 0
    for src in sources:
        name = src["name"]
        fetcher = FETCHERS.get(name)
        if not fetcher:
            print(f"[{name}] 알 수 없는 소스, 건너뜀")
            failures += 1
            continue

        try:
            entries = fetcher()
            entries = summarize_with_openai(entries)
            results[name] = entries
            print(f"[{name}] {len(entries)}건 수집 + 요약 완료")
        except Exception as e:
            print(f"[{name}] 수집 실패: {e}")
            results[name] = []
            failures += 1

    if sources and failures == len(sources):
        raise RuntimeError("기술 뉴스 소스 조회가 모두 실패했습니다.")

    message = build_message(results)
    if message:
        send_telegram(message)
        print("기술 뉴스 알림 발송 완료")
    else:
        print("새 뉴스 없음")


if __name__ == "__main__":
    main()
