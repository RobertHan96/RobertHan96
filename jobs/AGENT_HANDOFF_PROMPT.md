# Agent Handoff Prompt

아래 작업을 이어서 진행해 주세요.

## 목표

현재 로컬에서 동작하는 채용공고 모니터링 스크립트를 `GitHub Actions`에서 주기적으로 실행 가능한 형태로 마무리하고, 실행 결과 Markdown 리포트를 artifact로 저장해 주세요.

## 현재 상태

- 로컬 프로토타입 구현 완료
- 세 사이트 수집 가능
  - 직행
  - 인디스워크
  - 잡다
- Playwright 기반 동적 렌더링 수집
- fit score 계산 및 `지원동기`, `나의 역량 및 강점` 초안 생성 가능

핵심 파일:

- `/Users/han/Desktop/Dev/Carrer/run_job_monitor.py`
- `/Users/han/Desktop/Dev/Carrer/job_monitor/core.py`
- `/Users/han/Desktop/Dev/Carrer/job_monitor/profile.py`
- `/Users/han/Desktop/Dev/Carrer/job_monitor/requirements.txt`
- `/Users/han/Desktop/Dev/Carrer/job_monitor/github-actions-job-monitor.yml`
- `/Users/han/Desktop/Dev/Carrer/job_monitor/HANDOFF_SPEC.md`

## 이미 반영된 사항

- `JOB_MONITOR_REPORT_DIR` 환경변수로 리포트 출력 경로 변경 가능
- GitHub Actions 예시 워크플로 파일 작성됨
- 샘플 리포트 생성 확인됨

## 당신이 할 일

1. 실제 저장소 기준으로 `.github/workflows/job-monitor.yml` 구성
2. GitHub Actions에서 Python / Playwright / Chromium 설치 후 실행 검증
3. `job_monitor/reports/*.md` artifact 업로드 검증
4. 필요하면 schedule 시간, timeout, 실행 옵션 튜닝
5. 가능하면 실패 시 디버깅 로그가 남도록 개선

## 하지 않아도 되는 것

- Cloudflare Workers 재구현
- Browser Rendering + TypeScript 전환
- R2/KV/D1 저장소 설계

## 완료 기준

1. `workflow_dispatch` 수동 실행 성공
2. 스케줄 실행 설정 완료
3. 리포트 artifact 저장 성공
4. 리포트에 최소 1개 이상 fit 공고 포함
5. 리포트에 `지원동기`, `나의 역량 및 강점` 섹션 포함

## 참고

자세한 요구사항은 아래 문서를 우선 기준으로 봐 주세요.

- `/Users/han/Desktop/Dev/Carrer/job_monitor/HANDOFF_SPEC.md`
