from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urljoin

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - 의존성 미설치 허용
    OpenAI = None

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - 의존성 미설치 허용
    PdfReader = None

try:
    from scripts.automation.notify import send_telegram
except Exception:  # pragma: no cover - jobs 단독 실행 허용
    send_telegram = None

try:
    from .profile import CANDIDATE, CandidateProfile, ProjectProfile
except ImportError:
    try:
        from jobs.profile import CANDIDATE, CandidateProfile, ProjectProfile
    except ImportError:
        from profile import CANDIDATE, CandidateProfile, ProjectProfile


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_DIR = str(ROOT_DIR / "jobs" / "reports")
REPORT_DIR = Path(os.environ.get("JOB_MONITOR_REPORT_DIR", DEFAULT_REPORT_DIR))
REPORT_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_NOTIFY_MIN_SCORE = 80
CONTEXT_TEXT_FILES = (
    ROOT_DIR / "content" / "about" / "index.md",
    ROOT_DIR / "README.md",
    ROOT_DIR / "content" / "posts" / "rag-knowledge-system" / "index.md",
    ROOT_DIR / "content" / "posts" / "confluence-to-blog-pipeline" / "index.md",
    ROOT_DIR / "resume.md",
)
PORTFOLIO_PDF_FILES = (
    ROOT_DIR / "한영신_AI Engineering Portfolio.pdf",
    ROOT_DIR / "portfolio.pdf",
    ROOT_DIR / "resume.pdf",
)
ASSISTANT_CONTEXT_HINTS = (
    "후보자는 AI Engineer, LLM Engineer, Agent Engineer, Enterprise AI 역할을 우선 선호한다.",
    "실서비스 운영 경험, 사내 시스템 구축 경험, 사용자 피드백 반영 경험이 중요한 강점이다.",
    "RAG, memory, evaluation, vLLM, 내부망/온프레미스, developer productivity와 닿는 역할을 높게 본다.",
    "비AI 직무, 영업/마케팅/행정 중심 역할은 우선순위가 낮다.",
)

UUID_RE = re.compile(r"^/recruitment/[0-9a-f-]{36}$")
ARCHIVE_POST_RE = re.compile(r"^https://inthiswork\.com/archives/\d+/?$")


@dataclass
class JobPosting:
    source: str
    url: str
    raw_card_text: str
    title: str = ""
    company: str = ""
    location: str = ""
    card_meta: str = ""
    detail_title: str = ""
    detail_text: str = ""

    @property
    def combined_text(self) -> str:
        return "\n".join(
            part
            for part in [
                self.title,
                self.company,
                self.location,
                self.card_meta,
                self.raw_card_text,
                self.detail_title,
                self.detail_text,
            ]
            if part
        )


@dataclass
class JobMatch:
    job: JobPosting
    score: int
    matched_keywords: list[str] = field(default_factory=list)
    project_hits: list[str] = field(default_factory=list)
    quick_reason: str = ""
    motivation_essay: str = ""
    strengths_essay: str = ""
    llm_used: bool = False


def clean_lines(text: str) -> list[str]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    deduped: list[str] = []
    for line in lines:
        if deduped and deduped[-1] == line:
            continue
        deduped.append(line)
    return deduped


