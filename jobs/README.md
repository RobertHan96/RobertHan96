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

## 참고

- 동적 렌더링 사이트가 포함되어 있어 `Playwright`와 `Chromium`을 사용합니다.
- 에세이 초안은 LLM 기반 자동 생성 결과이므로, 최종 제출 전 사람이 한 번 더 다듬는 것을 권장합니다.
- 텔레그램에는 `고적합`으로 분류된 공고의 제목만 보냅니다.
