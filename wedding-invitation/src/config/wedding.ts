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
  accounts: { groom: [], bride: [] },
  rsvp: { enabled: false, maxCompanions: 5 },
  gallery: {
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
    wedding: [],
    comingSoon: true,
  },
  share: {
    title: '한영신 ♥ 이다예, 결혼합니다',
    description: '2026년 11월 15일 더컨벤션 잠실',
    ogImage: '/images/location/map.jpeg',
    kakaoJavascriptKey: '',
  },
}
