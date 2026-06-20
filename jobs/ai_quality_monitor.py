from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin

from playwright.sync_api import Page, sync_playwright

try:
    from scripts.automation.notify import send_telegram
except Exception:  # pragma: no cover - jobs 단독 실행 허용
    send_telegram = None

from .ai_quality_profile import AI_QUALITY_CANDIDATE, AI_QUALITY_SEED_ROLES
from .core import JobPosting, build_match, clean_lines, get_first_env, safe_goto, score_text, shrink

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_DIR = ROOT_DIR / "jobs" / "reports"
DEFAULT_STATE_PATH = ROOT_DIR / "data" / "job_monitors" / "ai_quality_state.json"
KST = dt.timezone(dt.timedelta(hours=9))
HIGH_FIT_SEEN_KEY = "ai-quality/high-fit-seen"
SUMMARY_KEY_PREFIX = "ai-quality/summary"
HIGH_FIT_TTL_SECONDS = 60 * 60 * 24 * 180
SUMMARY_TTL_SECONDS = 60 * 60 * 24 * 14
WANTED_BASE_URL = "https://www.wanted.co.kr"
WANTED_JOB_URL = "https://www.wanted.co.kr/wd/{job_id}"

AI_HINTS = (
    "ai",
    "artificial intelligence",
    "llm",
    "language model",
    "generative ai",
    "gen ai",
    "모델",
    "생성형",
    "인공지능",
    "ai service",
    "ai 서비스",
)
QUALITY_HINTS = (
    "quality",
    "품질",
    "qa",
    "quality assurance",
    "evaluation",
    "eval",
    "평가",
    "validation",
    "검증",
    "safety",
    "안전성",
    "red team",
    "red teaming",
    "benchmark",
    "testing",
    "test",
    "테스트",
)
ROLE_SIGNAL_GROUPS: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("AI 서비스 품질", ("ai 서비스 품질", "ai quality", "service quality"), 24),
    ("안전성", ("안전성", "safety", "trust & safety", "responsible ai"), 22),
    ("평가", ("평가", "evaluation", "eval", "benchmark", "validation"), 18),
    ("LLM", ("llm", "prompt", "model behavior", "language model"), 12),
    ("QA", ("qa", "testing", "test engineer", "테스트 엔지니어"), 8),
    ("Red Teaming", ("red team", "red teaming"), 12),
)
ROLE_PENALTY_GROUPS: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("제조 품질", ("공정", "생산", "출하", "manufacturing", "supplier quality", "협력사"), 28),
    ("일반 품질보증", ("품질보증", "quality control", "inspection", "audit"), 18),
    ("일반 게임 QA", ("game qa", "게임qa", "게임 qa"), 15),
)
SEED_SIGNAL_GROUPS: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("카카오뱅크형", ("ai 서비스 품질", "안전성 평가", "ai quality & safety"), 28),
    ("LG형", ("ai 품질 엔지니어", "품질관리자", "서비스 품질"), 24),
    ("평가형", ("llm evaluation", "prompt evaluation", "model evaluation"), 18),
)
WANTED_SEARCH_TERMS = (
    "AI 품질",
    "AI Quality",
    "LLM",
    "AI Safety",
)


@dataclass(frozen=True)
class BrowserSource:
    name: str
    url: str
    selector: str
    parser: Callable[[Page, int], list[JobPosting]]


@dataclass
class AIQualityMatch:
    job: JobPosting
    fit_score: int
    role_score: int
    seed_score: int
    total_score: int
    matched_keywords: list[str]
    role_hits: list[str]
    penalties: list[str]
    project_hits: list[str]
    reason: str
    motivation_essay: str
    strengths_essay: str
    llm_used: bool

    def to_record(self) -> dict:
        return {
            "job_key": build_job_key(self.job),
            "source": self.job.source,
            "company": self.job.company,
            "title": self.job.title or self.job.detail_title,
            "url": self.job.url,
            "score": self.total_score,
            "fit_score": self.fit_score,
            "role_score": self.role_score,
            "seed_score": self.seed_score,
            "reason": self.reason,
            "project_hits": self.project_hits,
            "matched_keywords": self.matched_keywords,
            "role_hits": self.role_hits,
            "found_at": now_kst().isoformat(),
        }


