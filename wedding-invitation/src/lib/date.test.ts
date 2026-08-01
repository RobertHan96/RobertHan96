import { describe, expect, it } from 'vitest'

import { buildCalendarWeeks, formatDday } from './date'

const weddingDate = '2026-11-15T15:50:00+09:00'

describe('formatDday', () => {
  it('formats days before, on, and after the wedding in Korea time', () => {
    expect(formatDday(weddingDate, new Date('2026-11-14T23:59:00+09:00'))).toBe('D-1')
    expect(formatDday(weddingDate, new Date('2026-11-15T09:00:00+09:00'))).toBe('D-DAY')
    expect(formatDday(weddingDate, new Date('2026-11-16T00:01:00+09:00'))).toBe('D+1')
  })
})

describe('buildCalendarWeeks', () => {
  it('builds the Sunday-first grid for November 2026', () => {
    const weeks = buildCalendarWeeks(2026, 10)

    expect(weeks).toHaveLength(5)
    expect(weeks[0]).toEqual([1, 2, 3, 4, 5, 6, 7])
    expect(weeks[2][0]).toBe(15)
    expect(weeks[4]).toEqual([29, 30, null, null, null, null, null])
  })
})
