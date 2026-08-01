import { useState } from 'react'

import type { WeddingConfig } from '../types/wedding'
import { ImageViewer } from './ImageViewer'
import { SectionHeading } from './SectionHeading'

type GalleryProps = { gallery: WeddingConfig['gallery'] }

export function Gallery({ gallery }: GalleryProps) {
  const images = [...gallery.baby, ...gallery.wedding]
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  return (
    <section className="paper-section gallery-section reveal-section">
      <SectionHeading eyebrow="OUR STORY" title="우리의 어린 날" />
      <div className="polaroid-gallery">
        {images.map((image, index) => (
          <button
            type="button"
            className="polaroid-card"
            key={image.src}
            aria-label={`${image.alt} 크게 보기`}
            onClick={() => setSelectedIndex(index)}
          >
            <img
              src={image.src}
              alt={image.alt}
              width="540"
              height="540"
              loading="lazy"
              style={{ objectPosition: image.objectPosition }}
            />
          </button>
        ))}
      </div>
      <p className="story-copy">
        <span>아이들은 자라서</span>
        <span>서로의 가장 좋은 친구가 되었습니다.</span>
      </p>
      {gallery.comingSoon && (
        <div className="coming-soon">
          <strong>TO BE CONTINUED...</strong>
          <span>Wedding photos coming soon</span>
        </div>
      )}
      {selectedIndex !== null && (
        <ImageViewer
          images={images}
          index={selectedIndex}
          onMove={setSelectedIndex}
          onClose={() => setSelectedIndex(null)}
        />
      )}
    </section>
  )
}