def now_kst() -> dt.datetime:
    return dt.datetime.now(KST)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results


def bracket_company(title: str, fallback: str) -> str:
    match = re.match(r"^\[([^\]]+)\]", (title or "").strip())
    if match:
        return match.group(1).strip()
    return fallback


def build_job_key(job: JobPosting) -> str:
    if job.url:
        return f"{job.source}:{job.url}"
    title = re.sub(r"[^0-9A-Za-z가-힣]+", "-", (job.title or job.detail_title).lower()).strip("-")
    company = re.sub(r"[^0-9A-Za-z가-힣]+", "-", (job.company or "").lower()).strip("-")
    return f"{job.source}:{company}:{title}"


def role_text_for_scoring(job: JobPosting) -> str:
    parts = [
        job.title,
        job.company,
        job.card_meta,
        job.raw_card_text,
        job.detail_title,
    ]
    return "\n".join(part for part in parts if part)


def extract_naver_anno_id(onclick: str) -> str:
    match = re.search(r"show\('(\d+)'\)", onclick or "")
    return match.group(1) if match else ""


def score_role_relevance(text: str) -> tuple[int, list[str], list[str]]:
    lowered = normalize_text(text).lower()
    score = 0
    matched: list[str] = []
    penalized: list[str] = []

    ai_context = any(keyword in lowered for keyword in AI_HINTS)
    quality_context = any(keyword in lowered for keyword in QUALITY_HINTS)
    if ai_context and quality_context:
        score += 30
        matched.append("AI+품질/평가 조합")

    for label, keywords, weight in ROLE_SIGNAL_GROUPS:
        if any(keyword in lowered for keyword in keywords):
            score += weight
            matched.append(label)

    for label, keywords, weight in ROLE_PENALTY_GROUPS:
        if any(keyword in lowered for keyword in keywords):
            score -= weight
            penalized.append(label)

    if "qa" in lowered and not ai_context:
        score -= 18
        penalized.append("AI 없는 일반 QA")

    if not ai_context:
        score -= 8

    return max(0, min(100, score)), unique_preserve_order(matched), unique_preserve_order(penalized)


def score_seed_similarity(text: str) -> tuple[int, list[str]]:
    lowered = normalize_text(text).lower()
    score = 0
    hits: list[str] = []
    for label, keywords, weight in SEED_SIGNAL_GROUPS:
        if any(keyword in lowered for keyword in keywords):
            score += weight
            hits.append(label)
    for seed in AI_QUALITY_SEED_ROLES:
        company = str(seed["company"]).lower()
        if company and company in lowered:
            score += 4
            hits.append(str(seed["company"]))
    return max(0, min(100, score)), unique_preserve_order(hits)


def compose_total_score(fit_score: int, role_score: int, seed_score: int) -> int:
    blended = round((fit_score * 0.45) + (role_score * 0.40) + (seed_score * 0.15))
    return max(0, min(100, blended))


def build_reason(role_hits: list[str], penalties: list[str], fit_reason: str) -> str:
    parts: list[str] = []
    if role_hits:
        parts.append(f"{', '.join(role_hits[:3])} 문맥이 강합니다")
    if penalties:
        parts.append(f"{penalties[0]} 성격 공고와는 구분됩니다")
    cleaned_fit_reason = normalize_text(fit_reason).rstrip(".")
    if cleaned_fit_reason:
        parts.append(cleaned_fit_reason)
    if not parts:
        return "포트폴리오와 직접 연결되는 AI 품질 역할입니다."
    return " / ".join(parts[:3])


def html_escape(text: str) -> str:
    return html.escape(text or "", quote=False)


