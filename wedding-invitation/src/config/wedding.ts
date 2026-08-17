import type { WeddingConfig } from '../types/wedding'

export const wedding: WeddingConfig = {
  groom: { name: '한영신', phone: '010-2234-5619' },
  bride: { name: '이다예', phone: '010-7168-5132' },
  parents: {
    groom: {
      father: { name: '한성용' },
      mother: { name: '황진심' },
    },
    bride: {
      father: { name: '이성환' },
      mother: { name: '오영근' },
    },
  },
  invitation: {
    title: '서로의 오늘이 되어',
    lines: [
      '각자의 시간 속에서 자라온 두 사람이',
      '이제 같은 계절을 바라보며',
      '한 길을 걸어가려 합니다.',
      '저희의 새로운 시작에 함께하시어',
      '따뜻한 축복을 더해주시면 감사하겠습니다.',
    ],
  },
  date: {
    iso: '2026-11-15T15:50:00+09:00',
    display: '2026. 11. 15',
    time: '오후 3시 50분',
    year: 2026,
    monthIndex: 10,
    day: 15,
  },
  venue: {
    name: '더컨벤션 잠실',
    hall: '3층 비스타홀',
    address: '서울 송파구 올림픽로 319 3층',
    mapImage: {
      src: '/images/location/map.jpeg',
      alt: '더컨벤션 잠실 오시는 길 약도',
    },
    links: {
      naver: 'https://naver.me/F1rxJcrX',
      kakao: 'https://place.map.kakao.com/17651361',
      tmap: '',
    },
  },
  transportation: {
    subway: [
      '2호선 잠실역 8번 출구 약 300m',
      '8호선 잠실역 9번 출구 약 30m',
    ],
    bus: [
      '간선 302, 310, 341, 360',
      '지선 2311, 3411',
      '광역·직행 1000, 1100, 1700',
      '*그 외 다양한 노선 이용 가능',
    ],
    car: [
      '신주소 송파구 올림픽로 319',
      '구주소 송파구 신천동 11-7',
    ],
    parking: ['교통회관 지상·지하 주차장 이용'],
  },
  accounts: {
    groom: [{ bank: '신한은행', holder: '한영신', number: '110-467-266513' }],
    bride: [{ bank: '우리은행', holder: '이다예', number: '1002-353-385470' }],
  },
  rsvp: { enabled: false, maxCompanions: 5 },
  guestSnap: {
    enabled: true,
    uploadOpensAt: '2026-11-15T00:00:00+09:00',
    maxFiles: 10,
    maxFileSizeBytes: 20 * 1024 * 1024,
    turnstileSiteKey: import.meta.env.VITE_TURNSTILE_SITE_KEY ?? '',
  },
  gallery: {
    hero: {
      src: '/images/wedding/cover.webp',
      alt: '한영신과 이다예의 웨딩 대표 사진',
    },
    baby: [
      {
        src: '/images/baby/groom.jpeg',
        alt: '신랑 한영신의 어린 시절',
        objectPosition: '50% 42%',
      },
      {
        src: '/images/baby/bride.jpeg',
        alt: '신부 이다예의 어린 시절',
        objectPosition: '50% 42%',
      },
    ],
    wedding: [
      {
        src: '/images/wedding/opening.webp',
        alt: '정원에서 함께 웃는 한영신과 이다예',
        layout: 'wide',
      },
      {
        src: '/images/wedding/bride.webp',
        alt: '웨딩드레스를 입은 이다예',
        layout: 'half',
      },
      {
        src: '/images/wedding/groom.webp',
        alt: '부케를 든 한영신',
        layout: 'half',
      },
      {
        src: '/images/wedding/laugh.webp',
        alt: '함께 웃는 한영신과 이다예',
      },
      {
        src: '/images/wedding/veil.webp',
        alt: '베일 아래 마주 보는 한영신과 이다예',
      },
      {
        src: '/images/wedding/street.webp',
        alt: '벽돌길에서 마주 선 한영신과 이다예',
        layout: 'wide',
      },
      {
        src: '/images/wedding/red-dance.webp',
        alt: '정원에서 춤추는 한영신과 이다예',
      },
      {
        src: '/images/wedding/red-laugh.webp',
        alt: '베일 아래 함께 웃는 한영신과 이다예',
      },
    ],
  },
  share: {
    title: '한영신 ♥ 이다예, 결혼합니다',
    description: '2026년 11월 15일 오후 3시 50분 · 더컨벤션 잠실',
    ogImage: 'https://roberthan96.pages.dev/images/wedding/share.jpg',
    url: 'https://roberthan96.pages.dev/',
    kakaoJavascriptKey: import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY ?? '',
  },
}
