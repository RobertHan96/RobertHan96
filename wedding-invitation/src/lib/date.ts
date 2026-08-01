const DAY_IN_MS = 24 * 60 * 60 * 1000

function calendarDayInKorea(date: Date): number {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]))
  return Date.UTC(Number(values.year), Number(values.month) - 1, Number(values.day))
}

export function formatDday(weddingDate: string, now = new Date()): string {
  const difference = Math.round(
    (calendarDayInKorea(new Date(weddingDate)) - calendarDayInKorea(now)) / DAY_IN_MS,
  )
  if (difference === 0) return 'D-DAY'
  return difference > 0 ? `D-${difference}` : `D+${Math.abs(difference)}`
}

export function buildCalendarWeeks(year: number, monthIndex: number): Array<Array<number | null>> {
  const firstWeekday = new Date(Date.UTC(year, monthIndex, 1)).getUTCDay()
  const lastDate = new Date(Date.UTC(year, monthIndex + 1, 0)).getUTCDate()
  const cells: Array<number | null> = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: lastDate }, (_, index) => index + 1),
  ]
  while (cells.length % 7 !== 0) cells.push(null)
  return Array.from({ length: cells.length / 7 }, (_, index) => cells.slice(index * 7, index * 7 + 7))
}
