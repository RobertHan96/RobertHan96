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
        <span>{wedding.bride.name}</span> <small>그리고</small> <span>{wedding.groom.name}</span>
      </h1>
      <div className="hero-ceremony">
        <time dateTime={wedding.date.iso}>{wedding.date.display}</time>
        <span>{wedding.date.time}</span>
        <strong>{wedding.venue.name}</strong>
        <span>{wedding.venue.hall}</span>
      </div>
      <div className="hero-family">
        <p>
          <span>{wedding.parents.bride.father.name} · {wedding.parents.bride.mother.name}의 딸</span>
          <strong>신부 {wedding.bride.name},</strong>
        </p>
        <p>
          <span>{wedding.parents.groom.father.name} · {wedding.parents.groom.mother.name}의 아들</span>
          <strong>신랑 {wedding.groom.name}</strong>
        </p>
      </div>
    </section>
  )
}
