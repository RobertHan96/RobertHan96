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

게스트 스냅은 Pages Functions, 비공개 R2, Turnstile만 사용합니다. 이름이나 메시지는 수집하지 않으며 D1과 관리자 페이지도 사용하지 않습니다.

1. Cloudflare R2에서 `wedding-guest-snap` 버킷을 만들고 Public Development URL과 Custom Domain은 활성화하지 않습니다.
2. Pages 프로젝트의 Settings > Bindings에서 R2 bucket binding을 추가합니다. 변수 이름은 `GUEST_SNAP_BUCKET`, 대상은 `wedding-guest-snap`으로 지정합니다.
3. Turnstile에서 `wedding-guest-snap` 위젯을 Managed 모드로 만들고 허용 hostname에 `roberthan96.pages.dev`를 등록합니다.
4. Turnstile Site Key는 Pages 빌드 변수 `VITE_TURNSTILE_SITE_KEY`에 일반 텍스트로 등록합니다.
5. Turnstile Secret Key는 Pages 런타임 시크릿 `TURNSTILE_SECRET_KEY`에 암호화하여 등록합니다.
6. Pages 일반 변수 `VITE_GUEST_SNAP_UPLOAD_OPENS_AT`에 `2026-11-15T00:00:00+09:00`을 등록합니다. 이 값은 화면 버튼과 업로드 API의 개방 시각에 함께 적용됩니다.
7. 바인딩과 변수를 등록한 뒤 Production을 다시 배포합니다. 바인딩은 재배포 후 적용됩니다.

사진은 `guest-snap/YYYY-MM-DD/UUID.확장자` 경로로 비공개 R2에 저장됩니다. 확인, 다운로드, 삭제는 Cloudflare R2 대시보드에서 진행합니다. 로컬 Vite 서버에서는 UI만 확인할 수 있고 실제 업로드는 Cloudflare Pages 배포에서 테스트합니다.

## 개인정보 주의

현재 설정에는 신랑·신부 연락처가 포함되어 있습니다. 공개 저장소에 올리면 소스와 빌드 결과에서 누구나 확인할 수 있습니다. 계좌번호와 부모님 연락처를 추가하기 전에는 저장소 공개 범위와 노출 시점을 다시 확인하세요.
