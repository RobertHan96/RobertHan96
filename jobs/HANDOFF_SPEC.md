# Job Monitor Handoff Spec

## 목적

현재 로컬에서 동작하는 채용공고 모니터링 스크립트를 `사용자 PC가 꺼져 있어도 실행 가능한 원격 환경`으로 옮긴다.

우선순위는 다음과 같다.

1. `GitHub Actions`로 주기 실행 가능하게 만들기
2. 실행 결과를 `artifact` 또는 외부 저장소에 남기기
3. 필요 시 `Slack/Discord/이메일` 알림 추가

`Cloudflare Workers`는 현재 코드 기준으로 재구현 범위가 커서 1차 목표가 아니다.

## 현재 구현 상태

### 핵심 파일

- `/Users/han/Desktop/Dev/Carrer/run_job_monitor.py`
- `/Users/han/Desktop/Dev/Carrer/job_monitor/core.py`
- `/Users/han/Desktop/Dev/Carrer/job_monitor/profile.py`
- `/Users/han/Desktop/Dev/Carrer/job_monitor/README.md`

### 현재 기능

- 세 사이트 수집
  - `https://zighang.com/recruitment`
  - `https://inthiswork.com/junior`
  - `https://www.jobda.im/position`
- Playwright 기반 동적 렌더링 수집
- 상위 공고 상세 페이지 본문 수집
- 후보자 프로필 기반 fit score 계산
- `지원동기`, `나의 역량 및 강점` 500자 내외 초안 생성
- Markdown 리포트 저장

### 현재 산출물 예시

- `/Users/han/Desktop/Dev/Carrer/job_monitor/reports/job_report_20260331_233615.md`

## 이번 핸드오프에서 다른 에이전트가 해야 할 일

### 1. GitHub Actions용으로 실행 경로 정리

이미 최소 수정은 반영됨.

- `core.py`는 `JOB_MONITOR_REPORT_DIR` 환경변수로 리포트 경로를 오버라이드 가능
- 기본값은 로컬 경로 유지

확인 포인트:

- GitHub Actions에서 상대 경로 기준으로 리포트가 정상 생성되는지 확인
- `job_monitor/reports/*.md` artifact 업로드가 정상 동작하는지 확인

### 2. 워크플로 추가

예시 파일:

- `/Users/han/Desktop/Dev/Carrer/job_monitor/github-actions-job-monitor.yml`

다른 에이전트가 할 일:

- 이 파일을 실제 저장소의 `.github/workflows/job-monitor.yml`로 복사 또는 변환
- 실행 브랜치, schedule, Python 버전, artifact 정책을 저장소 정책에 맞게 조정

### 3. 저장 방식 결정

최소 요구사항:

- 실행 후 생성된 Markdown 리포트를 artifact로 보존

선택 확장:

- 리포트를 저장소에 커밋
- Slack webhook 전송
- Discord webhook 전송
- Gmail/Resend 등 이메일 전송
- Notion / Google Sheets / Supabase 적재

### 4. 실패 대응

다른 에이전트가 아래를 점검해야 함.

- 대상 사이트 DOM 변경 시 selector 깨짐 여부
- Playwright 브라우저 설치 실패 여부
- 스케줄 실행 시 타임존 해석
- 장시간 실행 시 timeout 조정

## 비목표

이번 단계에서는 아래는 하지 않아도 됨.

- Cloudflare Workers로 완전 재작성
- Browser Rendering용 TypeScript 마이그레이션
- R2/KV/D1 저장소 설계
- Worker Cron Trigger 배포

## 권장 배포 방향

### 1순위: GitHub Actions

이유:

- 현재 코드가 `Python + Playwright` 구조라 거의 그대로 실행 가능
- 주기 실행과 artifact 저장이 간단함
- 로컬 머신 상시 실행이 필요 없음

### 2순위: Cloudflare Workers

현재 코드 기준 문제:

- Python 스크립트를 Worker 구조로 재작성 필요
- Playwright 사용 방식이 달라짐
- 파일 저장 불가, `R2/KV/D1`로 저장소 설계 필요

즉, 지금은 추천하지 않음.

## 실행 명령

로컬 검증:

```bash
cd /Users/han/Desktop/Dev/Carrer
.venv/bin/python run_job_monitor.py --limit-per-site 12 --detail-top-n 4 --min-score 20 --report-limit 5
```

GitHub Actions 환경 기준:

```bash
python run_job_monitor.py --limit-per-site 20 --detail-top-n 8 --min-score 20 --report-limit 10
```

환경 변수:

```bash
JOB_MONITOR_REPORT_DIR=/path/to/output
```

## 의존성

파일:

- `/Users/han/Desktop/Dev/Carrer/job_monitor/requirements.txt`

현재 목록:

- `playwright==1.58.0`
- `beautifulsoup4==4.14.3`

추가로 GitHub Actions에서는 브라우저 설치 필요:

```bash
python -m playwright install --with-deps chromium
```

## 수용 기준

다른 에이전트의 작업 완료 기준은 아래와 같다.

1. GitHub Actions에서 수동 실행 `workflow_dispatch` 성공
2. 스케줄 실행이 설정되어 있음
3. Playwright Chromium 설치 후 스크립트가 정상 수행됨
4. `job_monitor/reports/*.md`가 artifact로 업로드됨
5. 리포트에 최소 1개 이상 공고가 포함됨
6. 리포트에 `지원동기`, `나의 역량 및 강점` 섹션이 포함됨

## 알려진 한계

- 점수 계산은 규칙 기반이라 완벽하지 않음
- 잡다/직행/인디스워크 DOM 구조가 바뀌면 selector 수정 필요
- 에세이 초안은 제출 전 사람이 한 번 더 다듬는 것이 권장됨
- 현재는 알림 기능이 없음

## 다른 에이전트에게 바로 넘길 때 사용할 메모

현재 로컬 프로토타입은 완성되어 있고, 원격 실행만 남아 있는 상태다.
우선 GitHub Actions로 운영 가능한 형태로 마무리하고, artifact 저장까지 연결해주면 된다.
Cloudflare Workers는 이번 범위에서 제외해도 된다.
