import { useEffect } from 'react'
import { createPortal } from 'react-dom'

import type { GalleryImage } from '../types/wedding'

type ImageViewerProps = {
  image: GalleryImage
  onClose: () => void
}

export function ImageViewer({ image, onClose }: ImageViewerProps) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [onClose])

  return createPortal(
    <div
      className="image-viewer"
      role="dialog"
      aria-modal="true"
      aria-label="사진 크게 보기"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <button type="button" className="viewer-close" aria-label="사진 닫기" onClick={onClose}>×</button>
      <figure>
        <img src={image.src} alt={`확대: ${image.alt}`} style={{ objectPosition: image.objectPosition }} />
      </figure>
    </div>,
    document.body,
  )
}
