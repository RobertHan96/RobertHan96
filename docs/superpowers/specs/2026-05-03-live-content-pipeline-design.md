# Live Content Pipeline Design

**Date:** 2026-05-03

## Goal

유튜브 라이브 방송을 `OBS 로컬 녹화본` 기준으로 후처리해서, 다음 산출물을 로컬에서 반자동으로 만드는 파이프라인을 구축한다.

- Hugo 블로그 초안
- 숏츠 후보 구간
- 숏츠 1차 렌더 파일
- 게시 직전 검토용 메타데이터

이 파이프라인은 대용량 영상 원본을 GitHub Actions나 클라우드 저장소에 올리지 않고, 현재 로컬 프로젝트 환경에서 실행되는 것을 기본 원칙으로 한다.

## Scope

이번 1차 구현 범위는 아래까지다.

- 로컬 녹화본 목록을 보여주는 대시보드 웹페이지
- 선택한 영상에 대해 `STT 실행`
- 선택한 영상에 대해 `AI 주제/챕터/요약 추출`
- Hugo 블로그 초안 생성
- 숏츠 후보 구간 3~5개 생성
- 숏츠용 짧은 보이스오버를 ElevenLabs TTS로 생성
- `ffmpeg` 기반 9:16 숏츠 1차 렌더

이번 1차 구현에서 제외한다.

- 유튜브/쇼츠 자동 업로드
- 완전 무인 게시
- 클라우드 영상 저장
- 장시간 전체 더빙
- 고급 GUI 편집기 수준의 수동 타임라인 편집

## User Workflow

1. 사용자는 `OBS`로 라이브를 송출하면서 로컬 녹화를 남긴다.
2. 녹화 종료 후 파일은 미리 지정한 로컬 디렉터리에 저장된다.
3. 사용자는 로컬 대시보드에서 최근 녹화 영상을 확인한다.
4. 영상 하나를 선택해 `STT 실행` 버튼을 누른다.
5. 파이프라인은 오디오 추출 후 ElevenLabs STT로 transcript를 만든다.
6. 사용자는 `AI 영상 주제 뽑기`를 실행한다.
7. 파이프라인은 transcript를 분석해 아래 산출물을 만든다.
   - 영상 주제 후보
   - 챕터
   - 핵심 요약
   - 블로그 초안
   - 숏츠 후보
8. 사용자는 숏츠 후보 중 하나를 선택해 1차 렌더를 만든다.
9. 최종 미감 보정은 선택적으로 Descript, Premiere, OpusClip 같은 외부 AI 편집 도구로 마감한다.
10. 검토 후 블로그 게시와 숏츠 업로드는 사용자가 수동 승인한다.

## Architecture

### Overall

로컬 단일 프로젝트 안에서 돌아가는 `Python orchestration + FastAPI dashboard + ffmpeg + ElevenLabs API` 구조를 사용한다.

### Core Components

1. **Recording Scanner**
   - 지정한 녹화 디렉터리를 스캔한다.
   - 영상 메타데이터를 읽어 목록을 구성한다.
   - 최근 녹화본 정렬, 상태 표시, 결과 경로 연결을 담당한다.

2. **Transcription Pipeline**
   - 영상에서 오디오를 추출한다.
   - ElevenLabs STT API로 transcript를 생성한다.
   - 한국어 중심 + 영어 기술용어 혼합에 맞춰 후처리한다.

3. **Content Analyzer**
   - transcript를 기반으로 주제/챕터/핵심 요약을 생성한다.
   - 블로그용 구조화 요약과 숏츠용 하이라이트 후보를 만든다.

4. **Blog Draft Writer**
   - Hugo 포스트 초안을 생성한다.
   - `draft: true` 상태로 저장한다.
   - 방송 주제, 시도한 것, 막힌 점, 해결한 점, 코드/명령어, 실무 팁을 구조화한다.

5. **Shorts Pipeline**
   - 숏츠 후보 타임코드를 기준으로 구간을 자른다.
   - 필요 시 ElevenLabs TTS로 짧은 도입/전환 멘트를 생성한다.
   - `ffmpeg`로 9:16 렌더, 자막 입히기, 기본 브랜딩을 수행한다.

6. **Dashboard**
   - 로컬 웹 UI
   - 최근 녹화본 리스트 표시
   - STT 실행
   - AI 주제 뽑기
   - 블로그 초안/숏츠 후보 상태 확인

## Technical Choices

### Web App

- **Framework:** FastAPI
- **Reason:** 이미 repo에 Python 자동화 구조가 있고, 가벼운 로컬 API + HTML 템플릿 조합에 적합하다.

### Video Processing

- **Tool:** ffmpeg
- **Reason:** 컷 편집, 리사이즈, 자막 합성, 오디오 추출을 자동화하기 가장 안정적이다.

### STT / TTS

