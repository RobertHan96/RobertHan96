import type { WeddingConfig } from '../types/wedding'
import { SectionHeading } from './SectionHeading'

type CoupleProps = { wedding: WeddingConfig }

function phoneHref(phone: string): string {
  return phone.replace(/\D/g, '')
}

type ContactRowProps = {
  side: '신랑' | '신부'
  person: WeddingConfig['groom']
  familyLine: string
}

function ContactRow({ side, person, familyLine }: ContactRowProps) {
  const phone = person.phone ? phoneHref(person.phone) : ''
  return (
    <article className="contact-row">
      <div>
        <p>{familyLine}</p>
        <strong><span>{side}</span> {person.name}</strong>
      </div>
      {phone && (
        <div className="contact-actions">
          <a href={`tel:${phone}`} aria-label={`${side}에게 전화`}>전화</a>
          <a href={`sms:${phone}`} aria-label={`${side}에게 문자`}>문자</a>
        </div>
      )}
    </article>
  )
}

export function Couple({ wedding }: CoupleProps) {
  const { parents } = wedding
  return (
    <section className="paper-section couple-section reveal-section">
      <SectionHeading eyebrow="THE COUPLE" title="두 사람을 소개합니다" />
      <div className="contact-list">
        <ContactRow
          side="신랑"
          person={wedding.groom}
          familyLine={`${parents.groom.father.name} · ${parents.groom.mother.name}의 아들`}
        />
        <ContactRow
          side="신부"
          person={wedding.bride}
          familyLine={`${parents.bride.father.name} · ${parents.bride.mother.name}의 딸`}
        />
      </div>
    </section>
  )
}
