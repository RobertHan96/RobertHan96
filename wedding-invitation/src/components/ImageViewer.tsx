import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

import type { GalleryImage } from '../types/wedding'

type ImageViewerProps = {
  image: GalleryImage
  onClose: () => void
  onPrevious?: () => void
  onNext?: () => void
}

export function ImageViewer({ image, onClose, onPrevious, onNext }: ImageViewerProps) {
  const touchStart = useRef<{ x: number; y: number } | null>(null)
  const multiTouchGesture = useRef(false)

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key === 'ArrowLeft') onPrevious?.()
      if (event.key === 'ArrowRight') onNext?.()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [onClose, onNext, onPrevious])

  return createPortal(
    <div
      className="image-viewer"
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
          if (distanceX > 0) onPrevious?.()
          else onNext?.()
        }
        touchStart.current = null
      }}
      onTouchCancel={() => {
        multiTouchGesture.current = false
        touchStart.current = null
      }}
    >
      <button type="button" className="viewer-close" aria-label="사진 닫기" onClick={onClose}>×</button>
      <figure>
        <img src={image.src} alt={`확대: ${image.alt}`} style={{ objectPosition: image.objectPosition }} />
      </figure>
    </div>,
    document.body,
  )
}