def build_immediate_message(records: list[dict], date_label: str) -> str:
    if not records:
        return ""
    lines = [f"<b>🎯 AI 품질 고적합 공고</b> ({date_label})", ""]
    for item in records:
        lines.extend(
            [
                f"- <b>{html_escape(item.get('company') or '-')}</b> | {html_escape(item.get('title') or '-')}"
                f" ({item.get('score', 0)}점)",
                f"  {html_escape(item.get('reason') or '')}",
                f"  {html_escape(item.get('url') or '')}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def build_daily_summary_message(
    records: list[dict],
    *,
    high_fit_score: int,
    date_label: str,
) -> str:
    lines = [f"<b>🧭 AI 품질 공고 일일 요약</b> ({date_label})", ""]
    if not records:
        lines.append("오늘 새로 포착한 AI 품질 관련 공고가 없습니다.")
        return "\n".join(lines)

    high_fit = [item for item in records if int(item.get("score", 0)) >= high_fit_score]
    review = [item for item in records if int(item.get("score", 0)) < high_fit_score]

    if high_fit:
        lines.append("<b>고적합</b>")
        for item in high_fit:
            lines.append(
                f"- {html_escape(item.get('company') or '-')} | {html_escape(item.get('title') or '-')}"
                f" ({item.get('score', 0)}점)"
            )
            lines.append(f"  {html_escape(item.get('reason') or '')}")
            lines.append(f"  {html_escape(item.get('url') or '')}")
        lines.append("")

    if review:
        lines.append("<b>추가 검토</b>")
        for item in review:
            lines.append(
                f"- {html_escape(item.get('company') or '-')} | {html_escape(item.get('title') or '-')}"
                f" ({item.get('score', 0)}점)"
            )
            lines.append(f"  {html_escape(item.get('reason') or '')}")
            lines.append(f"  {html_escape(item.get('url') or '')}")

    return "\n".join(lines).strip()


def merge_summary_records(existing: list[dict], new_records: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for item in existing + new_records:
        key = str(item.get("job_key") or "")
        if not key:
            continue
        current = merged.get(key)
        if current is None or int(item.get("score", 0)) > int(current.get("score", 0)):
            merged[key] = item
    return sorted(
        merged.values(),
        key=lambda item: (-int(item.get("score", 0)), item.get("company", ""), item.get("title", "")),
    )


def load_json_url(url: str, *, headers: dict[str, str] | None = None, label: str) -> dict:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read() or b"{}")
            return payload if isinstance(payload, dict) else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{label} [{exc.code}] {url}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"{label} 실패 [{url}]: {exc}") from exc


def fetch_wanted_job_detail(job_id: str) -> dict:
    url = f"{WANTED_BASE_URL}/api/v4/jobs/{job_id}"
    data = load_json_url(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        label="Wanted 상세 조회",
    )
    return data.get("job", {}) if isinstance(data, dict) else {}


def summarize_wanted_detail(job_detail: dict) -> str:
    detail = job_detail.get("detail") or {}
    parts = []
    for field in ("main_tasks", "requirements", "intro"):
        value = normalize_text(detail.get(field, ""))
        if value:
            parts.append(value)
    return shrink(" / ".join(parts), 900)


def scrape_wanted(limit: int) -> list[JobPosting]:
    results: list[JobPosting] = []
    seen_ids: set[str] = set()
    for keyword in WANTED_SEARCH_TERMS:
        query = urllib.parse.urlencode(
            {
                "query": keyword,
                "limit": max(limit, 20),
                "offset": 0,
                "country": "kr",
                "sort": "latest",
            }
        )
        url = f"{WANTED_BASE_URL}/api/v4/jobs?{query}"
        data = load_json_url(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            label=f"Wanted 검색 [{keyword}]",
        )
        for item in data.get("data", []):
            job_id = str(item.get("id") or "").strip()
            if not job_id or job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            detail = fetch_wanted_job_detail(job_id)
            title = normalize_text(item.get("position", ""))
            company = normalize_text((item.get("company") or {}).get("name", ""))
            summary = summarize_wanted_detail(detail)
            posting = JobPosting(
                source="wanted",
                url=WANTED_JOB_URL.format(job_id=job_id),
                raw_card_text=normalize_text(" ".join([title, company, keyword])),
                title=title,
                company=company,
                card_meta=keyword,
                detail_title=title,
                detail_text=summary,
            )
            results.append(posting)
            if len(results) >= limit:
                return results
    return results


def collect_unique_anchor_jobs(
    page: Page,
    selector: str,
    limit: int,
    builder: Callable[[Page, int], JobPosting | None],
) -> list[JobPosting]:
    anchors = page.locator(selector)
    results: list[JobPosting] = []
    seen_urls: set[str] = set()
    count = anchors.count()
    for idx in range(count):
        posting = builder(page, idx)
        if posting is None:
            continue
        if posting.url in seen_urls:
            continue
        seen_urls.add(posting.url)
        results.append(posting)
        if len(results) >= limit:
            break
    return results


