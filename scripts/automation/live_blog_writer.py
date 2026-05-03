#!/usr/bin/env python3
from __future__ import annotations

"""라이브 transcript 분석 결과를 Hugo 초안으로 변환"""

import re
from datetime import date
from pathlib import Path

try:
    from .live_pipeline_config import CONTENT_POSTS_DIR
except ImportError:
    from live_pipeline_config import CONTENT_POSTS_DIR


def slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:80].strip("-") or f"live-{date.today().isoformat()}"


def render_hugo_draft(
    slug: str,
    title: str,
    summary: str,
    tags: list[str],
    sections: dict[str, str],
) -> str:
    front_matter = [
        "---",
        f'title: "{title}"',
        f"date: {date.today().isoformat()}",
        "draft: true",
        "tags: [" + ", ".join(f'"{tag}"' for tag in tags) + "]",
        'categories: ["AI Engineering"]',
        f'summary: "{summary}"',
        "ShowToc: true",
        "TocOpen: true",
        "---",
        "",
    ]
    body = []
    for heading, content in sections.items():
        body.extend([f"## {heading}", "", str(content).strip(), ""])
    return "\n".join(front_matter + body).strip() + "\n"


def write_hugo_draft(
    *,
    recording_id: str,
    analysis: dict,
    preferred_title: str | None = None,
) -> Path:
    title = preferred_title or (analysis.get("title_candidates") or ["라이브 방송 정리"])[0]
    slug = slugify(title)
    summary = str(analysis.get("summary", "")).strip() or title
    tags = list(dict.fromkeys((analysis.get("keywords") or [])[:5])) or ["AI", "라이브", "개발"]
    sections = analysis.get("blog_sections") or {}
    markdown = render_hugo_draft(
        slug=slug,
        title=title,
        summary=summary,
        tags=tags,
        sections=sections,
    )
    post_dir = CONTENT_POSTS_DIR / slug
    post_dir.mkdir(parents=True, exist_ok=True)
    output_path = post_dir / "index.md"
    output_path.write_text(markdown, encoding="utf-8")
    return output_path
