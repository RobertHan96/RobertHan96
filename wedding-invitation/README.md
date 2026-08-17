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

RSVP와 T맵 링크는 사용하지 않습니다. 카카오 공유 버튼은 빌드 환경에 JavaScript 키가 있으면 활성화됩니다.

## 카카오톡 공유 설정

1. 카카오디벨로퍼스에서 앱을 만들고 `[앱] > [플랫폼 키] > [JavaScript 키]`를 발급합니다.
2. 같은 JavaScript 키 설정의 `JavaScript SDK 도메인`에 `https://roberthan96.pages.dev`를 등록합니다.
3. `[앱] > [제품 링크 관리] > [웹 도메인]`에도 `https://roberthan96.pages.dev`를 등록합니다.
4. Cloudflare Pages의 Production 환경변수에 `VITE_KAKAO_JAVASCRIPT_KEY` 이름으로 JavaScript 키를 등록합니다.
5. 로컬 테스트가 필요하면 `.env.example`을 참고해 `.env.local`에 같은 변수를 등록합니다.
6. 새 배포를 실행한 후 실제 카카오톡 앱에서 공유 버튼과 메시지 링크를 확인합니다.

JavaScript 키는 브라우저에서 사용하는 공개 플랫폼 키입니다. Vite 빌드 결과에는 값이 포함되므로 비밀 저장 목적이 아니라 환경별 설정을 위한 방식이며, REST API 키나 어드민 키를 입력하면 안 됩니다.

## Cloudflare Pages

Git 저장소를 Pages에 연결할 때 다음 값을 사용합니다.

| 항목 | 값 |
| --- | --- |
| Root directory | `wedding-invitation` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Node version | `24` |

Open Graph 이미지와 공유 링크는 `https://roberthan96.pages.dev/` 기준으로 설정되어 있습니다. 커스텀 도메인을 연결하면 `src/config/wedding.ts`와 `index.html`의 URL을 함께 변경해야 합니다.

## 게스트 스냅 설정

게스트 스냅은 Pages Functions, 비공개 R2, D1, Turnstile을 사용합니다.

1. R2 버킷 `wedding-guest-snap`을 만들고 Pages 프로젝트에 `GUEST_SNAP_BUCKET` 이름으로 바인딩합니다.
2. D1 데이터베이스 `wedding-guest-snap`을 만들고 `GUEST_SNAP_DB` 이름으로 바인딩합니다.
3. `npx wrangler d1 migrations apply wedding-guest-snap --remote`로 `migrations/0001_guest_snap.sql`을 적용합니다.
4. Turnstile 위젯을 만들고 공개 Site Key는 빌드 변수 `VITE_TURNSTILE_SITE_KEY`로 등록합니다.
5. Turnstile Secret Key는 암호화된 변수 `TURNSTILE_SECRET_KEY`로 등록합니다.
6. 관리자 비밀번호는 암호화된 변수 `GUEST_SNAP_ADMIN_PASSWORD`로 등록합니다.
7. 일반 변수 `GUEST_SNAP_UPLOAD_OPENS_AT`에는 `2026-11-15T00:00:00+09:00`을 등록합니다.
8. 바인딩과 변수를 등록한 뒤 Production을 다시 배포합니다.

사진은 승인 전까지 외부에서 접근할 수 없으며 `/guest-snap-admin`에서 승인, 제외, 삭제합니다. 공개 버킷 URL은 활성화하지 않습니다. 로컬 Vite 서버에서는 UI만 확인할 수 있고 실제 Functions 테스트는 Cloudflare Pages의 Preview 배포에서 진행합니다.

## 개인정보 주의

현재 설정에는 신랑·신부 연락처가 포함되어 있습니다. 공개 저장소에 올리면 소스와 빌드 결과에서 누구나 확인할 수 있습니다. 계좌번호와 부모님 연락처를 추가하기 전에는 저장소 공개 범위와 노출 시점을 다시 확인하세요.
