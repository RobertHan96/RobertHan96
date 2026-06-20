# AI Quality Job Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AI-quality-focused job monitor that scrapes selected career sites, scores postings against Han's portfolio, sends immediate Telegram alerts for high-fit roles, and sends a daily summary for the rest.

**Architecture:** Keep the existing `jobs/core.py` fit-evaluation engine intact and add a focused monitor around it. The new monitor owns source scraping, role-specific scoring, state persistence through the Cloudflare bridge or a local JSON fallback, and two scheduled GitHub Actions workflows for immediate alerts and daily summaries.

**Tech Stack:** Python, Playwright, BeautifulSoup, OpenAI API, Cloudflare Worker KV, GitHub Actions, unittest

---

## File Structure

- Create: `/Users/han/Desktop/Dev/RobertHan96/jobs/ai_quality_profile.py`
- Create: `/Users/han/Desktop/Dev/RobertHan96/jobs/ai_quality_monitor.py`
- Create: `/Users/han/Desktop/Dev/RobertHan96/jobs/run_ai_quality_job_monitor.py`
- Modify: `/Users/han/Desktop/Dev/RobertHan96/services/cloudflare-telegram-bridge/worker.mjs`
- Create: `/Users/han/Desktop/Dev/RobertHan96/.github/workflows/ai-quality-job-monitor.yml`
- Create: `/Users/han/Desktop/Dev/RobertHan96/.github/workflows/ai-quality-job-summary.yml`
- Modify: `/Users/han/Desktop/Dev/RobertHan96/jobs/README.md`
- Test: `/Users/han/Desktop/Dev/RobertHan96/tests/test_ai_quality_job_monitor.py`

## Task 1: Lock the AI-quality scoring contract with tests

- [ ] Add unittest coverage for:
  - AI 품질/안전성 공고가 높은 점수를 받는지
  - 제조/일반 QA 공고가 강하게 감점되는지
  - NAVER `show('annoId')` 패턴이 정상 복원되는지
  - 일일 요약 후보 병합 시 중복 제거와 점수 우선이 되는지
- [ ] Run:

```bash
python3 -m unittest tests/test_ai_quality_job_monitor.py -v
```

- [ ] Confirm the test suite fails because the new monitor module does not exist yet.

## Task 2: Implement profile, scoring, state storage, and message builders

- [ ] Create `jobs/ai_quality_profile.py` with:
  - tuned `CandidateProfile`
  - seed role examples
  - role positive/negative keywords
- [ ] Create `jobs/ai_quality_monitor.py` with:
  - source dataclasses
  - role score + seed similarity helpers
  - bridge/local state backend
  - summary merge logic
  - immediate/daily Telegram message builders
- [ ] Re-run:

```bash
python3 -m unittest tests/test_ai_quality_job_monitor.py -v
```

- [ ] Confirm the new tests pass.

## Task 3: Implement collectors and run modes

- [ ] Add collectors for:
  - Wanted
  - 카카오
  - 카카오뱅크
  - NAVER
  - 현대오토에버
  - KT
  - SK
  - HYBE
- [ ] Add generic detail enrichment for the top-ranked postings.
- [ ] Add CLI modes:
  - `immediate`
  - `summary`
  - `dry-run`
- [ ] Ensure `summary` mode excludes jobs that already qualified for immediate high-fit alerts.
- [ ] Add `jobs/run_ai_quality_job_monitor.py`.

## Task 4: Extend the Cloudflare Worker bridge

- [ ] Add authenticated state read/write endpoints backed by `TELEGRAM_MEMORY_KV`.
- [ ] Keep existing `/log`, `/logs`, `/job-fit-report`, and Telegram webhook behavior unchanged.
- [ ] Verify syntax with:

```bash
node --check services/cloudflare-telegram-bridge/worker.mjs
```

## Task 5: Wire up GitHub Actions and docs

- [ ] Add the immediate-alert workflow.
- [ ] Add the daily-summary workflow.
- [ ] Set `OPENAI_MODEL`, Telegram secrets, and bridge env reuse exactly like existing job-fit monitor.
- [ ] Document the new monitor in `jobs/README.md`.

## Task 6: Verification

- [ ] Run unit tests:

```bash
python3 -m unittest tests/test_ai_quality_job_monitor.py -v
```

- [ ] Run compile check:

```bash
python3 -m compileall jobs/core.py jobs/ai_quality_profile.py jobs/ai_quality_monitor.py jobs/run_ai_quality_job_monitor.py
```

- [ ] Run a narrow dry-run scrape:

```bash
python3 -m jobs.run_ai_quality_job_monitor --mode dry-run --limit-per-site 5 --detail-top-n 5 --min-score 60
```

- [ ] Run worker syntax check:

```bash
node --check services/cloudflare-telegram-bridge/worker.mjs
```

- [ ] Review output for:
  - partial-failure tolerance
  - at least one real AI-quality-adjacent match
  - no crash when a source has zero relevant jobs
