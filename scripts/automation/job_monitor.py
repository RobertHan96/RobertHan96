#!/usr/bin/env python3
from __future__ import annotations

"""
태스크7: 채용공고 모니터링
- 원티드 API로 AI/ML 관련 채용공고 검색
- 직행 API로 AI/LLM/RAG 관련 채용공고 조회
- 채용공고 본문에서 주요 업무 중심으로 요약해 전달
- 매일 10:00 KST 발송
"""

import html
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from config.loader import load_config
from notify import send_telegram
from runtime import request_json

KST = timezone(timedelta(hours=9))
ZIGHANG_BASE_URL = "https://api.zighang.com/api"
WANTED_JOB_URL = "https://www.wanted.co.kr/wd/{job_id}"


def wanted_request(url: str) -> dict:
    """Wanted API 요청"""
    data = request_json(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
        label="Wanted API 요청",
    )
    return data if isinstance(data, dict) else {}


def wanted_html_request(url: str) -> str:
    """Wanted 웹 페이지 HTML 요청"""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        raise RuntimeError(f"Wanted 페이지 요청 실패 [{url}]: {exc}") from exc


def zighang_request(path: str, query: list[tuple[str, str]] | None = None) -> dict:
    """직행 API 요청"""
    url = f"{ZIGHANG_BASE_URL}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"

    data = request_json(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        timeout=15,
        label=f"직행 API 요청 [{path}]",
    )
    return data if isinstance(data, dict) else {}


def clean_lines(text: str) -> list[str]:
    """본문 텍스트를 줄 단위로 정리"""
    cleaned = []
    for raw_line in (text or "").splitlines():
        line = " ".join(raw_line.replace("•", " ").replace("-", " ").split())
        if line:
            cleaned.append(line)
    return cleaned


def shorten_text(text: str, limit: int = 120) -> str:
    """긴 텍스트 축약"""
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def dedupe_preserve_order(items: list[str]) -> list[str]:
    """순서를 유지하며 중복 제거"""
    seen = set()
    results = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        results.append(item)
    return results


def summarize_job_detail(job_detail: dict) -> str:
    """채용 본문을 주요 업무 중심으로 요약"""
    detail = job_detail.get("detail") or {}
    task_lines = clean_lines(detail.get("main_tasks", ""))
    requirement_lines = clean_lines(detail.get("requirements", ""))
    intro_lines = clean_lines(detail.get("intro", ""))

    summary_parts = []
    if task_lines:
        summary_parts.append("주요 업무: " + ", ".join(task_lines[:3]))
    if requirement_lines:
        summary_parts.append("요건: " + ", ".join(requirement_lines[:2]))
    elif intro_lines:
        summary_parts.append("설명: " + shorten_text(intro_lines[0], 90))

    if not summary_parts:
        return "본문 요약 정보가 없습니다."

    return shorten_text(" / ".join(summary_parts), 180)


def parse_iso_date_to_kst(value: str) -> datetime | None:
    """ISO 날짜/시간 문자열을 KST datetime으로 변환"""
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST)


def fetch_wanted_posted_date(job_id: int | str) -> datetime | None:
    """Wanted 공고 페이지에서 datePosted 추출"""
    html_text = wanted_html_request(WANTED_JOB_URL.format(job_id=job_id))
    match = re.search(r'"datePosted":"([0-9]{4}-[0-9]{2}-[0-9]{2})"', html_text)
    if not match:
        confirm_match = re.search(r'"confirm_time":"([0-9]{4}-[0-9]{2}-[0-9]{2})"', html_text)
        if not confirm_match:
            return None
        return parse_iso_date_to_kst(confirm_match.group(1))
    return parse_iso_date_to_kst(match.group(1))


def extract_rich_text(node: dict | list | None) -> str:
    """ProseMirror JSON 노드에서 텍스트 추출"""
    if node is None:
        return ""
    if isinstance(node, list):
        return " ".join(filter(None, (extract_rich_text(item) for item in node))).strip()
    if not isinstance(node, dict):
        return str(node).strip()
    if node.get("type") == "text":
        return str(node.get("text", "")).strip()
    return " ".join(
        filter(None, (extract_rich_text(child) for child in node.get("content", [])))
    ).strip()


def extract_zighang_sections(doc: dict | None) -> list[tuple[str, list[str]]]:
    """직행 summary/content JSON을 heading/bullet 섹션으로 정리"""
    if not isinstance(doc, dict):
        return []

    sections: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        cleaned = dedupe_preserve_order([line for line in current_lines if line])
        if current_heading or cleaned:
            sections.append((current_heading, cleaned))
        current_lines = []

    for node in doc.get("content", []):
        node_type = node.get("type")
        if node_type == "heading":
            flush()
            current_heading = extract_rich_text(node)
        elif node_type in {"bulletList", "orderedList"}:
            for item in node.get("content", []):
                text = extract_rich_text(item)
                if text:
                    current_lines.append(text)
        elif node_type == "paragraph":
            text = extract_rich_text(node)
            if text:
                current_lines.append(text)
        else:
            text = extract_rich_text(node)
            if text:
                current_lines.append(text)

    flush()
    return sections


