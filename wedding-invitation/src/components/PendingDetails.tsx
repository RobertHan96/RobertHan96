import { SectionHeading } from './SectionHeading'

function PendingSection({ eyebrow, title, message = '안내를 준비하고 있습니다' }: { eyebrow: string; title: string; message?: string }) {
  return (
    <section className="paper-section pending-section reveal-section">
      <SectionHeading eyebrow={eyebrow} title={title} />
      <div className="pending-card" aria-live="polite">
        <span aria-hidden="true">⌁</span>
        <p>{message}</p>
      </div>
    </section>
  )
}

export function PendingDetails() {
  return (
    <>
      <PendingSection eyebrow="TRANSPORTATION" title="교통 안내" />
      <PendingSection eyebrow="ACCOUNT" title="마음 전하실 곳" />
      <PendingSection eyebrow="RSVP" title="참석 여부 전달" message="참석 여부 전달은 추후 오픈됩니다" />
    </>
  )
}