def build_kakao_posting(page: Page, idx: int) -> JobPosting | None:
    anchor = page.locator("a[href^='/jobs/P-']").nth(idx)
    href = anchor.get_attribute("href")
    if not href:
        return None
    raw_text = normalize_text(anchor.inner_text(timeout=5_000))
    lines = clean_lines(raw_text)
    title = lines[0] if lines else ""
    if not title:
        return None
    return JobPosting(
        source="kakao",
        url=urljoin(page.url, href),
        raw_card_text=raw_text,
        title=title,
        company="카카오",
        card_meta=" ".join(lines[1:6]),
    )


def scrape_kakao(page: Page, limit: int) -> list[JobPosting]:
    safe_goto(
        page,
        "https://careers.kakao.com/jobs?skillSet=&page=1&company=KAKAO&part=TECHNOLOGY&employeeType=&keyword=",
    )
    page.wait_for_selector("a[href^='/jobs/P-']", timeout=60_000)
    return collect_unique_anchor_jobs(page, "a[href^='/jobs/P-']", limit, build_kakao_posting)


def build_kakaobank_posting(page: Page, idx: int) -> JobPosting | None:
    anchor = page.locator("a[href^='/jobs/']").nth(idx)
    href = anchor.get_attribute("href")
    if not href or not re.search(r"/jobs/\d+", href):
        return None
    raw_text = normalize_text(anchor.inner_text(timeout=5_000))
    lines = clean_lines(raw_text)
    title = lines[0] if lines else ""
    if not title or "인재풀 등록하기" in title:
        return None
    return JobPosting(
        source="kakaobank",
        url=urljoin(page.url, href),
        raw_card_text=raw_text,
        title=title,
        company="카카오뱅크",
        card_meta=" ".join(lines[1:5]),
    )


def scrape_kakaobank(page: Page, limit: int) -> list[JobPosting]:
    safe_goto(page, "https://recruit.kakaobank.com/jobs?recruitClassNames=AI")
    page.wait_for_selector("a[href^='/jobs/']", timeout=60_000)
    return collect_unique_anchor_jobs(page, "a[href^='/jobs/']", limit, build_kakaobank_posting)


def build_naver_posting(page: Page, idx: int) -> JobPosting | None:
    anchor = page.locator("a.card_link").nth(idx)
    onclick = anchor.get_attribute("onclick") or ""
    anno_id = extract_naver_anno_id(onclick)
    if not anno_id:
        return None
    raw_text = normalize_text(anchor.inner_text(timeout=5_000))
    title = normalize_text(anchor.locator(".card_title").inner_text(timeout=5_000))
    company = bracket_company(title, "NAVER")
    return JobPosting(
        source="naver",
        url=f"https://recruit.navercorp.com/rcrt/view.do?annoId={anno_id}&lang=ko",
        raw_card_text=raw_text,
        title=title,
        company=company,
        card_meta=raw_text.replace(title, "", 1).strip(),
    )


def scrape_naver(page: Page, limit: int) -> list[JobPosting]:
    safe_goto(
        page,
        "https://recruit.navercorp.com/rcrt/list.do?subJobCdArr=&sysCompanyCdArr=&empTypeCdArr=&entTypeCdArr=&workAreaCdArr=&sw=",
    )
    page.wait_for_selector("a.card_link", timeout=60_000)
    return collect_unique_anchor_jobs(page, "a.card_link", limit, build_naver_posting)


def build_autoever_posting(page: Page, idx: int) -> JobPosting | None:
    anchor = page.locator("a[href^='/ko/o/']").nth(idx)
    href = anchor.get_attribute("href")
    if not href:
        return None
    raw_text = normalize_text(anchor.inner_text(timeout=5_000))
    lines = clean_lines(raw_text)
    title = lines[0] if lines else ""
    if not title:
        return None
    return JobPosting(
        source="autoever",
        url=urljoin(page.url, href),
        raw_card_text=raw_text,
        title=title,
        company="현대오토에버",
        card_meta=" ".join(lines[1:5]),
    )


