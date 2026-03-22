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
