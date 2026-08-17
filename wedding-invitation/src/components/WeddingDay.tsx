import { wedding } from '../config/wedding'
import { buildCalendarWeeks, formatDday } from '../lib/date'

const weekdays = ['일', '월', '화', '수', '목', '금', '토']

export function WeddingDay() {
  const { date } = wedding
  const weeks = buildCalendarWeeks(date.year, date.monthIndex)
  return (
    <section className="paper-section wedding-day-section reveal-section">
      <p className="ceremony-summary ceremony-summary-top">
        <time dateTime={date.iso}>{date.display}</time>
        <span>{date.time}</span>
      </p>
      <div className="dday-pill">{formatDday(date.iso)}</div>
      <p className="calendar-title">NOVEMBER 2026</p>
      <div className="calendar" role="grid" aria-label="2026년 11월 예식 달력">
        <div className="calendar-row calendar-weekdays" role="row">
          {weekdays.map((weekday) => <span role="columnheader" key={weekday}>{weekday}</span>)}
        </div>
        {weeks.map((week, weekIndex) => (
          <div className="calendar-row" role="row" key={weekIndex}>
            {week.map((day, dayIndex) => (
              <span
                role="gridcell"
                key={`${weekIndex}-${dayIndex}`}
                aria-current={day === date.day ? 'date' : undefined}
                className={day === date.day ? 'wedding-date' : undefined}
              >
                {day}
              </span>
            ))}
          </div>
        ))}
      </div>
    </section>
  )
}
