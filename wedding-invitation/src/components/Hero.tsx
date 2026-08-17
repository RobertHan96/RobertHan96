import type { WeddingConfig } from '../types/wedding'

type HeroProps = { wedding: WeddingConfig }

export function Hero({ wedding }: HeroProps) {
  const heroImage = wedding.gallery.hero

  return (
    <section className="hero-section" aria-labelledby="couple-title">
      <p className="script-kicker">Together, forever</p>
      <figure className="hero-cover">
        <img
          src={heroImage.src}
          alt={heroImage.alt}
          width="1067"
          height="1600"
          loading="eager"
          fetchPriority="high"
          style={{ objectPosition: heroImage.objectPosition }}
        />
      </figure>
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
