# AI Quality Job Monitor Design

**Date:** 2026-06-21

## Goal

AI 품질 담당자, AI 안전성 평가, 모델/서비스 평가, AI QA 계열 공고를 매일 수동으로 찾지 않아도 되도록 별도 모니터를 만든다.

이번 설계의 핵심은 아래 두 가지다.

- 일반 AI 엔지니어 공고와 구분되는 `AI 품질/평가/안전성` 역할만 별도 분류한다.
- `고적합 즉시 알림`과 `그 외 일일 요약`을 분리해 텔레그램 피로도를 낮춘다.

## Scope

이번 1차 구현 범위:

- AI 품질 전용 채용공고 수집기 추가
- 포트폴리오 기반 적합도 평가 재사용
- AI 품질 역할 전용 추가 점수 규칙
- 텔레그램 즉시 알림
- 텔레그램 일일 요약
- Cloudflare Worker KV를 이용한 중복 알림 상태 저장
- GitHub Actions 정기 실행

이번 1차에서 제외:

- Google 검색 기반 수집
- 삼성/LG/GS처럼 현재 목록 구조가 불안정한 사이트의 본격 지원
- 자소서 자동 생성 결과물 저장
- 지원서 자동 제출

## User Workflow

1. GitHub Actions가 하루 여러 번 사이트를 순회한다.
2. 수집한 공고는 제목/카드 텍스트 기준으로 1차 역할 적합도를 계산한다.
3. 상위 공고만 상세 페이지 본문을 열어 포트폴리오 기반 fit 점수와 지원 초안 근거를 만든다.
4. 최종 점수 85점 이상 신규 공고는 즉시 텔레그램으로 보낸다.
5. 65점 이상 84점 이하 신규 공고는 당일 요약 후보로만 적재한다.
6. 밤 21:30 KST에 하루 동안 누적된 후보를 요약 텔레그램으로 보낸다.

## Architecture

### Overall

기존 `jobs/core.py`의 후보자 fit 평가와 OpenAI 호출, 텔레그램 연동은 재사용하고, AI 품질 전용 소스/점수/상태 관리를 `jobs/ai_quality_monitor.py`로 분리한다.

### New Components

1. **AI Quality Profile**
   - 기존 후보자 프로필을 기반으로 하되 `평가`, `품질`, `안전성`, `red teaming`, `LLM eval` 쪽 가중치를 높인다.
   - 사용자가 제공한 seed 공고를 기준점으로 유지한다.

2. **Source Collectors**
   - 1차 구현 소스:
     - Wanted
     - 카카오
     - 카카오뱅크
     - NAVER Careers
     - 현대오토에버
     - KT Careers
     - SK Careers
     - HYBE Careers
   - 2차 후보 소스:
     - LG Careers
     - Samsung Careers
     - GS Caltex Careers

3. **Role Scoring Layer**
   - title/body에서 `AI + 품질/평가/안전성` 조합 여부를 본다.
   - 일반 서비스 QA, 제조 품질, 협력사 품질보증처럼 사용자의 목표와 다른 QA는 강하게 감점한다.

4. **Candidate Fit Layer**
   - `jobs/core.py`의 LLM 기반 fit 평가를 그대로 사용한다.
   - 포트폴리오/README/이력서 문맥은 기존 로더를 그대로 이용한다.

5. **State Store**
   - Cloudflare Worker KV에 아래 상태를 보관한다.
   - `ai-quality/high-fit-seen`
   - `ai-quality/summary/<YYYY-MM-DD>`
   - 로컬 실행 시에는 JSON 파일 fallback을 제공한다.

## Scoring Model

최종 점수는 아래 3층으로 계산한다.

1. **Role Score**
   - AI 품질 역할 그 자체와의 유사도
   - 예:
     - `AI 서비스 품질`
     - `안전성 평가`
     - `AI Quality`
     - `LLM Evaluation`
     - `Prompt Evaluation`
     - `Red Teaming`

2. **Seed Similarity**
   - 사용자가 준 기준 공고와의 유사도
   - seed 예시:
     - 카카오뱅크 `AI 서비스 품질 및 안전성 평가 담당자`
     - LG CNS `품질관리자 모집` 내 `AI 품질 엔지니어`

3. **Candidate Fit**
   - 기존 fit monitor와 같은 방식으로 포트폴리오/이력서 기반 적합도를 계산한다.

권장 가중치:

- role score 40%
- candidate fit 45%
- seed similarity 15%

## Alert Policy

### Immediate Alert

- 기준: 최종 점수 85 이상
- 대상: 이전에 즉시 알림을 보낸 적 없는 신규 공고
- 내용:
  - 회사
  - 공고 제목
  - 최종 점수
  - 짧은 적합 사유
  - 링크

### Daily Summary

- 기준: 최종 점수 65 이상
- 대상: 당일 누적 신규 공고 중 `즉시 알림으로 이미 보낸 85점 이상 공고를 제외한 나머지`
- 공고가 없으면 `오늘 새로 포착한 AI 품질 관련 공고가 없습니다.` 메시지를 보낸다.

## Failure Handling

- 한 소스 실패로 전체 워크플로를 실패시키지 않는다.
- 모든 소스가 실패했을 때만 워크플로를 실패시킨다.
- 상세 페이지 수집 실패는 목록 결과를 살리고 본문 없는 상태로 계속 평가한다.
- 브리지 상태 저장 실패 시:
  - 로컬 실행은 JSON fallback 사용
  - GitHub Actions는 경고 로그를 남기고 당회차 알림은 계속 진행한다

## Data Layout

새로 추가할 파일:

```text
jobs/
  ai_quality_profile.py
  ai_quality_monitor.py
  run_ai_quality_job_monitor.py

data/job_monitors/
  ai_quality_state.json

tests/
  test_ai_quality_job_monitor.py
```

## Schedules

1차 권장 스케줄:

- 즉시 알림 수집: 매일 `09:15`, `13:15`, `17:15`, `21:15` KST
- 일일 요약: 매일 `21:30` KST

즉시 알림과 일일 요약을 분리한 이유:

- 즉시 알림은 고적합 신규 공고만 짧게 보낸다.
- 요약은 그보다 낮지만 확인할 가치가 있는 공고를 묶어서 보낸다.

## Testing Strategy

1. 역할 점수 규칙 단위 테스트
2. 요약 후보 병합/중복 제거 단위 테스트
3. NAVER 링크 복원 로직 단위 테스트
4. 로컬 dry-run 스모크 테스트
5. `python3 -m compileall` 문법 검증
6. `node --check`로 Cloudflare Worker 문법 검증

## Success Criteria

아래가 되면 1차 성공이다.

- 여러 회사 채용 페이지에서 AI 품질 계열 공고를 실제로 수집한다.
- 일반 제조 QA나 무관한 운영 공고는 점수상 뒤로 밀린다.
- 고적합 공고는 중복 없이 즉시 텔레그램으로 온다.
- 나머지는 하루 한 번 요약으로 온다.
- 상태는 GitHub Actions 재실행 간에도 유지된다.
