# 모바일 청첩장 디자인 명세

## 목표

한영신·이다예의 모바일 청첩장을 독립 React + Vite 정적 앱으로 구현한다. 첫 단계는 로컬에서 완성된 화면을 확인하고 Cloudflare Pages에 정적 배포할 수 있는 상태까지이며, RSVP 저장과 D1 연결은 실제 응답 정책이 정해진 뒤 별도 단계로 연결한다.

## 시각 방향

- 선택안: `Botanical Letter`
- 아이보리 종이 질감, 절제된 식물 선화, 한국어 명조와 영문 세리프 조합
- 모바일 390px 화면을 기준으로 설계하고 데스크톱에서는 최대 430px 콘텐츠를 중앙에 배치
- 장식보다 사진·문장·여백의 흐름을 우선
- 스크롤 진입 애니메이션은 CSS와 IntersectionObserver만 사용하며 `prefers-reduced-motion`을 존중

## 콘텐츠

### Hero

- 신랑 한영신과 신부 이다예의 아기 사진을 나란한 아치형 프레임으로 표시
- `Together, forever`, 두 사람의 이름, `2026. 11. 15`, `오후 3시 50분`, `더컨벤션 잠실 · 3층 비스타홀` 표시
- 사진은 얼굴이 잘리지 않도록 개별 `object-position` 값을 설정 파일에서 관리

### Invitation

- 제목: `서로의 오늘이 되어`
- 본문:

  > 각자의 시간 속에서 자라온 두 사람이  
  > 이제 같은 계절을 바라보며  
  > 한 길을 걸어가려 합니다.  
  > 저희의 새로운 시작에 함께하시어  
  > 따뜻한 축복을 더해주시면 감사하겠습니다.

### Couple

- 신랑 부모: 한성용·황진심
- 신부 부모: 이성환·오영근
- 신랑·신부 전화 및 문자 연결 버튼 제공
- 부모 연락처는 값이 없으므로 이름만 표시하고 연락 버튼은 렌더링하지 않음

### Our Story / Gallery

- 신랑·신부 아기 사진을 편지 위에 올린 사진처럼 표시
- 사진 선택 시 전체 화면 viewer를 열고, 닫기·이전·다음·키보드·모바일 swipe를 지원
- `TO BE CONTINUED...`와 `Wedding photos coming soon` 표시
- 설정 파일의 `gallery.wedding` 배열과 `comingSoon` 값만 바꾸면 웨딩 사진 갤러리가 이어서 표시되는 구조

### Wedding Day

- 2026년 11월 달력과 15일 강조
- 현재 시각 기준 D-Day를 계산하며 예식 당일과 지난 날짜 문구도 처리
- 날짜와 시간은 한국 표준시 기준

### Location

- 더컨벤션 잠실, 3층 비스타홀, 서울 송파구 올림픽로 319 3층 표시
- 주소 복사 버튼 제공
- 첨부 약도 이미지를 표시하고 확대 viewer를 지원
- 지도 링크는 값이 비어 있으므로 버튼 대신 `길찾기 링크 준비 중` 상태 표시

### 보류 영역

- 교통, 계좌, RSVP는 섹션 구조와 시각적 위치만 구현
- 값이 비어 있으면 `안내를 준비하고 있습니다`를 표시
- RSVP는 입력값을 받거나 전송하지 않고 `참석 여부 전달은 추후 오픈됩니다`로 표시
- 링크 복사는 현재 주소로 작동하고 카카오 공유는 키가 없으므로 비활성 안내를 표시

### Footer / Metadata

- Footer에 `한영신 ♥ 이다예`와 `2026. 11. 15` 표시
- 문서 제목과 Open Graph 제목·설명·이미지를 설정
- 임시 Open Graph 이미지는 약도를 사용

## 구조

- 앱 경로: `wedding-invitation/`
- 개인정보, 문구, 이미지 경로는 `src/config/wedding.ts` 한 곳에서 관리
- 화면 컴포넌트는 Hero, Invitation/Couple, Gallery, WeddingDay, Location/Pending/Share 수준으로만 분리
- 날짜 계산과 클립보드 처리는 작은 유틸리티로 분리
- 이미지 원본은 `public/images/baby`, `public/images/location`에 복사

## 호환성과 성능

- 모바일 Safari, Chrome, 카카오톡 인앱 브라우저에서 사용할 수 있는 표준 DOM API만 사용
- 이미지에 width/height 또는 aspect-ratio를 지정해 layout shift를 억제
- Hero 이미지는 eager, 이후 이미지는 lazy loading
- 터치 영역은 최소 44px, safe-area inset 반영
- 빌드 타깃은 구형 모바일 브라우저를 고려한 `es2019`

## 테스트

- Vitest + Testing Library로 실제 콘텐츠 렌더링, 날짜 계산, 빈 데이터 fallback, viewer 열기/닫기를 검증
- TypeScript 검사, ESLint, 프로덕션 빌드 수행
- 로컬 서버에서 390px 모바일과 데스크톱 화면을 시각 검증
- 콘솔 오류와 가로 overflow 여부 확인

## 제외 범위

- Cloudflare Pages Functions와 D1 RSVP 저장
- 관리자 페이지, 방명록, 로그인, BGM, 하객 업로드, 결제
- 실제 계좌, 교통, 지도 링크, 카카오 JavaScript 키 연결

