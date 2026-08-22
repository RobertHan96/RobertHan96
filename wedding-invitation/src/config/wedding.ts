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
      width: 800,
      height: 381,
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
    groom: [{ bank: '신한은행', relation: '신랑', holder: '한영신', number: '110-467-266513' }],
    bride: [
      { bank: '우리은행', relation: '신부', holder: '이다예', number: '1002-353-385470' },
      { bank: '우리은행', relation: '신부 어머니', holder: '오영근', number: '1002-230-989004' },
      { bank: '신한은행', relation: '신부 아버지', holder: '이성환', number: '110-360-443299' },
    ],
  },
  rsvp: { enabled: false, maxCompanions: 5 },
  guestSnap: {
    enabled: true,
    uploadOpensAt: import.meta.env.VITE_GUEST_SNAP_UPLOAD_OPENS_AT ?? '2026-11-15T00:00:00+09:00',
    maxFiles: 10,
    maxFileSizeBytes: 20 * 1024 * 1024,
    turnstileSiteKey: import.meta.env.VITE_TURNSTILE_SITE_KEY ?? '',
  },
  gallery: {
    hero: {
      src: '/images/wedding/photo-14.webp',
      alt: '한영신과 이다예의 웨딩 대표 사진',
      width: 1200,
      height: 1800,
    },
    baby: [
      {
        src: '/images/baby/groom.jpeg',
        alt: '신랑 한영신의 어린 시절',
        width: 1080,
        height: 1080,
        objectPosition: '50% 42%',
      },
      {
        src: '/images/baby/bride.jpeg',
        alt: '신부 이다예의 어린 시절',
        width: 1023,
        height: 1023,
        objectPosition: '50% 42%',
      },
    ],
    wedding: [
      {
        src: '/images/wedding/photo-08.webp',
        alt: '아치 앞에 나란히 선 한영신과 이다예',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-09.webp',
        alt: '장난스럽게 웃는 한영신과 이다예',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-10.webp',
        alt: '꽃으로 둘러싸인 소파에 앉은 이다예',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-14.webp',
        alt: '꽃 장식 앞에 나란히 앉은 한영신과 이다예',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-15.webp',
        alt: '슬림 웨딩드레스의 뒷모습을 보이는 이다예',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-11.webp',
        alt: '꽃으로 둘러싸인 소파에 앉은 한영신',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-12.webp',
        alt: '창가에서 웨딩드레스를 펼친 이다예',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-13.webp',
        alt: '베일 너머 마주 보는 한영신과 이다예',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-04.webp',
        alt: '검은 의상을 입고 나란히 선 한영신과 이다예',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-05.webp',
        alt: '벽돌 담장 앞에 마주 선 한영신과 이다예',
        width: 1800,
        height: 1200,
      },
      {
        src: '/images/wedding/photo-07.webp',
        alt: '벽돌 담장 앞에서 함께 웃는 한영신과 이다예',
        width: 1350,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-06.webp',
        alt: '손을 잡고 걷는 한영신과 이다예의 흑백 사진',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-01.webp',
        alt: '부케를 든 웨딩드레스 차림의 이다예',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-02.webp',
        alt: '부케를 든 턱시도 차림의 한영신',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-03.webp',
        alt: '정원에서 함께 앉아 있는 한영신과 이다예',
        width: 1800,
        height: 1200,
      },
      {
        src: '/images/wedding/photo-16.webp',
        alt: '붉은 드레스를 입고 장난스럽게 포즈를 취한 한영신과 이다예',
        width: 1350,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-17.webp',
        alt: '정원에서 붉은 드레스를 입고 마주 선 한영신과 이다예',
        width: 1200,
        height: 1800,
      },
      {
        src: '/images/wedding/photo-18.webp',
        alt: '베일 아래 함께 웃는 한영신과 이다예',
        width: 1200,
        height: 1800,
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
