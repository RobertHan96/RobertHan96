import { wedding } from '../config/wedding'
import { SectionHeading } from './SectionHeading'

const sections = [
  { key: 'subway', label: '지하철 이용 시', mark: '01' },
  { key: 'bus', label: '버스 이용 시', mark: '02' },
  { key: 'car', label: '자가용 이용 시', mark: '03' },
  { key: 'parking', label: '주차 안내', mark: '04' },
] as const

export function Transportation() {
  return (
    <section className="paper-section transportation-section reveal-section">
      <SectionHeading eyebrow="TRANSPORTATION" title="교통 안내" />
      <div className="transportation-list">
        {sections.map(({ key, label, mark }) => (
          <article className="transportation-card" key={key}>
            <span className="transportation-mark" aria-hidden="true">{mark}</span>
            <div>
              <h3>{label}</h3>
              {wedding.transportation[key].map((line) => (
                <p key={line} className={line.startsWith('*') ? 'transportation-note' : undefined}>
                  {line.replace(/^\*/, '')}
                </p>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