def shrink(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def trim_detail_text(source: str, text: str) -> str:
    cut_markers = {
        "jobda": [
            "보고 계신 포지션과 비슷한 포지션이에요.",
            "채용정보 수정 요청",
            "JOBDA",
        ],
        "zighang": [
            "이 공고도 지원중!",
            "지원하기",
            "커리어 멘토챗",
        ],
        "inthiswork": [
            "최신 댓글 모음 보러가기",
            "취업토크 추천 아티클",
            "함께 보면 좋은 커리어 정보",
        ],
    }
    trimmed = text
    for marker in cut_markers.get(source, []):
        if marker in trimmed:
            trimmed = trimmed.split(marker, 1)[0].strip()
    return trimmed


def source_home(source: str) -> str:
    return {
        "inthiswork": "https://inthiswork.com",
        "jobda": "https://www.jobda.im",
        "zighang": "https://zighang.com",
    }[source]


def safe_goto(page: Page, url: str) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(2_000)


def wait_for_first_selector(
    page: Page,
    selectors: list[str],
    *,
    timeout_ms: int = 30_000,
    poll_ms: int = 1_000,
) -> str:
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        for selector in selectors:
            if page.locator(selector).count() > 0:
                return selector
        page.wait_for_timeout(poll_ms)
    raise PlaywrightTimeoutError(
        f"None of the selectors appeared within {timeout_ms}ms: {selectors}"
    )


def parse_inthiswork_card(raw_text: str, url: str) -> JobPosting:
    lines = clean_lines(raw_text)
    title = lines[0] if lines else ""
    company = title.split("｜", 1)[0].strip() if "｜" in title else ""
    return JobPosting(
        source="inthiswork",
        url=url,
        raw_card_text=raw_text,
        title=title,
        company=company,
        card_meta=" ".join(lines[1:4]),
    )


def parse_jobda_card(raw_text: str, url: str) -> JobPosting:
    lines = clean_lines(raw_text)
    title = lines[0] if lines else ""
    company = lines[1] if len(lines) > 1 else ""
    location = lines[2] if len(lines) > 2 else ""
    meta = " ".join(lines[3:6])
    return JobPosting(
        source="jobda",
        url=url,
        raw_card_text=raw_text,
        title=title,
        company=company,
        location=location,
        card_meta=meta,
    )


def parse_zighang_card(raw_text: str, url: str) -> JobPosting:
    lines = clean_lines(raw_text)
    company = lines[0] if lines else ""
    meta = lines[1] if len(lines) > 1 else ""
    title = lines[2] if len(lines) > 2 else (lines[0] if lines else "")
    return JobPosting(
        source="zighang",
        url=url,
        raw_card_text=raw_text,
        title=title,
        company=company,
        card_meta=meta,
    )


def collect_cards(page: Page, selector: str, parser, limit: int) -> list[JobPosting]:
    anchors = page.locator(selector)
    results: list[JobPosting] = []
    seen: set[str] = set()

    count = anchors.count()
    for idx in range(count):
        anchor = anchors.nth(idx)
        href = anchor.get_attribute("href")
        if not href:
            continue
        text = anchor.inner_text(timeout=5_000).strip()
        if not text:
            continue
        if href in seen:
            continue
        seen.add(href)
        url = urljoin(page.url, href)
        posting = parser(text, url)
        results.append(posting)
        if len(results) >= limit:
            break
    return results


def scrape_inthiswork(page: Page, limit: int) -> list[JobPosting]:
    safe_goto(page, "https://inthiswork.com/junior")
    selector = wait_for_first_selector(
        page,
        [
            "a[href*='/archives/']",
            "article a[href*='/archives/']",
            "main a[href*='/archives/']",
        ],
        timeout_ms=30_000,
    )
    anchors = page.locator(selector)
    results: list[JobPosting] = []
    seen: set[str] = set()
    for idx in range(anchors.count()):
        anchor = anchors.nth(idx)
        href = anchor.get_attribute("href")
        if not href:
            continue
        full_url = urljoin(page.url, href)
        if not ARCHIVE_POST_RE.match(full_url) or full_url in seen:
            continue
        text = anchor.inner_text(timeout=5_000).strip()
        if not text:
            continue
        seen.add(full_url)
        results.append(parse_inthiswork_card(text, full_url))
        if len(results) >= limit:
            break
    return results


def scrape_jobda(page: Page, limit: int) -> list[JobPosting]:
    safe_goto(page, "https://www.jobda.im/position")
    page.wait_for_selector("a[href^='/position/'][href$='/jd']", timeout=30_000)
    return collect_cards(
        page,
        "a[href^='/position/'][href$='/jd']",
        parse_jobda_card,
        limit,
    )


def scrape_zighang(page: Page, limit: int) -> list[JobPosting]:
    safe_goto(page, "https://zighang.com/recruitment")
    page.wait_for_selector("a[href^='/recruitment/']", timeout=30_000)
    anchors = page.locator("a[href^='/recruitment/']")
    results: list[JobPosting] = []
    seen: set[str] = set()
    for idx in range(anchors.count()):
        anchor = anchors.nth(idx)
        href = anchor.get_attribute("href")
        if not href or not UUID_RE.match(href):
            continue
        text = anchor.inner_text(timeout=5_000).strip()
        if not text or href in seen:
            continue
        seen.add(href)
        results.append(parse_zighang_card(text, urljoin(page.url, href)))
        if len(results) >= limit:
            break
    return results


def enrich_detail(page: Page, job: JobPosting) -> None:
    safe_goto(page, job.url)
    body_text = page.locator("body").inner_text()
    job.detail_title = page.title()
    cleaned = "\n".join(clean_lines(body_text))
    job.detail_text = shrink(trim_detail_text(job.source, cleaned), 8_000)

    if not job.title:
        lines = clean_lines(body_text)
        if lines:
            job.title = lines[0]

    if job.source == "jobda" and not job.company:
        lines = clean_lines(body_text)
        if len(lines) > 2:
            job.company = lines[2]


def collect_site_jobs(
    page: Page,
    *,
    label: str,
    scraper: Callable[[Page, int], list[JobPosting]],
    limit: int,
) -> tuple[list[JobPosting], str | None]:
    try:
        jobs = scraper(page, limit)
        print(f"[{label}] 목록 수집 완료: {len(jobs)}건")
        return jobs, None
    except Exception as exc:
        message = f"[{label}] 목록 수집 실패: {exc}"
        print(message)
        return [], message


def score_text(text: str, profile: CandidateProfile) -> tuple[int, list[str]]:
    lowered = text.lower()
    score = 0
    matched: list[str] = []

    for keyword, weight in profile.positive_keywords.items():
        if keyword in lowered:
            score += weight
            matched.append(keyword)

    title_boost_keywords = ("ai agent", "agent", "에이전트", "llm", "rag", "gen ai", "mcp")
    title_line = lowered.splitlines()[0] if lowered.splitlines() else lowered
    if any(keyword in title_line for keyword in title_boost_keywords):
        score += 6

    for keyword, weight in profile.negative_keywords.items():
        if keyword in title_line:
            score += weight

    return score, sorted(set(matched))


def project_score(text: str, project: ProjectProfile) -> int:
    lowered = text.lower()
    return sum(4 for keyword in project.keywords if keyword.lower() in lowered)


def rank_projects(text: str, profile: CandidateProfile, limit: int = 2) -> list[ProjectProfile]:
    scored = [(project_score(text, project), project) for project in profile.projects]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return list(profile.projects[:limit])
    return [project for _, project in scored[:limit]]


def summarize_reason(job: JobPosting, matched_keywords: Iterable[str], projects: Iterable[ProjectProfile]) -> str:
    keyword_part = ", ".join(list(matched_keywords)[:5]) if matched_keywords else "직무 문맥"
    project_part = ", ".join(project.name for project in projects)
    return f"{keyword_part} 키워드가 포착되어 {project_part} 경험과 직접 연결됩니다."


def detect_focus(job: JobPosting) -> str:
    text = job.combined_text.lower()
    if any(keyword in text for keyword in ("agent", "에이전트", "llm", "rag", "gen ai", "mcp")):
        return "agent"
    if any(keyword in text for keyword in ("data", "데이터", "analytics", "분석", "dq", "정합성")):
        return "data"
    if any(keyword in text for keyword in ("knowledge", "search", "지식", "검색", "internal", "내부망")):
        return "enterprise"
    return "general"


def trim_to_char_limit(text: str, limit: int = 500) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def get_first_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def resolve_openai_model() -> str:
    return get_first_env("OPENAI_MODEL", "JOB_FIT_MODEL") or DEFAULT_OPENAI_MODEL


def get_openai_client():
    api_key = get_first_env("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None
    return OpenAI(api_key=api_key)


def normalize_project_hits(values: Iterable[str], profile: CandidateProfile) -> list[str]:
    valid_projects = {project.name for project in profile.projects}
    project_hits: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if cleaned in valid_projects and cleaned not in project_hits:
            project_hits.append(cleaned)
    return project_hits


def normalize_keyword_hits(values: Iterable[str]) -> list[str]:
    cleaned_hits: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if cleaned and cleaned not in cleaned_hits:
            cleaned_hits.append(cleaned)
    return cleaned_hits[:10]


def extract_message_text(message) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                    continue
                if isinstance(text, dict) and isinstance(text.get("value"), str):
                    parts.append(text["value"])
        return "\n".join(part for part in parts if part).strip()
    return ""


def read_text_context(path: Path, limit: int = 2_000) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    lines = clean_lines(text)
    return shrink("\n".join(lines), limit)


def read_pdf_context(path: Path, limit: int = 2_500) -> str:
    if not path.exists() or PdfReader is None:
        return ""
    try:
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages[:6]:
            text = page.extract_text() or ""
            if text:
                parts.append(" ".join(text.split()))
        return shrink("\n".join(parts), limit)
    except Exception:
        return ""


@lru_cache(maxsize=1)
def load_candidate_context() -> str:
    sections: list[str] = []
    for path in CONTEXT_TEXT_FILES:
        content = read_text_context(path)
        if content:
            sections.append(f"[{path.name}]\n{content}")

    for path in PORTFOLIO_PDF_FILES:
        content = read_pdf_context(path)
        if content:
            sections.append(f"[{path.name}]\n{content}")
            break

    sections.append("[추가 컨텍스트]\n" + "\n".join(f"- {hint}" for hint in ASSISTANT_CONTEXT_HINTS))
    return shrink("\n\n".join(sections), 7_000)


def evaluate_job_with_llm(job: JobPosting, profile: CandidateProfile) -> dict | None:
    client = get_openai_client()
    if client is None:
        return None

    project_text = "\n".join(
        [
            f"- {project.name}: {project.summary} / 근거: {'; '.join(project.evidence)}"
            for project in profile.projects
        ]
    )
    candidate_context = load_candidate_context()
    strengths_text = ", ".join(profile.strengths)
    job_excerpt = shrink(job.combined_text, 4_200)
    heuristic_score, heuristic_hits = score_text(job.combined_text, profile)

    system_prompt = (
        "너는 한 명의 후보자와 채용공고 간 적합도를 평가하는 비서다. "
        "후보자 프로필과 공고 텍스트만 근거로 보수적으로 판단하고, 과장하지 마라. "
        "반드시 JSON 객체만 반환하라."
    )
    user_prompt = f"""
후보자 이름: {profile.name}
후보자 한 줄 소개: {profile.headline}
후보자 강점: {strengths_text}
프로젝트:
{project_text}

포트폴리오/이력서/추가 컨텍스트:
{candidate_context}

공고 소스: {job.source}
회사: {job.company or "-"}
공고 제목: {job.title or job.detail_title or "-"}
지역: {job.location or "-"}
URL: {job.url}
카드 메타: {job.card_meta or "-"}
휴리스틱 초기 점수: {heuristic_score}
휴리스틱 키워드: {", ".join(heuristic_hits) or "-"}

공고 상세 텍스트:
{job_excerpt}

다음 JSON 형식으로만 답해라.
{{
  "score": 0-100 사이 정수,
  "high_fit": true 또는 false,
  "matched_keywords": ["키워드", "..."],
  "project_hits": ["후보자 프로젝트명", "..."],
  "quick_reason": "120자 이내 한 줄 사유",
  "motivation_essay": "지원동기 초안, 500자 이내",
  "strengths_essay": "나의 역량 및 강점 초안, 500자 이내"
}}

판단 기준:
- 80점 이상: 바로 지원 검토할 만한 고적합
- 65~79점: 일부 겹치지만 확인 필요
- 64점 이하: 직접 적합도는 낮음
- quick_reason은 후보자 경험과 공고의 직접 연결점만 적어라.
- project_hits는 위 프로젝트명 중 실제로 강하게 연결되는 것만 넣어라.
""".strip()

    try:
        response = client.chat.completions.create(
            model=resolve_openai_model(),
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = extract_message_text(response.choices[0].message)
        if not content:
            return None
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return None
        return parsed
    except Exception as exc:
        print(f"[{job.title or job.url}] LLM 적합도 평가 실패: {exc}")
        return None


def make_motivation(job: JobPosting, focus: str, projects: list[ProjectProfile]) -> str:
    company = job.company or "해당 기업"
    title = job.title or "해당 포지션"

    if focus == "agent":
        body = (
            f"{company}의 {title} 포지션은 LLM 기반 애플리케이션, 에이전트, RAG를 실제 서비스로 구현하고 "
            "개선하는 역할이라는 점에서 제가 가장 집중해 온 문제와 맞닿아 있습니다. "
            "저는 SOOPi를 운영하며 RAG만으로는 사용자의 부족한 맥락을 충분히 보완하기 어렵다는 한계를 경험했고, "
            "Long-term Memory, 도구 연계, 품질 평가 자동화를 통해 에이전트 성능을 개선해 왔습니다. "
            f"이 경험을 바탕으로 {company}에서도 사용자 피드백과 운영 관점까지 반영되는 실무형 AI 서비스를 만들고 싶습니다."
        )
    elif focus == "data":
        body = (
            f"{company}의 {title} 포지션은 대규모 데이터를 구조화하고 신뢰도 높은 기준 데이터를 만드는 역할이라는 점에서 "
            "제가 연구와 실무에서 해온 문제의식과 닿아 있습니다. 저는 SOOP 수천만 건 채팅 데이터를 정제해 RAG 실험을 설계했고, "
            "실무에서는 100만 건 이상 사내 데이터를 연결한 KMS를 구축하며 데이터 정합성, 검색 품질, 운영 기준을 함께 다뤘습니다. "
            f"{company}에서도 데이터 신뢰도와 서비스 활용성을 함께 높이는 역할에 기여하고 싶습니다."
        )
    elif focus == "enterprise":
        body = (
            f"{company}의 {title} 포지션은 기업 데이터와 시스템을 연결해 실제 업무에 쓰이는 AI를 만드는 역할이라는 점에서 매력을 느꼈습니다. "
            "저는 전사 KMS를 구축하며 내부망 환경의 RAG 시스템, 접근 제어, 답변 평가 자동화를 운영했고, "
            "전사 AI 코드리뷰를 통해 조직이 실제로 쓰는 서비스로 안착시키는 과정까지 경험했습니다. "
            f"{company}에서도 기술 구현에 그치지 않고 현업이 신뢰하고 쓰는 Enterprise AI를 만드는 데 기여하고 싶습니다."
        )
    else:
        body = (
            f"{company}의 {title} 포지션은 AI 기술을 실제 서비스와 업무 문제 해결에 연결하는 역할이라는 점에서 지원하고 싶었습니다. "
            f"저는 {projects[0].name}과 {projects[1].name}을 통해 연구와 실무를 함께 경험했고, "
            "모델 성능뿐 아니라 데이터 구조, 운영 방식, 사용자 피드백까지 함께 설계해야 품질이 올라간다는 점을 배웠습니다. "
            f"{company}에서도 현장에서 실제로 쓰이는 AI 서비스를 만드는 데 기여하고 싶습니다."
        )
    return trim_to_char_limit(body)


def make_strengths(job: JobPosting, focus: str, projects: list[ProjectProfile]) -> str:
    if focus == "agent":
        body = (
            "제 강점은 실무 AI 에이전트를 직접 출시하고 개선해 온 경험입니다. "
            "SOOPi에서는 RAG만으로 부족한 지점을 Long-term Memory, 도구 연계, Whisper STT, 응답 품질 평가 자동화로 보완하며 "
            "실시간 에이전트를 고도화했습니다. "
            "또 전사 KMS에서는 100만 건 이상 사내 데이터를 연결한 RAG 기반 지식검색 시스템과 온프레미스 vLLM 환경을 구축했습니다. "
            "연구로는 SOOP 수천만 건 채팅 데이터를 정제해 RAG 요약 성능을 검증하며 BERTScore 약 8.6% 개선과 입력 토큰 약 84.6% 절감을 확인했습니다."
        )
    elif focus == "data":
        body = (
            "대규모 데이터를 서비스 가능한 구조로 바꾸는 경험이 제 강점입니다. "
            "대학원에서는 SOOP 수천만 건 채팅 데이터를 정제해 요약용 RAG 실험을 설계했고, 품질과 효율을 정량적으로 검증했습니다. "
            "실무에서는 100만 건 이상 사내 데이터를 연결한 KMS를 구축하며 데이터 연계, 검색 품질, 접근 제어를 함께 다뤘습니다. "
            "또 전사 AI 코드리뷰 시스템을 구축하며 로그와 운영 체계를 설계해 데이터가 실제 조직의 의사결정과 생산성 향상으로 이어지게 만들었습니다."
        )
    elif focus == "enterprise":
        body = (
            "기업 환경에서 실제로 쓰이는 AI 시스템을 만들어 본 경험이 가장 큰 강점입니다. "
            "전사 KMS에서는 내부망 환경에 온프레미스 vLLM 기반 RAG 시스템을 구축했고, 접근 제어와 답변 평가 자동화까지 설계했습니다. "
            "전사 AI 코드리뷰에서는 300명+ 개발조직이 사용하는 서비스를 런칭하며 CI/CD, 권한 정책, 로그 체계를 함께 만들었습니다. "
            "기술 구현뿐 아니라 조직 안착과 운영 기준까지 다뤄본 경험을 바탕으로 빠르게 기여할 수 있습니다."
        )
    else:
        body = (
            f"제 강점은 {projects[0].name}과 {projects[1].name}처럼 연구와 실무를 연결해 온 경험입니다. "
            "대규모 데이터를 정제하고, RAG·LLM 구조를 설계하고, 품질 평가와 운영 기준까지 함께 다뤄 왔습니다. "
            "특히 사용자 피드백을 바탕으로 서비스를 개선하고, 여러 부서와 협업해 전사 대상 서비스를 안착시킨 경험이 있어 "
            "기술 구현과 현업 커뮤니케이션을 함께 가져갈 수 있습니다."
        )
    return trim_to_char_limit(body)


def build_match_fallback(job: JobPosting, profile: CandidateProfile) -> JobMatch:
    score, matched_keywords = score_text(job.combined_text, profile)
    projects = rank_projects(job.combined_text, profile)
    quick_reason = summarize_reason(job, matched_keywords, projects)
    focus = detect_focus(job)
    return JobMatch(
        job=job,
        score=score,
        matched_keywords=matched_keywords,
        project_hits=[project.name for project in projects],
        quick_reason=quick_reason,
        motivation_essay=make_motivation(job, focus, projects),
        strengths_essay=make_strengths(job, focus, projects),
        llm_used=False,
    )


def build_match(job: JobPosting, profile: CandidateProfile) -> JobMatch:
    llm_result = evaluate_job_with_llm(job, profile)
    if not llm_result:
        return build_match_fallback(job, profile)

    fallback_match = build_match_fallback(job, profile)
    raw_score = llm_result.get("score", fallback_match.score)
    try:
        score = int(raw_score)
    except (TypeError, ValueError):
        score = fallback_match.score
    score = max(0, min(100, score))

    matched_keywords = normalize_keyword_hits(
        llm_result.get("matched_keywords") or fallback_match.matched_keywords
    )
    project_hits = normalize_project_hits(
        llm_result.get("project_hits") or fallback_match.project_hits,
        profile,
    ) or fallback_match.project_hits
    quick_reason = trim_to_char_limit(
        str(llm_result.get("quick_reason") or fallback_match.quick_reason),
        120,
    )
    motivation_essay = trim_to_char_limit(
        str(llm_result.get("motivation_essay") or fallback_match.motivation_essay),
        500,
    )
    strengths_essay = trim_to_char_limit(
        str(llm_result.get("strengths_essay") or fallback_match.strengths_essay),
        500,
    )

    return JobMatch(
        job=job,
        score=score,
        matched_keywords=matched_keywords,
        project_hits=project_hits,
        quick_reason=quick_reason,
        motivation_essay=motivation_essay,
        strengths_essay=strengths_essay,
        llm_used=True,
    )


def run_monitor(limit_per_site: int, detail_top_n: int, min_score: int) -> list[JobMatch]:
    scrape_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 2200})

        jobs: list[JobPosting] = []
        for label, scraper in [
            ("InThisWork", scrape_inthiswork),
            ("Jobda", scrape_jobda),
            ("Zighang", scrape_zighang),
        ]:
            items, error = collect_site_jobs(
                page,
                label=label,
                scraper=scraper,
                limit=limit_per_site,
            )
            jobs.extend(items)
            if error:
                scrape_errors.append(error)

        browser.close()

        if not jobs and scrape_errors:
            raise RuntimeError("채용공고 source 수집이 모두 실패했습니다.")

        quick_ranked = sorted(
            jobs,
            key=lambda job: score_text(job.combined_text, CANDIDATE)[0],
            reverse=True,
        )

    detail_targets = quick_ranked[:detail_top_n]
    detail_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 2200})
        for job in detail_targets:
            try:
                enrich_detail(page, job)
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

    matches = [build_match(job, CANDIDATE) for job in detail_targets]
    matches.sort(key=lambda match: match.score, reverse=True)
    return [match for match in matches if match.score >= min_score]


