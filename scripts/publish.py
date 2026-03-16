#!/usr/bin/env python3
"""
Confluence → Hugo 블로그 포스트 반자동 변환 스크립트

사용법:
    python scripts/publish.py \
        --url "https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/12345" \
        --overview "RAG 기반 지식시스템을 구축하면서 겪은 시행착오와 아키텍처 설계 포인트" \
        --tags "RAG,LLM,vLLM"

환경변수:
    CONFLUENCE_URL      - Confluence 인스턴스 URL
    CONFLUENCE_EMAIL    - Confluence 계정 이메일
    CONFLUENCE_TOKEN    - Confluence API 토큰
    LLM_API_URL        - LLM API 엔드포인트 (기본: http://localhost:8000/v1)
    LLM_MODEL          - 사용할 모델명
"""

import argparse
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from textwrap import dedent

# ---------------------------------------------------------------------------
# 1. Confluence 본문 추출
# ---------------------------------------------------------------------------

def fetch_confluence_page(page_url: str) -> dict:
    """Confluence 페이지 URL에서 본문과 메타데이터를 추출합니다."""
    try:
        from atlassian import Confluence
    except ImportError:
        print("atlassian-python-api 패키지가 필요합니다: pip install atlassian-python-api")
        raise

    confluence = Confluence(
        url=os.environ["CONFLUENCE_URL"],
        username=os.environ["CONFLUENCE_EMAIL"],
        password=os.environ["CONFLUENCE_TOKEN"],
        cloud=True,
    )

    # URL에서 page ID 추출
    page_id = extract_page_id(page_url)
    page = confluence.get_page_by_id(page_id, expand="body.storage,version")

    return {
        "title": page["title"],
        "content": page["body"]["storage"]["value"],
        "version": page["version"]["number"],
    }


def extract_page_id(url: str) -> str:
    """Confluence URL에서 page ID를 추출합니다."""
    # /pages/12345/... 형태
    match = re.search(r"/pages/(\d+)", url)
    if match:
        return match.group(1)
    # /pages/viewpage.action?pageId=12345
    match = re.search(r"pageId=(\d+)", url)
    if match:
        return match.group(1)
    raise ValueError(f"Confluence URL에서 page ID를 추출할 수 없습니다: {url}")


# ---------------------------------------------------------------------------
# 2. LLM으로 블로그 초안 생성
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = dedent("""\
    당신은 기술 블로그 작가입니다.
    사내 기술 문서를 외부 블로그용 마크다운으로 변환하세요.

    규칙:
    - 사내 고유명사, 내부 URL, 민감 정보는 반드시 제거하거나 일반화
    - 기술적 인사이트와 실무 경험 중심으로 재구성
    - 한국어로 작성
    - Hugo front matter는 포함하지 말 것 (별도 생성됨)
    - 마크다운 형식으로 출력
    - 코드 블록이 있으면 언어 태그 포함
""")


def generate_blog_post(overview: str, page_content: str) -> str:
    """LLM을 사용하여 블로그 초안을 생성합니다."""
    try:
        from openai import OpenAI
    except ImportError:
        print("openai 패키지가 필요합니다: pip install openai")
        raise

    api_url = os.environ.get("LLM_API_URL", "http://localhost:8000/v1")
    model = os.environ.get("LLM_MODEL", "default")

    client = OpenAI(base_url=api_url, api_key=os.environ.get("LLM_API_KEY", "none"))

    user_prompt = f"""
[작성자가 제공한 개요]:
{overview}

[Confluence 원본 (HTML)]:
{page_content[:8000]}

위 내용을 바탕으로 기술 블로그 글을 작성해주세요.
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=4000,
    )

    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# 3. Hugo 포스트 저장
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """한글/영문 텍스트를 URL-safe slug로 변환합니다."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80].strip("-")


def save_hugo_post(
    title: str,
    content: str,
    tags: list[str],
    category: str = "AI Engineering",
    summary: str = "",
) -> Path:
    """Hugo 포스트를 content/posts/ 디렉토리에 저장합니다."""
    blog_root = Path(__file__).resolve().parent.parent
    slug = slugify(title)
    today = datetime.now().strftime("%Y-%m-%d")

    post_dir = blog_root / "content" / "posts" / slug
    post_dir.mkdir(parents=True, exist_ok=True)

    front_matter = dedent(f"""\
        ---
        title: "{title}"
        date: {today}
        draft: true
        tags: {tags}
        categories: ["{category}"]
        summary: "{summary}"
        ShowToc: true
        TocOpen: true
        ---
    """)

    post_path = post_dir / "index.md"
    post_path.write_text(front_matter + "\n" + content, encoding="utf-8")

    print(f"\n포스트가 생성되었습니다: {post_path}")
    print(f"  - draft: true 상태입니다. 검수 후 draft: false로 변경하세요.")
    print(f"  - 미리보기: cd {blog_root} && hugo server -D")

    return post_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Confluence 문서 → Hugo 블로그 포스트 변환"
    )
    parser.add_argument("--url", required=True, help="Confluence 페이지 URL")
    parser.add_argument("--overview", required=True, help="블로그 글 방향/개요 (한 줄)")
    parser.add_argument("--tags", default="", help="태그 (쉼표 구분)")
    parser.add_argument("--category", default="AI Engineering", help="카테고리")
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="LLM 변환 건너뛰기 (Confluence 원본 HTML 그대로 저장)",
    )
    args = parser.parse_args()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    # Step 1: Confluence 추출
    print(f"[1/3] Confluence 페이지 추출 중... ({args.url})")
    page = fetch_confluence_page(args.url)
    print(f"  - 제목: {page['title']}")

    # Step 2: LLM 변환
    if args.skip_llm:
        print("[2/3] LLM 변환 건너뜀 (--skip-llm)")
        blog_content = page["content"]
    else:
        print("[2/3] LLM으로 블로그 초안 생성 중...")
        blog_content = generate_blog_post(args.overview, page["content"])

    # Step 3: 저장
    print("[3/3] Hugo 포스트 저장 중...")
    post_path = save_hugo_post(
        title=page["title"],
        content=blog_content,
        tags=tags,
        category=args.category,
        summary=args.overview,
    )

    print(f"\n완료! 다음 단계:")
    print(f"  1. {post_path} 파일을 검수/편집하세요")
    print(f"  2. front matter의 draft: true → false로 변경")
    print(f"  3. git add && git commit && git push")
    print(f"  4. GitHub Actions가 자동으로 빌드·배포합니다")


if __name__ == "__main__":
    main()
