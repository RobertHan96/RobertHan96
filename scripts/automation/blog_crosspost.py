#!/usr/bin/env python3
"""
태스크8: 블로깅 봇 - Hugo → 미디움 크로스포스팅
- 최근 7일 내 새로 추가된 Hugo 포스트 감지
- 미디움 API로 자동 게시
- 주 1회 월요일 09:00 KST
"""

import json
import os
import subprocess
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from notify import send_telegram

KST = timezone(timedelta(hours=9))
BLOG_ROOT = Path(__file__).resolve().parent.parent.parent


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


def post_to_medium(title: str, body: str, tags: list[str]) -> str | None:
    """미디움 API로 글 게시, 게시된 URL 반환"""
    token = os.environ["MEDIUM_TOKEN"]

    # 1. 사용자 ID 조회
    user_req = urllib.request.Request("https://api.medium.com/v1/me")
    user_req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(user_req, timeout=10) as resp:
        user_data = json.loads(resp.read())
        user_id = user_data["data"]["id"]

    # 2. 글 게시
    post_data = json.dumps({
        "title": title,
        "contentFormat": "markdown",
        "content": f"# {title}\n\n{body}",
        "tags": tags[:5],  # 미디움 최대 5개 태그
        "publishStatus": "draft",  # 초안으로 게시 (검수 후 public으로 변경)
    }).encode()

    post_req = urllib.request.Request(
        f"https://api.medium.com/v1/users/{user_id}/posts",
        data=post_data,
        method="POST",
    )
    post_req.add_header("Authorization", f"Bearer {token}")
    post_req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(post_req, timeout=15) as resp:
        result = json.loads(resp.read())
        return result["data"].get("url")


def build_message(posted: list[dict]) -> str:
    """텔레그램 알림 메시지"""
    lines = ["<b>✍️ 블로그 크로스포스팅 완료</b>\n"]
    for p in posted:
        lines.append(f"  • <b>{p['title']}</b>")
        if p.get("medium_url"):
            lines.append(f"    미디움: {p['medium_url']} (draft)")
    return "\n".join(lines)


def main():
    print("최근 7일 내 새 포스트 확인 중...")
    posts = get_recent_posts(days=7)

    if not posts:
        print("새 포스트 없음, 건너뜀")
        return

    print(f"{len(posts)}개 새 포스트 발견")

    posted = []
    for post in posts:
        result = {"title": post["title"]}

        # 미디움
        if os.environ.get("MEDIUM_TOKEN"):
            try:
                url = post_to_medium(post["title"], post["body"], post["tags"])
                result["medium_url"] = url
                print(f"[미디움] {post['title']} → {url}")
            except Exception as e:
                print(f"[미디움] {post['title']} 실패: {e}")

        posted.append(result)

    if posted:
        message = build_message(posted)
        send_telegram(message)
        print("크로스포스팅 알림 발송 완료")


if __name__ == "__main__":
    main()
