import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

import type { GalleryImage } from '../types/wedding'

type ImageViewerProps = {
  images: GalleryImage[]
  index: number
  onClose: () => void
  onMove: (index: number) => void
}

export function ImageViewer({ images, index, onClose, onMove }: ImageViewerProps) {
  const touchStart = useRef<{ x: number; y: number } | null>(null)
  const multiTouchGesture = useRef(false)
  const current = images[index]
  const move = (offset: number) => onMove((index + offset + images.length) % images.length)

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key === 'ArrowLeft') move(-1)
      if (event.key === 'ArrowRight') move(1)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKeyDown)
    }
  })

  return createPortal(
    <div
      className={`image-viewer${images.length === 1 ? ' image-viewer-single' : ''}`}
      role="dialog"
      aria-modal="true"
      aria-label="사진 크게 보기"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
      onTouchStart={(event) => {
        if (event.touches.length !== 1) {
          multiTouchGesture.current = true
          touchStart.current = null
          return
        }
        if (multiTouchGesture.current) return
        const touch = event.touches[0]
        touchStart.current = { x: touch.clientX, y: touch.clientY }
      }}
      onTouchMove={(event) => {
        if (event.touches.length > 1) {
          multiTouchGesture.current = true
          touchStart.current = null
        }
      }}
      onTouchEnd={(event) => {
        if (multiTouchGesture.current) {
          if (event.touches.length === 0) multiTouchGesture.current = false
          touchStart.current = null
          return
        }
        if (touchStart.current === null) return
        const touch = event.changedTouches[0]
        const distanceX = touch.clientX - touchStart.current.x
        const distanceY = touch.clientY - touchStart.current.y
        if (Math.abs(distanceX) > 45 && Math.abs(distanceX) > Math.abs(distanceY) * 1.2) {
          move(distanceX > 0 ? -1 : 1)
        }
        touchStart.current = null
      }}
      onTouchCancel={() => {
        multiTouchGesture.current = false
        touchStart.current = null
      }}
    >
      <button type="button" className="viewer-close" aria-label="사진 닫기" onClick={onClose}>×</button>
      {images.length > 1 && (
        <button type="button" className="viewer-nav viewer-prev" aria-label="이전 사진" onClick={() => move(-1)}>‹</button>
      )}
      <figure>
        <img src={current.src} alt={`확대: ${current.alt}`} style={{ objectPosition: current.objectPosition }} />
        <figcaption>{index + 1} / {images.length}</figcaption>
      </figure>
      {images.length > 1 && (
        <button type="button" className="viewer-nav viewer-next" aria-label="다음 사진" onClick={() => move(1)}>›</button>
      )}
    </div>,
    document.body,
  )
}
