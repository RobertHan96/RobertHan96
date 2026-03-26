학습을 즐기고, 항상 목표 달성을 위해 나아가는 개발자 한영신 입니다.   
즐거운 👩‍💻   을 위해 긍정적으로 생각하고, 새로운 것을 배우는 것 또한 좋아합니다.   
자세한 내용은 각 페이지에서 확인 해주세요!

*** 

### 🎫   [자기소개와 이력서](https://github.com/RobertHan96/RobertHan96/blob/main/resume.md)

*** 

### 💼 [포트폴리오](https://github.com/RobertHan96/RobertHan96/blob/main/portfolio.pdf)

*** 

### ✍️ 블로그 작성 가이드

이제 Hugo 포스트는 로컬에서 파일을 만들고 `git push`하지 않아도 됩니다.  
GitHub의 `Issues`에서 `블로그 글 작성` 폼을 열어 내용만 작성하면, GitHub Actions가 자동으로 `content/posts/<slug>/index.md` 파일을 만들고 커밋한 뒤 배포까지 연결합니다.

#### 가장 쉬운 방법: Issue Form으로 작성

1. GitHub 저장소의 `Issues` 탭으로 이동합니다.
2. `New issue`에서 `블로그 글 작성` 템플릿을 선택합니다.
3. 아래 항목을 입력합니다.
   - 글 제목
   - 슬러그(선택)
   - 한 줄 요약
   - 태그
   - 카테고리
   - 발행 방식: `초안으로 저장` 또는 `즉시 발행`
   - 본문(Markdown)
4. 이슈를 등록하면 GitHub Actions가 자동으로 포스트를 생성합니다.
5. 처리 결과는 해당 이슈 댓글로 안내됩니다.

#### 동작 방식

- `초안으로 저장`을 선택하면 `draft: true`로 생성됩니다.
- `즉시 발행`을 선택하면 `draft: false`로 생성되어 배포됩니다.
- 같은 이슈를 수정하면 기존 포스트가 다시 갱신됩니다.
- 제목이나 슬러그를 바꾸면 포스트 폴더도 함께 이동됩니다.
- 공개 저장소이지만 실제 포스트 생성은 `OWNER`, `MEMBER`, `COLLABORATOR` 권한이 있는 작성자만 실행됩니다.

#### 예전 방식도 가능

필요하면 기존처럼 로컬에서 직접 포스트를 작성하거나, `scripts/publish.py`를 사용해 Confluence 문서를 Hugo 포스트 초안으로 변환할 수도 있습니다.  
다만 평소에는 Issue Form 방식이 가장 빠르고 편합니다.

*** 

### 📈 주식 워치리스트 가이드

주식/관심 뉴스 모니터링용 워치리스트는 이제 로컬 파일 대신 Google Sheets의 `웹에 게시된 CSV`를 기본 소스로 사용합니다.  
Google Sheets API, OAuth, 서비스 계정 없이 `게시된 CSV URL`만 있으면 됩니다.

#### 설정 방법

1. Google Sheets에서 워치리스트 시트를 만듭니다.
2. `파일 > 공유 > 웹에 게시`에서 해당 시트를 CSV로 게시합니다.
3. 발급된 CSV URL을 GitHub 저장소 `Variables`의 `WATCHLIST_PUBLISHED_CSV_URL` 에 저장합니다.
4. GitHub Actions가 실행될 때 이 값을 환경변수로 받아 워치리스트를 읽습니다.

#### CSV 컬럼 구조

헤더는 아래 순서를 권장합니다.

```csv
symbol,name,market,enabled,price_enabled,news_enabled,price_threshold_pct,price_provider,price_symbol,news_provider,news_symbol,countries,language
```

예시:

```csv
symbol,name,market,enabled,price_enabled,news_enabled,price_threshold_pct,price_provider,price_symbol,news_provider,news_symbol,countries,language
NVDA,NVIDIA,us,true,true,true,3.0,twelvedata,NVDA,marketaux,NVDA,us,en
TSLA,Tesla,us,true,true,true,3.0,twelvedata,TSLA,marketaux,TSLA,us,en
005930,삼성전자,kr,true,true,false,3.0,legacy_naver,005930,marketaux,005930,kr,ko
```

#### 컬럼 설명