def scrape_autoever(page: Page, limit: int) -> list[JobPosting]:
    safe_goto(page, "https://career.hyundai-autoever.com/ko/apply")
    page.wait_for_selector("a[href^='/ko/o/']", timeout=60_000)
    return collect_unique_anchor_jobs(page, "a[href^='/ko/o/']", limit, build_autoever_posting)


def build_kt_posting(page: Page, idx: int) -> JobPosting | None:
    anchor = page.locator("a[href^='/careers/']").nth(idx)
    href = anchor.get_attribute("href")
    if not href or not re.search(r"/careers/\d+", href):
        return None
    raw_text = normalize_text(anchor.inner_text(timeout=5_000))
    title = raw_text
    date_match = re.search(r"\d{4}\.\d{2}\.\d{2}\s*~", raw_text)
    if date_match:
        title = raw_text[: date_match.start()].strip()
    company = bracket_company(title, "KT")
    return JobPosting(
        source="kt",
        url=urljoin(page.url, href),
        raw_card_text=raw_text,
        title=title,
        company=company,
        card_meta=raw_text.replace(title, "", 1).strip(),
    )


def scrape_kt(page: Page, limit: int) -> list[JobPosting]:
    safe_goto(page, "https://recruit.kt.com/careers")
    page.wait_for_selector("a[href^='/careers/']", timeout=60_000)
    return collect_unique_anchor_jobs(page, "a[href^='/careers/']", limit, build_kt_posting)


def build_sk_posting(page: Page, idx: int) -> JobPosting | None:
    anchor = page.locator("a[href*='/Recruit/Detail/']").nth(idx)
    href = anchor.get_attribute("href")
    if not href or "/Recruit/Detail/" not in href:
        return None
    raw_text = normalize_text(anchor.inner_text(timeout=5_000))
    if len(raw_text) < 20:
        return None
    title = raw_text
    for marker in ("May ", "June ", "July ", "August ", "September ", "October ", "November ", "December ", "January ", "February ", "March ", "April "):
        if marker in raw_text:
            title = raw_text.split(marker, 1)[0].strip()
            break
    company = bracket_company(title, "SK")
    return JobPosting(
        source="sk",
        url=href if href.startswith("http") else urljoin(page.url, href),
        raw_card_text=raw_text,
        title=title,
        company=company,
        card_meta=raw_text.replace(title, "", 1).strip(),
    )


def scrape_sk(page: Page, limit: int) -> list[JobPosting]:
    safe_goto(page, "https://www.skcareers.com/Recruit")
    page.wait_for_selector("a[href*='/Recruit/Detail/']", timeout=60_000)
    return collect_unique_anchor_jobs(page, "a[href*='/Recruit/Detail/']", limit, build_sk_posting)


def build_hybe_posting(page: Page, idx: int) -> JobPosting | None:
    anchor = page.locator("a[href^='/ko/o/']").nth(idx)
    href = anchor.get_attribute("href")
    if not href:
        return None
    raw_text = normalize_text(anchor.inner_text(timeout=5_000))
    lines = clean_lines(raw_text)
    title = lines[0] if lines else ""
    if not title:
        return None
    company = bracket_company(title, "HYBE")
    return JobPosting(
        source="hybe",
        url=urljoin(page.url, href),
        raw_card_text=raw_text,
        title=title,
        company=company,
        card_meta=" ".join(lines[1:5]),
    )


def scrape_hybe(page: Page, limit: int) -> list[JobPosting]:
    safe_goto(page, "https://careers.hybecorp.com/ko/career?occupations=%EA%B8%B0%EC%88%A0")
    page.wait_for_selector("a[href^='/ko/o/']", timeout=60_000)
    return collect_unique_anchor_jobs(page, "a[href^='/ko/o/']", limit, build_hybe_posting)


BROWSER_SOURCES: tuple[tuple[str, Callable[[Page, int], list[JobPosting]]], ...] = (
    ("카카오", scrape_kakao),
    ("카카오뱅크", scrape_kakaobank),
    ("NAVER", scrape_naver),
    ("현대오토에버", scrape_autoever),
    ("KT", scrape_kt),
    ("SK", scrape_sk),
    ("HYBE", scrape_hybe),
)


def enrich_detail_generic(page: Page, job: JobPosting) -> None:
    if job.detail_text:
        return
    safe_goto(page, job.url)
    body_text = normalize_text(page.locator("body").inner_text(timeout=15_000))
    job.detail_title = page.title()
    job.detail_text = shrink(body_text, 9_000)


