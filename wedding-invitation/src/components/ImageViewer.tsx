import Lightbox from 'yet-another-react-lightbox'
import Zoom from 'yet-another-react-lightbox/plugins/zoom'
import 'yet-another-react-lightbox/styles.css'

import type { GalleryImage } from '../types/wedding'

type ImageViewerProps = {
  images: GalleryImage[]
  index: number
  onClose: () => void
}

export function ImageViewer({ images, index, onClose }: ImageViewerProps) {
  return (
    <Lightbox
      open
      close={onClose}
      index={index}
      slides={images}
      plugins={[Zoom]}
      labels={{
        Lightbox: '사진 크게 보기',
        'Photo gallery': '사진 모음',
      }}
      carousel={{
        finite: images.length <= 1,
        imageFit: 'contain',
        padding: 0,
      }}
      controller={{
        aria: true,
        closeOnBackdropClick: true,
        closeOnPullDown: true,
      }}
      toolbar={{ buttons: [] }}
      render={{
        buttonPrev: () => null,
        buttonNext: () => null,
        buttonClose: () => null,
        buttonZoom: () => null,
        controls: () => (
          <button
            type="button"
            className="image-viewer-close"
            aria-label="사진 닫기"
            onClick={onClose}
          >
            ×
          </button>
        ),
      }}
      styles={{
        container: { backgroundColor: '#fff' },
      }}
      zoom={{
        maxZoomPixelRatio: 2,
        pinchZoomV4: true,
      }}
    />
  )
}
