export type Person = {
  name: string
  phone?: string
}

export type GalleryImage = {
  src: string
  alt: string
  objectPosition?: string
  layout?: 'wide' | 'half'
}

export type Account = {
  bank: string
  relation: string
  holder: string
  number: string
}

export type GuestSnapConfig = {
  enabled: boolean
  uploadOpensAt: string
  maxFiles: number
  maxFileSizeBytes: number
  turnstileSiteKey: string
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
  accounts: { groom: Account[]; bride: Account[] }
  rsvp: { enabled: boolean; maxCompanions: number }
  guestSnap: GuestSnapConfig
  gallery: { hero: GalleryImage; baby: GalleryImage[]; wedding: GalleryImage[] }
  share: { title: string; description: string; ogImage: string; url: string; kakaoJavascriptKey: string }
}
