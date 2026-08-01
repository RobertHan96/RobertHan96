# 한영신 · 이다예 모바일 청첩장

모바일 Safari, Chrome, 카카오톡 인앱 브라우저를 우선으로 만든 React 정적 청첩장입니다. 현재는 아기 사진과 예식 기본 정보를 사용하며, 추후 `src/config/wedding.ts`의 사진 배열과 설정만 바꾸면 웨딩 갤러리와 상세 안내를 확장할 수 있습니다.

## 로컬 실행

Node.js 24 LTS 기준입니다.

```bash
npm install
npm run dev
```

검증 명령은 아래와 같습니다.

```bash
npm test -- --run
npm run lint
npm run build
```

## 정보 수정

- 예식·가족·문구·연락처: `src/config/wedding.ts`
- 신랑·신부 아기 사진: `public/images/baby/`
- 웨딩 사진: `public/images/wedding/` 생성 후 `gallery.wedding` 배열에 추가
- 약도와 공유 이미지: `public/images/location/map.jpeg`
- 전체 디자인: `src/index.css`

현재 계좌, RSVP, T맵 링크, 카카오 JavaScript 키는 미입력 상태입니다. 화면에는 준비 중 상태로 표시되며 정보가 확정된 뒤 기능을 연결합니다.

## Cloudflare Pages

Git 저장소를 Pages에 연결할 때 다음 값을 사용합니다.

| 항목 | 값 |
| --- | --- |
| Root directory | `wedding-invitation` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Node version | `24` |

최종 도메인이 정해지면 `index.html`의 `og:image`를 절대 URL로 변경해야 카카오톡 대표 이미지가 안정적으로 표시됩니다. RSVP를 추가할 때만 Pages Functions와 D1을 연결합니다.

## 개인정보 주의

현재 설정에는 신랑·신부 연락처가 포함되어 있습니다. 공개 저장소에 올리면 소스와 빌드 결과에서 누구나 확인할 수 있습니다. 계좌번호와 부모님 연락처를 추가하기 전에는 저장소 공개 범위와 노출 시점을 다시 확인하세요.
