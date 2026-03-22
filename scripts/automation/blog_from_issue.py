#!/usr/bin/env python3
from __future__ import annotations

"""
GitHub Issue Form -> Hugo 포스트 생성 스크립트
"""

import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

KST = timezone(timedelta(hours=9))
FIELD_ORDER = [
    "글 제목",
    "슬러그",
    "한 줄 요약",
    "태그",
    "카테고리",
    "발행 방식",
    "본문",
]
DEFAULT_CATEGORY = "AI Engineering"
MANAGED_FRONT_MATTER_KEYS = {
    "title",
    "date",
    "lastmod",
    "draft",
    "tags",
    "categories",
    "summary",
    "ShowToc",
    "TocOpen",
    "issue_id",
    "issue_url",
    "issue_author",
}


def slugify(text: str) -> str:
    """한글/영문 텍스트를 URL-safe slug로 변환"""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:80].strip("-")


def parse_iso_date(value: str | None) -> datetime:
    """GitHub ISO 시간을 KST datetime으로 변환"""
    if not value:
        return datetime.now(KST)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(KST)


def normalize_issue_value(value: str) -> str:
    """Issue form placeholder 제거"""
    normalized = value.strip()
    if normalized == "_No response_":
        return ""
    return normalized


def parse_issue_form(body: str) -> dict[str, str]:
    """Issue form body를 섹션별로 분리"""
    text = body.replace("\r\n", "\n").strip()
    sections: dict[str, str] = {}

    positions = []
    for label in FIELD_ORDER:
        match = re.search(rf"^###\s+{re.escape(label)}\s*$", text, re.MULTILINE)
        if match:
            positions.append((label, match.start(), match.end()))

    if not positions:
        raise ValueError("블로그 Issue Form 본문을 찾지 못했습니다.")

    for index, (label, _start, end) in enumerate(positions):
        next_start = positions[index + 1][1] if index + 1 < len(positions) else len(text)
        value = text[end:next_start].strip()
        sections[label] = normalize_issue_value(value)

    return sections


def parse_csv_field(value: str, default: list[str] | None = None) -> list[str]:
    """쉼표 구분 문자열을 리스트로 변환"""
    items = [item.strip() for item in value.split(",") if item.strip()]
    if items:
        return items
    return list(default or [])


def extract_front_matter(content: str) -> tuple[dict, str]:
    """마크다운에서 front matter와 본문 분리"""
    if not content.startswith("---\n"):
        return {}, content

    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return {}, content

    try:
        front_matter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}, content

    return front_matter, parts[2].lstrip("\n")


def load_existing_post(post_path: Path) -> tuple[dict, str]:
    """기존 포스트가 있으면 front matter/body 로드"""
    if not post_path.exists():
        return {}, ""
    return extract_front_matter(post_path.read_text(encoding="utf-8"))


def find_existing_post(posts_dir: Path, issue_number: int) -> Path | None:
    """issue_id로 기존 포스트 검색"""
    for post_path in posts_dir.glob("*/index.md"):
        front_matter, _ = load_existing_post(post_path)
        if front_matter.get("issue_id") == issue_number:
            return post_path
    return None


def build_front_matter(
    existing_front_matter: dict,
    issue: dict,
    sections: dict[str, str],
    draft: bool,
    title: str,
    summary: str,
    tags: list[str],
    categories: list[str],
) -> dict:
    """포스트 front matter 조합"""
    preserved = {
        key: value
        for key, value in existing_front_matter.items()
        if key not in MANAGED_FRONT_MATTER_KEYS
    }

    created_at = parse_iso_date(issue.get("created_at"))
    updated_at = parse_iso_date(issue.get("updated_at"))
    original_date = existing_front_matter.get("date") or created_at.strftime("%Y-%m-%d")

    preserved.update({
        "title": title,
        "date": str(original_date),
        "lastmod": updated_at.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "draft": draft,
        "tags": tags,
        "categories": categories,
        "summary": summary,
        "ShowToc": True,
        "TocOpen": True,
        "issue_id": issue["number"],
        "issue_url": issue["html_url"],
        "issue_author": issue["user"]["login"],
    })

    return preserved


def render_post(front_matter: dict, body: str) -> str:
    """Hugo 포스트 렌더링"""
    yaml_text = yaml.safe_dump(
        front_matter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()
    return f"---\n{yaml_text}\n---\n\n{body.strip()}\n"


def write_outputs(outputs: dict[str, str]) -> None:
    """GitHub Actions output 기록"""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return

    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in outputs.items():
            handle.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue Form으로 Hugo 포스트 생성")
    parser.add_argument("--event-path", required=True, help="GitHub event JSON path")
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).resolve().parent.parent.parent),
        help="블로그 루트 디렉토리",
    )
    args = parser.parse_args()

    root_dir = Path(args.root_dir).resolve()
    posts_dir = root_dir / "content" / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)

    event = json.loads(Path(args.event_path).read_text(encoding="utf-8"))
    issue = event["issue"]
    body = issue.get("body") or ""
    sections = parse_issue_form(body)

    title = sections.get("글 제목", "").strip()
    summary = sections.get("한 줄 요약", "").strip()
    content = sections.get("본문", "").strip()
    slug = slugify(sections.get("슬러그", "").strip() or title)
    tags = parse_csv_field(sections.get("태그", ""))
    categories = parse_csv_field(
        sections.get("카테고리", ""),
        default=[DEFAULT_CATEGORY],
    )
    publish_mode = sections.get("발행 방식", "").strip()
    draft = publish_mode != "즉시 발행"

    if not title:
        raise ValueError("'글 제목' 값이 비어 있습니다.")
    if not summary:
        raise ValueError("'한 줄 요약' 값이 비어 있습니다.")
    if not content:
        raise ValueError("'본문' 값이 비어 있습니다.")
    if not slug:
        raise ValueError("슬러그를 생성할 수 없습니다.")

    existing_post = find_existing_post(posts_dir, issue["number"])
    desired_dir = posts_dir / slug

    if existing_post is not None:
        current_dir = existing_post.parent
        if current_dir != desired_dir:
            if desired_dir.exists():
                raise FileExistsError(f"이미 사용 중인 슬러그입니다: {slug}")
            current_dir.rename(desired_dir)
        post_path = desired_dir / "index.md"
    else:
        if desired_dir.exists():
            existing_front_matter, _ = load_existing_post(desired_dir / "index.md")
            if existing_front_matter.get("issue_id") != issue["number"]:
                raise FileExistsError(f"이미 사용 중인 슬러그입니다: {slug}")
        desired_dir.mkdir(parents=True, exist_ok=True)
        post_path = desired_dir / "index.md"

    existing_front_matter, _existing_body = load_existing_post(post_path)
    front_matter = build_front_matter(
        existing_front_matter=existing_front_matter,
        issue=issue,
        sections=sections,
        draft=draft,
        title=title,
        summary=summary,
        tags=tags,
        categories=categories,
    )
    rendered = render_post(front_matter, content)
    post_path.write_text(rendered, encoding="utf-8")

    relative_post_path = post_path.relative_to(root_dir)
    print(f"포스트 생성/수정 완료: {relative_post_path}")
    write_outputs({
        "post_path": str(relative_post_path),
        "slug": slug,
        "draft": str(draft).lower(),
        "title": title,
    })


if __name__ == "__main__":
    main()