def collect_jobs(limit_per_site: int) -> tuple[list[JobPosting], list[str]]:
    jobs: list[JobPosting] = []
    errors: list[str] = []

    try:
        items = scrape_wanted(limit_per_site)
        jobs.extend(items)
        print(f"[Wanted] 목록 수집 완료: {len(items)}건")
    except Exception as exc:
        message = f"[Wanted] 목록 수집 실패: {exc}"
        print(message)
        errors.append(message)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 2200})
        for label, scraper in BROWSER_SOURCES:
            try:
                items = scraper(page, limit_per_site)
                jobs.extend(items)
                print(f"[{label}] 목록 수집 완료: {len(items)}건")
            except Exception as exc:
                message = f"[{label}] 목록 수집 실패: {exc}"
                print(message)
                errors.append(message)
        browser.close()

    deduped: dict[str, JobPosting] = {}
    for job in jobs:
        key = build_job_key(job)
        current = deduped.get(key)
        if current is None or len(job.combined_text) > len(current.combined_text):
            deduped[key] = job
    return list(deduped.values()), errors


def quick_rank(job: JobPosting) -> int:
    role_text = role_text_for_scoring(job)
    role_score, _, _ = score_role_relevance(role_text)
    seed_score, _ = score_seed_similarity(role_text)
    fit_hint, _ = score_text(role_text, AI_QUALITY_CANDIDATE)
    return role_score + seed_score + min(fit_hint, 30)


def build_ai_quality_match(job: JobPosting) -> AIQualityMatch:
    fit_match = build_match(job, AI_QUALITY_CANDIDATE)
    role_text = role_text_for_scoring(job)
    role_score, role_hits, penalties = score_role_relevance(role_text)
    seed_score, seed_hits = score_seed_similarity(role_text)
    fit_score = max(0, min(100, fit_match.score))
    total_score = compose_total_score(fit_score, role_score, seed_score)
    matched_keywords = unique_preserve_order(fit_match.matched_keywords + seed_hits)
    reason = build_reason(role_hits, penalties, fit_match.quick_reason)
    return AIQualityMatch(
        job=job,
        fit_score=fit_score,
        role_score=role_score,
        seed_score=seed_score,
        total_score=total_score,
        matched_keywords=matched_keywords,
        role_hits=role_hits,
        penalties=penalties,
        project_hits=fit_match.project_hits,
        reason=reason,
        motivation_essay=fit_match.motivation_essay,
        strengths_essay=fit_match.strengths_essay,
        llm_used=fit_match.llm_used,
    )


def resolve_bridge_state_base_url() -> str:
    return get_first_env("TELEGRAM_MEMORY_BRIDGE_URL", "JOB_FIT_REPORT_BRIDGE_URL").rstrip("/")


def resolve_bridge_state_token() -> str:
    return get_first_env("TELEGRAM_MEMORY_BRIDGE_TOKEN", "JOB_FIT_REPORT_BRIDGE_TOKEN")


