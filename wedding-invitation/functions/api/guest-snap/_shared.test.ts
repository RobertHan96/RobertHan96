import { describe, expect, it } from 'vitest'

import { createAdminSession, validateGuestImage, verifyAdminSession } from './_shared'

describe('guest snap server rules', () => {
  it('accepts supported images and rejects oversized or unknown files', () => {
    expect(validateGuestImage(new File(['photo'], 'guest.jpg', { type: 'image/jpeg' }))).toEqual({ ok: true, extension: 'jpg' })
    expect(validateGuestImage(new File(['text'], 'guest.txt', { type: 'text/plain' }))).toEqual({ ok: false, error: '지원하지 않는 이미지 형식입니다.' })

    const oversized = new File([new Uint8Array(21 * 1024 * 1024)], 'large.jpg', { type: 'image/jpeg' })
    expect(validateGuestImage(oversized)).toEqual({ ok: false, error: '사진 한 장은 20MB 이하여야 합니다.' })
  })

  it('creates an expiring signed administrator session', async () => {
    const now = new Date('2026-08-17T10:00:00Z')
    const token = await createAdminSession('secret', now)

    expect(await verifyAdminSession(token, 'secret', new Date('2026-08-17T11:00:00Z'))).toBe(true)
    expect(await verifyAdminSession(token, 'wrong-secret', new Date('2026-08-17T11:00:00Z'))).toBe(false)
    expect(await verifyAdminSession(token, 'secret', new Date('2026-08-18T11:00:01Z'))).toBe(false)
  })
})
