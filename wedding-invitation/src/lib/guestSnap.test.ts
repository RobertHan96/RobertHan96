import { describe, expect, it } from 'vitest'

import { isGuestSnapOpen, validateGuestFiles } from './guestSnap'

describe('guest snap client rules', () => {
  it('opens uploads on the configured date and during local preview', () => {
    const opensAt = '2026-11-15T00:00:00+09:00'

    expect(isGuestSnapOpen(true, opensAt, new Date('2026-11-14T14:59:59Z'), false)).toBe(false)
    expect(isGuestSnapOpen(true, opensAt, new Date('2026-11-14T15:00:00Z'), false)).toBe(true)
    expect(isGuestSnapOpen(true, opensAt, new Date('2026-08-17T00:00:00Z'), true)).toBe(true)
  })

  it('limits a selection to ten supported images of at most 20 MB each', () => {
    const valid = new File(['photo'], 'moment.jpg', { type: 'image/jpeg' })
    const unsupported = new File(['video'], 'moment.mp4', { type: 'video/mp4' })

    expect(validateGuestFiles([valid], 10, 20 * 1024 * 1024)).toEqual({ valid: [valid], errors: [] })
    expect(validateGuestFiles([unsupported], 10, 20 * 1024 * 1024).errors[0]).toContain('지원하지 않는 형식')
    expect(validateGuestFiles(Array.from({ length: 11 }, () => valid), 10, 20 * 1024 * 1024).errors[0]).toContain('최대 10장')
  })
})