- `symbol`: 내부 표시용 기본 심볼
- `name`: 텔레그램에 표시할 이름
- `market`: `us` 또는 `kr`
- `enabled`: 전체 on/off
- `price_enabled`: 가격 알림 on/off
- `news_enabled`: 뉴스 알림 on/off
- `price_threshold_pct`: 종목별 가격 변동 임계치
- `price_provider`: `twelvedata`, `legacy_naver`, `legacy_yahoo`
- `price_symbol`: 가격 API 호출에 사용할 심볼
- `news_provider`: 현재 `marketaux`
- `news_symbol`: 뉴스 API 호출에 사용할 심볼
- `countries`: 뉴스 국가 필터
- `language`: 뉴스 언어 필터

#### 참고

- 미국 종목은 `Twelve Data + Marketaux` 조합을 기본으로 사용합니다.
- 한국 종목은 현재 free tier 한계 때문에 가격은 `legacy_naver` fallback 을 유지하고 있습니다.
- 샘플 CSV는 [watchlist.csv](/Users/han/Desktop/Dev/RobertHan96/data/watchlist.csv) 에 남겨두었습니다.

***

### 🧠 투자자료 RAG 가이드

투자 관련 PDF, 메모, 이미지 자료를 계속 쌓아두고 Telegram에서 질문하면, OpenAI File Search 기반으로 관련 자료를 검색해 답변하도록 확장할 수 있습니다.  
별도 벡터 DB 서버를 두지 않고, OpenAI Vector Store를 그대로 사용합니다.

#### 현재 포함된 구성

- 수동 자료 동기화 스크립트: [investment_rag_sync.py](/Users/han/Desktop/Dev/RobertHan96/scripts/automation/investment_rag_sync.py)
- OpenAI Vector Store 공통 모듈: [investment_rag.py](/Users/han/Desktop/Dev/RobertHan96/scripts/automation/investment_rag.py)
- 일일 투자 브리프 생성기: [investment_digest.py](/Users/han/Desktop/Dev/RobertHan96/scripts/automation/investment_digest.py)
- Telegram webhook 앱: [telegram_rag_app.py](/Users/han/Desktop/Dev/RobertHan96/services/telegram_rag_app.py)

#### 자료 적재 방식

- 직접 넣고 싶은 자료는 [investment_docs](/Users/han/Desktop/Dev/RobertHan96/data/investment_docs) 에 둡니다.
- 필요할 때 수동 실행으로 워치리스트 가격/뉴스를 요약한 markdown 문서를 생성해 [investment_rag](/Users/han/Desktop/Dev/RobertHan96/data/investment_rag) 아래에 누적할 수 있습니다.
- PDF, TXT, MD, JSON, HTML, DOCX, PPTX는 바로 적재합니다.
- 이미지(`png/jpg/jpeg/webp`)는 OCR 후 markdown으로 변환해서 적재합니다.

#### 필요한 환경변수

- `OPENAI_API_KEY`
- `MARKETAUX_API_TOKEN`
- `TWELVE_DATA_API_KEY`
- `WATCHLIST_PUBLISHED_CSV_URL`
- `INVESTMENT_VECTOR_STORE_NAME`
- `INVESTMENT_VECTOR_STORE_ID`  
  처음엔 없어도 되지만, 한 번 생성된 store id를 여기에 넣어두면 수동 실행과 webhook 앱이 항상 같은 Vector Store를 안정적으로 재사용합니다.
- `INVESTMENT_RAG_MODEL`
- `INVESTMENT_OCR_MODEL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET_TOKEN`

#### Telegram 질의응답 방식

- Telegram은 상시 서버 대신 webhook 방식으로 받습니다.
- 앱 엔트리포인트는 [telegram_rag_app.py](/Users/han/Desktop/Dev/RobertHan96/services/telegram_rag_app.py) 입니다.
- Cloud Run, Vercel, Functions 같은 serverless HTTPS 환경에 배포한 뒤 Telegram `setWebhook` 으로 `/telegram/webhook` URL을 연결하면 됩니다.
- 텍스트 메시지는 RAG 질의응답, PDF/문서는 즉시 적재, 이미지는 OCR 후 적재합니다.

#### 로컬 실행 예시

```bash
uvicorn services.telegram_rag_app:app --host 0.0.0.0 --port 8000
python3 scripts/automation/investment_rag_sync.py --generate-digest
```

***

### 💬 텔레그램 메모리/RAG 가이드

텔레그램으로 오간 내용을 가볍게 기억하고, 파일 첨부 자료는 바로 RAG에 넣을 수 있는 구조를 추가했습니다.  
별도 서버 대신 `Cloudflare Worker -> GitHub Actions -> repo 파일 저장 + SQLite FTS5` 흐름으로 동작합니다.

#### 현재 포함된 구성