class StateBackend:
    def __init__(self, local_path: Path | None = None) -> None:
        self.base_url = resolve_bridge_state_base_url()
        self.token = resolve_bridge_state_token()
        self.local_path = Path(
            os.environ.get("AI_QUALITY_STATE_FILE", str(local_path or DEFAULT_STATE_PATH))
        )

    def get(self, key: str, default):
        if self.base_url and self.token:
            try:
                value = self._bridge_get(key)
                return default if value is None else value
            except Exception as exc:
                print(f"브리지 상태 조회 실패, 로컬 fallback 사용: {exc}")
        state = self._load_local_state()
        return state.get(key, default)

    def put(self, key: str, value, ttl_seconds: int | None = None) -> None:
        if self.base_url and self.token:
            try:
                self._bridge_put(key, value, ttl_seconds=ttl_seconds)
                return
            except Exception as exc:
                print(f"브리지 상태 저장 실패, 로컬 fallback 사용: {exc}")
        state = self._load_local_state()
        state[key] = value
        self._save_local_state(state)

    def _bridge_get(self, key: str):
        request = urllib.request.Request(
            self.base_url + "/state/get",
            data=json.dumps({"key": key}, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read() or b"{}")
            if not payload.get("ok"):
                raise RuntimeError(str(payload))
            if not payload.get("found"):
                return None
            return payload.get("value")

    def _bridge_put(self, key: str, value, ttl_seconds: int | None = None) -> None:
        payload = {"key": key, "value": value}
        if ttl_seconds:
            payload["ttl_seconds"] = ttl_seconds
        request = urllib.request.Request(
            self.base_url + "/state/put",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read() or b"{}")
            if not body.get("ok"):
                raise RuntimeError(str(body))

    def _load_local_state(self) -> dict:
        if not self.local_path.exists():
            return {}
        try:
            return json.loads(self.local_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_local_state(self, state: dict) -> None:
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        self.local_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def summary_key_for(date_label: str) -> str:
    return f"{SUMMARY_KEY_PREFIX}/{date_label}"


def run_monitor(limit_per_site: int, detail_top_n: int, min_score: int) -> list[AIQualityMatch]:
    jobs, scrape_errors = collect_jobs(limit_per_site)
    if not jobs and scrape_errors:
        raise RuntimeError("AI 품질 채용공고 source 수집이 모두 실패했습니다.")

    ranked = sorted(jobs, key=quick_rank, reverse=True)
    detail_targets = ranked[:detail_top_n]

    detail_errors: list[str] = []
    detail_jobs = [job for job in detail_targets if job.source != "wanted"]
    if detail_jobs:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 2200})
            for job in detail_jobs:
                try:
                    enrich_detail_generic(page, job)
                except Exception as exc:
                    message = f"[{job.source}] 상세 수집 실패: {job.url} ({exc})"
                    print(message)
                    detail_errors.append(message)
            browser.close()

    if scrape_errors:
        print("부분 수집 실패:")
        for error in scrape_errors:
            print(f"- {error}")
    if detail_errors:
        print("부분 상세 수집 실패:")
        for error in detail_errors[:10]:
            print(f"- {error}")

    matches = [build_ai_quality_match(job) for job in detail_targets]
    matches.sort(key=lambda item: item.total_score, reverse=True)
    return [match for match in matches if match.total_score >= min_score]


def render_report(matches: list[AIQualityMatch], mode: str) -> str:
    now = now_kst().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# AI Quality Job Monitor Report",
        "",
        f"- 생성 시각: {now}",
        f"- 실행 모드: {mode}",
        f"- 후보자: {AI_QUALITY_CANDIDATE.name}",
        f"- 핵심 역할: AI 품질 / AI 안전성 평가 / 모델 평가 / AI QA",
        "",
    ]
    if not matches:
        lines.append("조건에 맞는 공고를 찾지 못했습니다.")
        return "\n".join(lines)
    for idx, match in enumerate(matches, start=1):
        lines.extend(
            [
                f"## {idx}. {match.job.title or match.job.detail_title}",
                f"- 회사: {match.job.company or '-'}",
                f"- 소스: {match.job.source}",
                f"- 최종 점수: {match.total_score}",
                f"- Fit / Role / Seed: {match.fit_score} / {match.role_score} / {match.seed_score}",
                f"- URL: {match.job.url}",
                f"- 사유: {match.reason}",
                f"- 프로젝트 연결: {', '.join(match.project_hits) or '-'}",
                f"- 키워드: {', '.join(match.matched_keywords[:10]) or '-'}",
                "",
            ]
        )
    return "\n".join(lines)


def save_report(report: str, mode: str) -> Path:
    stamp = now_kst().strftime("%Y%m%d_%H%M%S")
    path = DEFAULT_REPORT_DIR / f"ai_quality_report_{mode}_{stamp}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    return path


def send_message_if_available(message: str) -> None:
    if not message:
        return
    if send_telegram is None:
        print("send_telegram import에 실패해 텔레그램 전송을 건너뜁니다.")
        return
    send_telegram(message)


