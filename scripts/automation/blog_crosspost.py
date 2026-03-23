#!/usr/bin/env python3
"""
태스크8: 블로깅 봇 - Hugo -> Dev.to 크로스포스팅
- 최근 7일 내 새로 추가된 Hugo 포스트 감지
- Dev.to API로 draft 게시
- 주 1회 월요일 09:00 KST
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from notify import send_telegram
from runtime import get_required_env

KST = timezone(timedelta(hours=9))
BLOG_ROOT = Path(__file__).resolve().parent.parent.parent
DEVTO_API_KEY = os.environ.get("DEVTO_API_KEY", "")

# Hugo 블로그의 GitHub Pages URL (canonical URL용)
BLOG_BASE_URL = os.environ.get("BLOG_BASE_URL", "")


def get_recent_posts(days: int = 7) -> list[dict]:
    """최근 N일 내 추가된 Hugo 포스트 조회 (front matter 기준)"""
    posts_dir = BLOG_ROOT / "content" / "posts"
    cutoff = datetime.now(KST).date() - timedelta(days=days)

    recent = []
    for post_dir in posts_dir.iterdir():
        if not post_dir.is_dir():
            continue
        index_md = post_dir / "index.md"
        if not index_md.exists():
            continue

        content = index_md.read_text(encoding="utf-8")
        front_matter = extract_front_matter(content)

        if not front_matter:
            continue
        if front_matter.get("draft", False):
            continue

        post_date_str = str(front_matter.get("date", ""))
        try:
            post_date = datetime.strptime(post_date_str[:10], "%Y-%m-%d").date()
        except ValueError:
            continue

        if post_date >= cutoff:
            body = content.split("---", 2)[-1].strip() if "---" in content else content
            recent.append({
                "title": front_matter.get("title", post_dir.name),
                "date": post_date_str[:10],
                "tags": front_matter.get("tags", []),
                "body": body,
                "slug": post_dir.name,
                "description": front_matter.get("description", ""),
            })

    return recent


def extract_front_matter(content: str) -> dict | None:
    """마크다운에서 YAML front matter 추출"""
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def post_to_devto(
    title: str,
    body: str,
    tags: list[str],
    api_key: str,
    description: str = "",
    canonical_url: str = "",
) -> str | None:
    """Dev.to API로 글 게시 (draft), 게시된 URL 반환"""
    # Dev.to 태그: 소문자, 영숫자+하이픈만, 최대 4개
    clean_tags = []
    for tag in tags[:4]:
        cleaned = tag.lower().replace(" ", "").replace("_", "")
        if cleaned:
            clean_tags.append(cleaned)

    article_data = {
        "article": {
            "title": title,
            "body_markdown": body,
            "published": False,  # draft로 게시
            "tags": clean_tags,
        }
    }

    if description:
        article_data["article"]["description"] = description[:150]
    if canonical_url:
        article_data["article"]["canonical_url"] = canonical_url

    data = json.dumps(article_data).encode()

    req = urllib.request.Request(
        "https://dev.to/api/articles",
        data=data,
        method="POST",
    )
    req.add_header("api-key", api_key)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/vnd.forem.api-v1+json")

    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        return result.get("url")


def build_message(posted: list[dict]) -> str:
    """텔레그램 알림 메시지"""
    lines = ["<b>✍️ 블로그 크로스포스팅 완료</b>\n"]
    for p in posted:
        lines.append(f"  • <b>{p['title']}</b>")
        if p.get("devto_url"):
            lines.append(f"    Dev.to: {p['devto_url']} (draft)")
    return "\n".join(lines)


def main():
    print("최근 7일 내 새 포스트 확인 중...")
    posts = get_recent_posts(days=7)

    if not posts:
        print("새 포스트 없음, 건너뜀")
        return

    print(f"{len(posts)}개 새 포스트 발견")
    api_key = get_required_env("DEVTO_API_KEY")

    posted = []
    failures = 0
    for post in posts:
        canonical = ""
        if BLOG_BASE_URL:
            canonical = f"{BLOG_BASE_URL.rstrip('/')}/posts/{post['slug']}/"

        try:
            url = post_to_devto(
                title=post["title"],
                body=post["body"],
                tags=post["tags"],
                api_key=api_key,
                description=post["description"],
                canonical_url=canonical,
            )
            posted.append({
                "title": post["title"],
                "devto_url": url,
            })
            print(f"[Dev.to] {post['title']} -> {url}")
        except Exception as e:
            print(f"[Dev.to] {post['title']} 실패: {e}")
            failures += 1

    if posts and failures == len(posts):
        raise RuntimeError("Dev.to 게시가 모두 실패했습니다.")

    if posted:
        message = build_message(posted)
        send_telegram(message)
        print("크로스포스팅 알림 발송 완료")


if __name__ == "__main__":
    main()
