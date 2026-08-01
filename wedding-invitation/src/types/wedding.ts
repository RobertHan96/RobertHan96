export type Person = {
  name: string
  phone?: string
}

export type GalleryImage = {
  src: string
  alt: string
  objectPosition?: string
}

export type WeddingConfig = {
  groom: Person
  bride: Person
  parents: {
    groom: { father: Person; mother: Person }
    bride: { father: Person; mother: Person }
  }
  invitation: { title: string; lines: string[] }
  date: {
    iso: string
    display: string
    time: string
    year: number
    monthIndex: number
    day: number
  }
  venue: {
    name: string
    hall: string
    address: string
    mapImage: GalleryImage
    links: { naver: string; kakao: string; tmap: string }
  }
  transportation: { subway: string[]; bus: string[]; car: string[]; parking: string[] }
  accounts: { groom: unknown[]; bride: unknown[] }
  rsvp: { enabled: boolean; maxCompanions: number }
  gallery: { baby: GalleryImage[]; wedding: GalleryImage[]; comingSoon: boolean }
  share: { title: string; description: string; ogImage: string; kakaoJavascriptKey: string }
}