def render_report(matches: list[JobMatch], limit: int) -> str:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Job Monitor Report",
        "",
        f"- 생성 시각: {now}",
        f"- 후보자: {CANDIDATE.name}",
        f"- 핵심 포지션: AI Engineer / LLM Engineer / Agent Engineer / Enterprise AI",
        f"- 적합도 평가 모델: {resolve_openai_model() if get_openai_client() else 'fallback-heuristic'}",
        "",
        "## Top Matches",
        "",
    ]

    if not matches:
        lines.append("조건에 맞는 공고를 찾지 못했습니다.")
        return "\n".join(lines)

    for idx, match in enumerate(matches[:limit], start=1):
        job = match.job
        lines.extend(
            [
                f"### {idx}. {job.title or job.detail_title}",
                "",
                f"- Source: {job.source}",
                f"- Company: {job.company or '-'}",
                f"- Score: {match.score}",
                f"- URL: {job.url}",
                f"- 평가 방식: {'OpenAI 기반' if match.llm_used else '휴리스틱 fallback'}",
                f"- Matched Keywords: {', '.join(match.matched_keywords[:10]) or '-'}",
                f"- Related Projects: {', '.join(match.project_hits)}",
                f"- Why Fit: {match.quick_reason}",
                "",
                f"#### 지원동기",
                match.motivation_essay,
                "",
                f"#### 나의 역량 및 강점",
                match.strengths_essay,
                "",
                f"#### Detail Excerpt",
                shrink(job.detail_text or job.raw_card_text, 700),
                "",
            ]
        )

    return "\n".join(lines)


