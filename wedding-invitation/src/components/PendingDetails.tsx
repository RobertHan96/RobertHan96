import { SectionHeading } from './SectionHeading'

function PendingSection({
  eyebrow,
  title,
  message = '안내를 준비하고 있습니다',
  notice,
}: {
  eyebrow: string
  title: string
  message?: string
  notice?: string
}) {
  return (
    <section className="paper-section pending-section reveal-section">
      <SectionHeading eyebrow={eyebrow} title={title} />
      <div className="pending-card" aria-live="polite">
        <span aria-hidden="true">⌁</span>
        <p>{message}</p>
        {notice && <p className="pending-notice">{notice}</p>}
      </div>
    </section>
  )
}

export function PendingDetails() {
  return (
    <>
      <PendingSection
        eyebrow="ACCOUNT"
        title="마음 전하실 곳"
        message="계좌 안내를 준비하고 있습니다"
        notice="축하의 마음만 감사히 받겠습니다. 화환은 정중히 사양하오니 너른 양해 부탁드립니다."
      />
      <PendingSection eyebrow="RSVP" title="참석 여부 전달" message="참석 여부 전달은 추후 오픈됩니다" />
    </>
  )
}