- Cloudflare Worker 브리지: [worker.mjs](/Users/han/Desktop/Dev/RobertHan96/services/cloudflare-telegram-bridge/worker.mjs)
- Telegram 인입 workflow: [telegram-memory.yml](/Users/han/Desktop/Dev/RobertHan96/.github/workflows/telegram-memory.yml)
- 일일 요약 workflow: [telegram-memory-digest.yml](/Users/han/Desktop/Dev/RobertHan96/.github/workflows/telegram-memory-digest.yml)
- 메모리/검색 모듈: [telegram_memory.py](/Users/han/Desktop/Dev/RobertHan96/scripts/automation/telegram_memory.py)
- 이벤트 처리기: [telegram_memory_event.py](/Users/han/Desktop/Dev/RobertHan96/scripts/automation/telegram_memory_event.py)

#### Telegram에서 쓰는 방법

1. 일반 텍스트를 보내면 저장하지 않고 바로 검색 질문으로 처리됩니다.
2. `/ask 질문내용`은 일반 텍스트와 동일한 검색 별칭입니다.
3. `pdf`, `txt`, `md`, `html`, `json`, `docx` 파일을 보내면 문서로 저장되고 즉시 RAG 인덱스에 반영됩니다.
4. 기존 자동화 태스크가 텔레그램으로 보낸 메시지와 일반 텍스트 대화는 Worker KV에 임시 버퍼링됩니다.
5. 매일 1번 일일 요약 workflow가 전날 대화/알림 로그를 요약해 [summaries](/Users/han/Desktop/Dev/RobertHan96/data/telegram_memory/summaries)에 저장하고 커밋합니다.

#### 저장 위치

- 원본 로그: [data/telegram_memory](/Users/han/Desktop/Dev/RobertHan96/data/telegram_memory)
- SQLite 검색 인덱스: [index.db](/Users/han/Desktop/Dev/RobertHan96/data/telegram_memory/index.db)
- 첨부 파일 원문/추출 텍스트: [inbox](/Users/han/Desktop/Dev/RobertHan96/data/telegram_memory/inbox)
- 일일 요약: [summaries](/Users/han/Desktop/Dev/RobertHan96/data/telegram_memory/summaries)

#### Cloudflare에서 해야 할 설정

1. Cloudflare Dashboard에서 새 Worker를 만듭니다.
2. [worker.mjs](/Users/han/Desktop/Dev/RobertHan96/services/cloudflare-telegram-bridge/worker.mjs) 내용을 붙여넣어 배포합니다.
3. Worker에 KV namespace를 하나 만들고 `TELEGRAM_MEMORY_KV` 이름으로 바인딩합니다.
4. Worker 환경변수를 설정합니다.
   - `GITHUB_REPOSITORY`: `RobertHan96/RobertHan96`
   - `TELEGRAM_MEMORY_BRIDGE_TOKEN`: 브리지 읽기/쓰기용 랜덤 토큰
5. Worker secret을 설정합니다.
   - `GITHUB_TOKEN`: `repo` 권한 또는 해당 저장소 dispatch 권한이 있는 토큰
   - `TELEGRAM_WEBHOOK_SECRET_TOKEN`: 임의의 긴 랜덤 문자열
6. Worker URL을 배포한 뒤 Telegram webhook을 연결합니다.

예시:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -d "url=https://<your-worker>.workers.dev" \
  -d "secret_token=<TELEGRAM_WEBHOOK_SECRET_TOKEN>"
```

#### GitHub Secrets / Variables

- `Secrets`
  - `TELEGRAM_BOT_TOKEN`
  - `OPENAI_API_KEY`
  - `TELEGRAM_MEMORY_BRIDGE_TOKEN`
- `Variables`
  - `TELEGRAM_MEMORY_MODEL` 선택 사항. 기본값은 `gpt-4o-mini`
  - `TECH_NEWS_MODEL` 선택 사항. 기본값은 `gpt-4o-mini`
  - `TELEGRAM_MEMORY_BRIDGE_URL`

#### 참고

- 이 구조는 무료 인프라 기준으로 가장 단순한 편이지만, OpenAI 답변 생성은 호출량에 따라 비용이 발생할 수 있습니다.
- 일반 텍스트 대화와 자동화 알림은 즉시 git push하지 않고, 하루 1번 요약해서만 저장합니다.
- 파일 첨부는 의도적인 자료 적재로 보고 즉시 저장/커밋됩니다.
- 메모리 관련 커밋이 있어도 페이지 배포가 불필요하게 돌지 않도록 [deploy.yml](/Users/han/Desktop/Dev/RobertHan96/.github/workflows/deploy.yml) 에 `data/telegram_memory/**` 경로는 배포 제외로 처리했습니다.
