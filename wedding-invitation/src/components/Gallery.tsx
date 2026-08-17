import { useState } from 'react'

import type { WeddingConfig } from '../types/wedding'
import { ImageViewer } from './ImageViewer'
import { SectionHeading } from './SectionHeading'

type GalleryProps = { gallery: WeddingConfig['gallery'] }

export function Gallery({ gallery }: GalleryProps) {
  const images = [...gallery.baby, ...gallery.wedding]
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  return (
    <>
      <section className="paper-section gallery-section reveal-section">
        <SectionHeading eyebrow="OUR STORY" title="우리의 어린 날" />
        <div className="polaroid-gallery">
          {gallery.baby.map((image, index) => (
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
      </section>

      <section className="paper-section wedding-gallery-section reveal-section">
        <SectionHeading eyebrow="WEDDING GALLERY" title="오늘의 우리" />
        <div className="wedding-photo-grid">
          {gallery.wedding.map((image, index) => (
            <button
              type="button"
              className="wedding-thumbnail"
              key={image.src}
              aria-label={`${image.alt} 크게 보기`}
              onClick={() => setSelectedIndex(gallery.baby.length + index)}
            >
              <img
                src={image.src}
                alt={image.alt}
                width="800"
                height="800"
                loading="lazy"
              />
            </button>
          ))}
        </div>
      </section>

      {selectedIndex !== null && (
        <ImageViewer
          images={images}
          index={selectedIndex}
          onMove={setSelectedIndex}
          onClose={() => setSelectedIndex(null)}
        />
      )}
    </>
  )
}