- **Vendor:** ElevenLabs
- **STT:** 영상 transcript 생성
- **TTS:** 숏츠용 짧은 내레이션/전환 멘트 생성

### AI Text Analysis

- **LLM:** 기존 프로젝트의 `OPENAI_MODEL`
- **Role:** 주제 추출, 챕터링, 블로그 초안, 숏츠 후보 선정

## Data Layout

아래 구조를 새로 만든다.

```text
data/live_pipeline/
  recordings/
    manifest.json
  transcripts/
    <recording-id>.json
    <recording-id>.txt
  analysis/
    <recording-id>.json
  blog_drafts/
    <recording-id>.md
  shorts/
    <recording-id>/
      candidates.json
      voiceover/
      subtitles/
      renders/
```

### Recording ID

녹화본 식별자는 아래 조합으로 만든다.

- 파일명 slug
- 수정 시각
- 파일 크기

이 조합으로 동일 영상 재처리 시 결과 경로를 안정적으로 재사용한다.

## Dashboard Features

이번 1차 버전의 주요 기능은 아래 3개다.

1. **최근 녹화된 영상 리스트 확인**
   - 파일명
   - 녹화 시각
   - 길이
   - 용량
   - 현재 처리 상태

2. **STT 돌리기**
   - 선택 영상에 대해 transcript 생성
   - 진행 상태와 결과 경로 표시

3. **AI 영상 주제 뽑기**
   - 제목 후보
   - 핵심 주제
   - 챕터
   - 블로그 요약
   - 숏츠 후보 개수

추가로 UI에는 아래 보조 정보를 같이 둔다.

- 블로그 초안 생성 여부
- 숏츠 후보 생성 여부
- 렌더 결과물 경로

## Blog Draft Format

블로그 초안은 Hugo 포스트 형식으로 저장한다.

- 위치: `content/posts/<slug>/index.md`
- 상태: `draft: true`
- 기본 섹션:
  - 문제 배경
  - 오늘 다룬 기술
  - 구현 흐름
  - 막힌 점
  - 해결 방법
  - 배운 점
  - 다음 실험 아이디어

## Shorts Candidate Rules

숏츠 후보는 transcript 기준으로 3~5개 생성한다.

후보당 포함 정보:

- `start_seconds`
- `end_seconds`
- `hook`
- `title_candidate`
- `summary`
- `why_this_clip`

우선순위는 아래 특성을 높게 본다.

- 놀라운 결과
- 실수/삽질 뒤 해결
- 최신 AI/SW 개발 트렌드
- 실무 팁
- 한 문장으로 전달 가능한 교훈

## Error Handling

- 녹화본 메타데이터 파싱 실패는 개별 파일 단위로 격리한다.
- STT 실패는 transcript 단계만 실패 처리하고, 다른 영상 목록에는 영향 주지 않는다.
- 분석 실패는 transcript를 보존한 채 재시도 가능 상태로 남긴다.
- 숏츠 렌더 실패는 해당 후보만 실패 처리한다.
- 대시보드에서는 단계별 상태를 `pending/running/succeeded/failed`로 보여준다.

## Security / Privacy

- 영상 원본은 로컬에만 저장한다.
- API 키는 `.env`에서 읽는다.
- transcript와 분석 결과는 로컬 프로젝트 디렉터리 안에 저장한다.
- 외부로 전송되는 데이터는 ElevenLabs STT/TTS와 LLM 분석 요청에 필요한 텍스트/오디오로 제한한다.

## Environment Variables

필수:

- `ELEVENLABS_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

선택:

- `LIVE_PIPELINE_RECORDINGS_DIR`
- `LIVE_PIPELINE_OUTPUT_DIR`
- `LIVE_PIPELINE_DEFAULT_VOICE_ID`

## Testing Strategy

1. 녹화 디렉터리 스캔 단위 테스트
2. transcript 후처리 단위 테스트
3. 분석 결과 스키마 단위 테스트
4. 블로그 초안 렌더 테스트
5. 숏츠 후보 JSON 생성 테스트
6. FastAPI 라우트 스모크 테스트
7. ffmpeg 명령 생성 테스트

## MVP Success Criteria

아래가 되면 1차 성공이다.

- 대시보드에서 최근 녹화본 목록이 보인다
- 영상 하나를 골라 STT를 돌릴 수 있다
- STT 결과로 주제/챕터/블로그 초안/숏츠 후보가 생성된다
- 숏츠 후보 하나를 실제 9:16 파일로 렌더할 수 있다
- 블로그 초안이 Hugo 포스트 초안으로 저장된다

## Recommendation

이번 구현은 `로컬 우선, 자동화는 강하게, 게시는 반자동` 원칙으로 간다.

이 방식이 현재 사용자의 방송/개발 콘텐츠 제작 방식과 가장 잘 맞고, 대용량 영상 처리와 결과물 검수 모두에서 리스크가 가장 낮다.