def save_report(report: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORT_DIR / f"job_report_{stamp}.md"
    path.write_text(report, encoding="utf-8")
    return path


def resolve_bridge_base_url() -> str:
    return get_first_env("JOB_FIT_REPORT_BRIDGE_URL", "TELEGRAM_MEMORY_BRIDGE_URL")


def resolve_bridge_token() -> str:
    return get_first_env("JOB_FIT_REPORT_BRIDGE_TOKEN", "TELEGRAM_MEMORY_BRIDGE_TOKEN")


def upload_report_to_bridge(path: Path, matches: list[JobMatch]) -> dict | None:
    base_url = resolve_bridge_base_url()
    token = resolve_bridge_token()
    if not base_url or not token:
        print("Cloudflare 보고서 업로드 설정이 없어 업로드를 건너뜁니다.")
        return None

    payload = {
        "date": dt.datetime.now().strftime("%Y-%m-%d"),
        "filename": path.name,
        "report": path.read_text(encoding="utf-8"),
        "high_fit_titles": [
            match.job.title or match.job.detail_title
            for match in matches
            if match.score >= DEFAULT_NOTIFY_MIN_SCORE
        ],
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    request = urllib.request.Request(
        resolve_bridge_base_url().rstrip("/") + "/job-fit-report",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read() or b"{}")
            if not body.get("ok"):
                raise RuntimeError(str(body))
            return body
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"Cloudflare 보고서 업로드 실패 [{exc.code}]: {detail}"
        ) from exc


def build_high_fit_titles_message(
    matches: list[JobMatch],
    min_score: int,
    limit: int,
) -> str:
    high_fit_matches = [
        match for match in matches
        if match.score >= min_score and (match.job.title or match.job.detail_title)
    ]
    high_fit_matches = high_fit_matches[:limit]
    date_label = dt.datetime.now().strftime("%Y-%m-%d")

    if not high_fit_matches:
        return (
            f"<b>💼 고적합 채용공고</b> ({date_label})\n\n"
            "오늘 기준으로 바로 챙겨볼 만한 공고를 찾지 못했습니다."
        )

    lines = [f"<b>💼 고적합 채용공고</b> ({date_label})", ""]
    lines.extend(
        f"- {match.job.title or match.job.detail_title}"
        for match in high_fit_matches
    )
    return "\n".join(lines)


def maybe_send_high_fit_titles(matches: list[JobMatch], min_score: int, limit: int) -> None:
    if send_telegram is None:
        print("send_telegram import에 실패해 제목 알림을 건너뜁니다.")
        return
    message = build_high_fit_titles_message(matches, min_score=min_score, limit=limit)
    send_telegram(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="세 사이트 채용공고를 수집하고 fit 리포트를 생성합니다.")
    parser.add_argument("--limit-per-site", type=int, default=40, help="사이트별 목록 수집 개수")
    parser.add_argument("--detail-top-n", type=int, default=15, help="상위 공고 상세 수집 개수")
    parser.add_argument("--min-score", type=int, default=70, help="리포트에 포함할 최소 점수")
    parser.add_argument("--report-limit", type=int, default=12, help="보고서에 포함할 최대 공고 수")
    parser.add_argument(
        "--upload-report",
        action="store_true",
        help="생성한 Markdown 리포트를 Cloudflare Worker를 통해 비공개 저장소에 업로드",
    )
    parser.add_argument(
        "--notify-high-fit-titles",
        action="store_true",
        help="고적합 공고 제목만 텔레그램으로 전송",
    )
    parser.add_argument(
        "--notify-min-score",
        type=int,
        default=DEFAULT_NOTIFY_MIN_SCORE,
        help="텔레그램으로 보낼 고적합 공고 최소 점수",
    )
    parser.add_argument(
        "--notify-limit",
        type=int,
        default=5,
        help="텔레그램으로 보낼 최대 공고 제목 수",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    matches = run_monitor(
        limit_per_site=args.limit_per_site,
        detail_top_n=args.detail_top_n,
        min_score=args.min_score,
    )
    report = render_report(matches, limit=args.report_limit)
    path = save_report(report)
    if args.upload_report:
        uploaded = upload_report_to_bridge(path, matches)
        if uploaded:
            print(f"Cloudflare 업로드 완료: {uploaded.get('key', '-')}")

    if args.notify_high_fit_titles:
        maybe_send_high_fit_titles(
            matches,
            min_score=args.notify_min_score,
            limit=args.notify_limit,
        )

    print(path)


if __name__ == "__main__":
    main()
