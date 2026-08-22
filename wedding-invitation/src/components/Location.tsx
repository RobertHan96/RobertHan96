import { useState } from 'react'

import { wedding } from '../config/wedding'
import { copyText } from '../lib/clipboard'
import { ImageViewer } from './ImageViewer'
import { SectionHeading } from './SectionHeading'

export function Location() {
  const [copied, setCopied] = useState(false)
  const [viewerOpen, setViewerOpen] = useState(false)
  const { venue } = wedding

  const copyAddress = async () => {
    await copyText(venue.address)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }

  const mapLinks = [
    { label: '네이버지도', href: venue.links.naver },
    { label: '카카오맵', href: venue.links.kakao },
    { label: 'T맵', href: venue.links.tmap },
  ].filter(({ href }) => Boolean(href))
  return (
    <section className="paper-section location-section reveal-section">
      <SectionHeading eyebrow="LOCATION" title="오시는 길" />
      <div className="venue-copy">
        <strong>{venue.name}</strong>
        <span>{venue.hall}</span>
        <p>{venue.address}</p>
        <button type="button" className="outline-button" aria-label="예식장 주소 복사" onClick={copyAddress}>
          {copied ? '복사했어요' : '주소 복사'}
        </button>
      </div>
      <button type="button" className="map-image-button" aria-label="약도 크게 보기" onClick={() => setViewerOpen(true)}>
        <img src={venue.mapImage.src} alt={venue.mapImage.alt} width="800" height="381" loading="lazy" />
      </button>
      {mapLinks.length > 0 ? (
        <div className="map-link-list">
          {mapLinks.map(({ label, href }) => <a key={label} href={href} target="_blank" rel="noreferrer">{label}</a>)}
        </div>
      ) : (
        <p className="pending-note">길찾기 링크 준비 중</p>
      )}
      {viewerOpen && (
        <ImageViewer image={venue.mapImage} onClose={() => setViewerOpen(false)} />
      )}
    </section>
  )
}