def handle_immediate_alerts(
    matches: list[AIQualityMatch],
    *,
    backend: StateBackend,
    high_fit_score: int,
    notify_limit: int,
) -> list[dict]:
    seen = set(str(item) for item in backend.get(HIGH_FIT_SEEN_KEY, []))
    new_high_fit: list[dict] = []
    for match in matches:
        if match.total_score < high_fit_score:
            continue
        record = match.to_record()
        if record["job_key"] in seen:
            continue
        new_high_fit.append(record)
        seen.add(record["job_key"])
    backend.put(
        HIGH_FIT_SEEN_KEY,
        list(seen)[-1000:],
        ttl_seconds=HIGH_FIT_TTL_SECONDS,
    )
    return new_high_fit[:notify_limit]


def persist_summary_candidates(
    matches: list[AIQualityMatch],
    *,
    backend: StateBackend,
    summary_score: int,
    date_label: str,
) -> list[dict]:
    existing = backend.get(summary_key_for(date_label), [])
    new_records = [match.to_record() for match in matches if match.total_score >= summary_score]
    merged = merge_summary_records(existing if isinstance(existing, list) else [], new_records)
    backend.put(
        summary_key_for(date_label),
        merged,
        ttl_seconds=SUMMARY_TTL_SECONDS,
    )
    return merged


def drain_summary_candidates(
    matches: list[AIQualityMatch],
    *,
    backend: StateBackend,
    summary_score: int,
    high_fit_score: int,
    summary_limit: int,
    date_label: str,
) -> list[dict]:
    merged = persist_summary_candidates(
        matches,
        backend=backend,
        summary_score=summary_score,
        date_label=date_label,
    )
    selected = [
        record for record in merged
        if int(record.get("score", 0)) < high_fit_score
    ][:summary_limit]
    seen = set(str(item) for item in backend.get(HIGH_FIT_SEEN_KEY, []))
    for record in merged:
        if int(record.get("score", 0)) >= high_fit_score:
            seen.add(str(record.get("job_key", "")))
    backend.put(HIGH_FIT_SEEN_KEY, list(seen)[-1000:], ttl_seconds=HIGH_FIT_TTL_SECONDS)
    backend.put(summary_key_for(date_label), [], ttl_seconds=SUMMARY_TTL_SECONDS)
    return selected


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI 품질 채용공고 모니터링")
    parser.add_argument("--mode", choices=("immediate", "summary", "dry-run"), default="dry-run")
    parser.add_argument("--limit-per-site", type=int, default=20, help="소스별 목록 수집 개수")
    parser.add_argument("--detail-top-n", type=int, default=12, help="상위 상세 수집 개수")
    parser.add_argument("--min-score", type=int, default=60, help="리포트 최소 점수")
    parser.add_argument("--high-fit-score", type=int, default=85, help="즉시 알림 최소 점수")
    parser.add_argument("--summary-score", type=int, default=65, help="일일 요약 최소 점수")
    parser.add_argument("--notify-limit", type=int, default=5, help="즉시 알림 최대 개수")
    parser.add_argument("--summary-limit", type=int, default=12, help="요약 최대 개수")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    matches = run_monitor(
        limit_per_site=args.limit_per_site,
        detail_top_n=args.detail_top_n,
        min_score=args.min_score,
    )
    report = render_report(matches, mode=args.mode)
    path = save_report(report, mode=args.mode)
    date_label = now_kst().strftime("%Y-%m-%d")
    backend = StateBackend()

    if args.mode == "immediate":
        persist_summary_candidates(
            matches,
            backend=backend,
            summary_score=args.summary_score,
            date_label=date_label,
        )
        records = handle_immediate_alerts(
            matches,
            backend=backend,
            high_fit_score=args.high_fit_score,
            notify_limit=args.notify_limit,
        )
        message = build_immediate_message(records, date_label)
        if message:
            send_message_if_available(message)
        else:
            print("신규 고적합 AI 품질 공고가 없어 즉시 알림을 생략합니다.")
    elif args.mode == "summary":
        records = drain_summary_candidates(
            matches,
            backend=backend,
            summary_score=args.summary_score,
            high_fit_score=args.high_fit_score,
            summary_limit=args.summary_limit,
            date_label=date_label,
        )
        message = build_daily_summary_message(
            records,
            high_fit_score=args.high_fit_score,
            date_label=date_label,
        )
        send_message_if_available(message)
    else:
        top_records = [match.to_record() for match in matches[: args.summary_limit]]
        print(json.dumps(top_records, ensure_ascii=False, indent=2))

    print(path)


if __name__ == "__main__":
    main()
