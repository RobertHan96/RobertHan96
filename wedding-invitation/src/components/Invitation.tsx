import { SectionHeading } from './SectionHeading'
import type { WeddingConfig } from '../types/wedding'

type InvitationProps = { invitation: WeddingConfig['invitation'] }

export function Invitation({ invitation }: InvitationProps) {
  return (
    <section className="paper-section invitation-section reveal-section">
      <SectionHeading eyebrow="INVITATION" title={invitation.title} />
      <p className="invitation-copy">
        {invitation.lines.map((line) => (
          <span key={line}>{line}</span>
        ))}
      </p>
    </section>
  )
}
