# Job Monitor

세 사이트의 공개 채용 페이지를 수집하고, 한영신 후보자의 포트폴리오/이력서/소개 문서를 함께 참고해 `fit 점수`, `지원동기`, `나의 역량 및 강점` 초안을 생성하는 스크립트입니다.

## 대상 사이트

- `https://zighang.com/recruitment`
- `https://inthiswork.com/junior`
- `https://www.jobda.im/position`

## 실행 방법

```bash
cd /Users/han/Desktop/Dev/RobertHan96
python -m jobs.run_job_monitor
```

옵션 예시:

```bash
python -m jobs.run_job_monitor --limit-per-site 50 --detail-top-n 20 --min-score 20 --report-limit 10
```

## 출력

- 경로: `/Users/han/Desktop/Dev/RobertHan96/jobs/reports`
- 형식: Markdown 리포트
- GitHub Actions 정기 실행 시에는 로컬 리포트를 GitHub artifact로 남기지 않고 Cloudflare Worker/R2로 업로드합니다.

## 현재 구현 범위

- 세 사이트 공개 목록 페이지 수집
- 상위 공고 상세 페이지 본문 수집
- 후보자 프로필 + `resume.md` + `content/about/index.md` + `portfolio.pdf` 기반 적합도 판단
- OpenAI API 기반 `fit 점수`, `지원동기`, `나의 역량 및 강점` 500자 내외 초안 생성
- GitHub Actions workflow: `.github/workflows/job-fit-monitor.yml`

## AI 품질·Builder 전용 모니터

별도로 `AI 품질 / AI 안전성 평가 / LLM 평가 / AI QA / AI Builder / Forward Developer` 역할을 모아보는 전용 모니터도 추가했다.

- 실행 엔트리: `/Users/han/Desktop/Dev/RobertHan96/jobs/run_ai_quality_job_monitor.py`
- 핵심 로직: `/Users/han/Desktop/Dev/RobertHan96/jobs/ai_quality_monitor.py`
- 역할 프로필: `/Users/han/Desktop/Dev/RobertHan96/jobs/ai_quality_profile.py`

현재 1차 수집 소스:

- Wanted
- 카카오
- 카카오뱅크
- NAVER Careers
- 삼성 커리어스
- LG Careers
- 현대오토에버
- CJ Careers
- KT Careers
- SK Careers
- HYBE Careers

실행 예시:

```bash
python3 -m jobs.run_ai_quality_job_monitor --mode dry-run --limit-per-site 5 --detail-top-n 5 --min-score 60
```

알림 정책:

- `85점 이상`: 즉시 텔레그램 알림
- `65점 이상`: 일일 요약 후보로 적재
- 일일 요약 발송 시에는 이미 즉시 알림으로 보낸 `85점 이상` 공고를 제외하고 나머지만 보낸다

상태 저장:

- GitHub Actions에서는 Cloudflare Worker KV를 사용
- 로컬에서는 `data/job_monitors/ai_quality_state.json` 파일 fallback 사용

## 참고

- 동적 렌더링 사이트가 포함되어 있어 `Playwright`와 `Chromium`을 사용합니다.
- 에세이 초안은 LLM 기반 자동 생성 결과이므로, 최종 제출 전 사람이 한 번 더 다듬는 것을 권장합니다.
- 텔레그램에는 `고적합`으로 분류된 공고의 제목만 보냅니다.