def format_career_range(career_min: int | None, career_max: int | None) -> str:
    """경력 범위 포맷"""
    min_value = career_min or 0
    max_value = career_max or 0
    if min_value == 0 and max_value == 0:
        return "경력무관/신입 가능"
    if min_value == 0:
        return f"{max_value}년 이하"
    if max_value == 0:
        return f"{min_value}년 이상"
    return f"{min_value}~{max_value}년"


def parse_zighang_created_at(value: str) -> datetime | None:
    """직행 createdAt 문자열을 KST datetime으로 변환"""
    if not value:
        return None

    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST)


def summarize_zighang_job_detail(job_detail: dict, fallback_item: dict) -> str:
    """직행 채용 상세를 주요 업무 중심으로 요약"""
    summary_doc = job_detail.get("summary") or fallback_item.get("summary")
    content_doc = job_detail.get("content") or {}
    sections = extract_zighang_sections(summary_doc) or extract_zighang_sections(content_doc)

    task_lines: list[str] = []
    requirement_lines: list[str] = []
    other_lines: list[str] = []

    for heading, lines in sections:
        normalized = heading.replace(" ", "").lower()
        if any(keyword in normalized for keyword in ["주요업무", "담당업무", "업무", "responsibil", "role"]):
            task_lines.extend(lines)
        elif any(keyword in normalized for keyword in ["자격요건", "지원자격", "필수요건", "requirements", "qualification"]):
            requirement_lines.extend(lines)
        else:
            other_lines.extend(lines)

    task_lines = dedupe_preserve_order(task_lines)
    requirement_lines = dedupe_preserve_order(requirement_lines)
    other_lines = dedupe_preserve_order(other_lines)

    summary_parts = []
    if task_lines:
        summary_parts.append("주요 업무: " + ", ".join(task_lines[:3]))
    elif other_lines:
        summary_parts.append("주요 내용: " + ", ".join(other_lines[:3]))

    if requirement_lines:
        summary_parts.append("요건: " + ", ".join(requirement_lines[:2]))

    depth_twos = fallback_item.get("depthTwos") or []
    keywords = fallback_item.get("keywords") or []
    if depth_twos:
        summary_parts.append("분야: " + ", ".join(depth_twos[:3]))
    if keywords:
        summary_parts.append("키워드: " + ", ".join(keywords[:2]))

    if not summary_parts:
        summary_parts.append(
            "분야: "
            + ", ".join(dedupe_preserve_order((fallback_item.get("depthTwos") or [])[:3]))
        )

    return shorten_text(" / ".join(filter(None, summary_parts)), 200)


def fetch_wanted_job_detail(job_id: int | str) -> dict:
    """원티드 채용공고 상세 조회"""
    url = f"https://www.wanted.co.kr/api/v4/jobs/{job_id}"

    try:
        data = wanted_request(url)
        return data.get("job", {}) or {}
    except Exception as e:
        print(f"원티드 상세 조회 실패 [{job_id}]: {e}")
        return {}


def search_wanted_jobs(
    keyword: str,
    *,
    limit: int = 5,
    size: int = 20,
    sort: str = "latest",
    today_only: bool = True,
) -> list[dict]:
    """원티드 채용공고 검색 (비공식 API)"""
    url = "https://www.wanted.co.kr/api/v4/jobs?" + urllib.parse.urlencode({
        "query": keyword,
        "limit": size,
        "offset": 0,
        "country": "kr",
        "sort": sort,
    })

    data = wanted_request(url)
    jobs = []
    today = datetime.now(KST).date()
    for item in data.get("data", []):
        job_id = item.get("id", "")
        if today_only:
            posted_at = fetch_wanted_posted_date(job_id)
            if posted_at is None or posted_at.date() != today:
                continue

        detail = fetch_wanted_job_detail(job_id)
        jobs.append({
            "id": job_id,
            "source": "Wanted",
            "title": item.get("position", ""),
            "company": item.get("company", {}).get("name", ""),
            "link": WANTED_JOB_URL.format(job_id=job_id),
            "summary": summarize_job_detail(detail),
        })
        if len(jobs) >= limit:
            break
    return jobs


def fetch_zighang_job_detail(job_id: str) -> dict:
    """직행 채용공고 상세 조회"""
    data = zighang_request(f"recruitments/{job_id}")
    if data.get("success") is False and not data.get("data"):
        raise RuntimeError(data.get("message") or "직행 상세 조회 실패")
    return data.get("data") or {}


