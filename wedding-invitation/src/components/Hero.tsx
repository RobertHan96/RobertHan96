import type { WeddingConfig } from '../types/wedding'

type HeroProps = { wedding: WeddingConfig }

function BotanicalSprig({ side }: { side: 'left' | 'right' }) {
  return (
    <svg className={`botanical-sprig botanical-sprig-${side}`} viewBox="0 0 90 230" aria-hidden="true">
      <path d="M72 8C42 67 31 133 18 222M56 48C34 39 18 45 7 65c23 7 39 0 49-17Zm-15 55c22-12 39-9 48 9-21 13-38 10-48-9Zm-13 56c-18-8-32-3-41 13 18 9 32 4 41-13Z" />
    </svg>
  )
}

export function Hero({ wedding }: HeroProps) {
  const [groomImage, brideImage] = wedding.gallery.baby
  return (
    <section className="hero-section" aria-labelledby="couple-title">
      <BotanicalSprig side="left" />
      <BotanicalSprig side="right" />
      <p className="script-kicker">Together, forever</p>
      <div className="hero-portraits">
        {[groomImage, brideImage].map((image) => (
          <figure className="hero-portrait" key={image.src}>
            <img
              src={image.src}
              alt={image.alt}
              width="540"
              height="680"
              loading="eager"
              style={{ objectPosition: image.objectPosition }}
            />
          </figure>
        ))}
      </div>
      <h1 id="couple-title">
        <span>{wedding.groom.name}</span> <small>그리고</small> <span>{wedding.bride.name}</span>
      </h1>
      <div className="hero-ceremony">
        <time dateTime={wedding.date.iso}>{wedding.date.display}</time>
        <span>{wedding.date.time}</span>
        <strong>{wedding.venue.name}</strong>
        <span>{wedding.venue.hall}</span>
      </div>
    </section>
  )
}
