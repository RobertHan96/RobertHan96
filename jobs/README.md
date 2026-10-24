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

- 일반 채용 모니터: 월·금 10:00 KST. 최근 5일 공고 중 미발송 공고만 전송한다.
- Fit 리포트: 월·금 10:20 KST. `80점 이상` 미발송 공고 제목만 최대 5건 전송한다.
- AI 품질·Builder: 월·금 18:30 KST. `65점 이상` 미발송 공고만 최대 5건 전송한다.
- 요약 후보는 `60점 이상`부터 적재하며, 요약 워크플로는 수동 실행만 지원한다.
- 신규 공고가 없으면 텔레그램을 보내지 않는다. 일부 소스 실패는 Actions 로그에만 남긴다.
- 모든 목록 소스가 실패하면 텔레그램 경고를 보내고 실행을 실패 처리한다. 정상 조회 결과 0건은 실패로 보지 않는다.

상태 저장:

- GitHub Actions에서는 Cloudflare Worker KV를 사용
- 로컬에서는 `data/job_monitors/ai_quality_state.json` 파일 fallback 사용
- 채용 워크플로의 `TELEGRAM_MEMORY_BRIDGE_URL`과 `OPENAI_MODEL`은 GitHub Variable을 우선 읽고, 없으면 같은 이름의 Secret을 읽는다.
- `TELEGRAM_MEMORY_BRIDGE_TOKEN`은 Secret에 등록한다. URL이나 토큰이 비어 있으면 Actions에서 수집을 시작하기 전에 실패 처리해 임시 로컬 상태로 인한 반복 발송을 막는다.
- 기존 운영에서 발송 이력이 KV에 저장되지 않았다면 첫 실행에서 기존 공고가 한 차례 다시 발송될 수 있다.

## 참고

- 동적 렌더링 사이트가 포함되어 있어 `Playwright`와 `Chromium`을 사용합니다.
- 에세이 초안은 LLM 기반 자동 생성 결과이므로, 최종 제출 전 사람이 한 번 더 다듬는 것을 권장합니다.
- 텔레그램에는 `고적합`으로 분류된 공고의 제목만 보냅니다.