def search_zighang_jobs(source: dict) -> tuple[str, list[dict]]:
    """직행 채용공고 검색"""
    label = source.get("label") or "직행 AI 채용"
    page = int(source.get("page", 0))
    size = int(source.get("size", 20))
    max_results = int(source.get("max_results", 5))
    today_only = bool(source.get("today_only", False))
    depth_twos = source.get("depth_twos") or []

    query: list[tuple[str, str]] = [
        ("page", str(page)),
        ("size", str(size)),
        ("careerMin", str(source.get("career_min", 0))),
        ("careerMax", str(source.get("career_max", 10))),
        ("includeCareerOpen", str(source.get("include_career_open", True)).lower()),
        ("sortCondition", str(source.get("sort_condition", "LATEST"))),
        ("orderCondition", str(source.get("order_condition", "DESC"))),
    ]
    for depth_two in depth_twos:
        query.append(("depthTwos", str(depth_two)))

    data = zighang_request("recruitments/v3", query=query)
    if data.get("success") is False and not data.get("data"):
        raise RuntimeError(data.get("message") or "직행 채용공고 조회 실패")

    content = (data.get("data") or {}).get("content") or []
    today = datetime.now(KST).date()

    jobs = []
    for item in content:
        job_id = item.get("id", "")
        created_at = parse_zighang_created_at(str(item.get("createdAt") or ""))
        if today_only and (created_at is None or created_at.date() != today):
            continue
        detail = fetch_zighang_job_detail(job_id) if job_id else {}
        company = (item.get("company") or {}).get("name", "")
        career_label = format_career_range(item.get("careerMin"), item.get("careerMax"))
        region_label = ", ".join(item.get("regions") or [])
        meta_bits = [bit for bit in [career_label, region_label] if bit]
        if detail.get("deadlineType") or item.get("deadlineType"):
            meta_bits.append(str(detail.get("deadlineType") or item.get("deadlineType")))

        summary = summarize_zighang_job_detail(detail, item)
        if meta_bits:
            summary = shorten_text(f"{summary} / 기본 정보: {', '.join(meta_bits)}", 220)

        jobs.append({
            "id": job_id,
            "source": "직행",
            "title": item.get("title", ""),
            "company": company,
            "link": item.get("redirectUrl") or f"https://zighang.com/recruitment/{job_id}",
            "summary": summary,
        })
        if len(jobs) >= max_results:
            break

    return label, jobs


def build_message(results: dict[str, list]) -> str:
    """텔레그램 메시지 생성"""
    now = datetime.now(KST).strftime("%Y-%m-%d")
    lines = [f"<b>💼 채용공고 모니터링</b> ({now})\n"]

    has_jobs = False
    for keyword, jobs in results.items():
        if not jobs:
            continue

        has_jobs = True
        lines.append(f"<b>▸ {html.escape(keyword)}</b>")
        for job in jobs:
            lines.append(
                f"  • <a href=\"{job['link']}\">{html.escape(job['title'])}</a>\n"
                f"    🏢 {html.escape(job['company'])}\n"
                f"    🧷 {html.escape(job.get('source', ''))}\n"
                f"    🧩 {html.escape(job['summary'])}"
            )
        lines.append("")

    if not has_jobs:
        return ""

    return "\n".join(lines).rstrip()


def main():
    config = load_config()
    sources = config["job_monitor"]["sources"]

    results = {}
    attempted = 0
    failures = 0
    for src in sources:
        source_name = (src.get("name") or "").strip().lower()

        if source_name == "zighang":
            attempted += 1
            label = src.get("label") or "직행 AI 채용"
            try:
                result_label, jobs = search_zighang_jobs(src)
                results[result_label] = jobs
                print(f"[{result_label}] {len(jobs)}건")
            except Exception as e:
                print(f"직행 검색 실패 [{label}]: {e}")
                results[label] = []
                failures += 1
            continue

        for keyword in src.get("keywords", []):
            attempted += 1
            try:
                jobs = search_wanted_jobs(
                    keyword,
                    limit=int(src.get("max_results", 5)),
                    size=int(src.get("size", 20)),
                    sort=str(src.get("sort", "latest")),
                    today_only=bool(src.get("today_only", True)),
                )
                results[keyword] = jobs
                print(f"[{keyword}] {len(jobs)}건")
            except Exception as e:
                print(f"원티드 검색 실패 [{keyword}]: {e}")
                results[keyword] = []
                failures += 1

    if attempted and failures == attempted:
        raise RuntimeError("채용공고 검색이 모두 실패했습니다.")

    message = build_message(results)
    if message:
        send_telegram(message)
        print("채용공고 알림 발송 완료")
    else:
        print("새 채용공고 없음")


if __name__ == "__main__":
    main()
