import { describe, expect, it } from 'vitest'

import { validateGuestImage } from './_shared'

describe('guest snap server rules', () => {
  it('accepts supported images and rejects oversized or unknown files', () => {
    expect(validateGuestImage(new File(['photo'], 'guest.jpg', { type: 'image/jpeg' }))).toEqual({ ok: true, extension: 'jpg' })
    expect(validateGuestImage(new File(['text'], 'guest.txt', { type: 'text/plain' }))).toEqual({ ok: false, error: '지원하지 않는 이미지 형식입니다.' })

    const oversized = new File([new Uint8Array(21 * 1024 * 1024)], 'large.jpg', { type: 'image/jpeg' })
    expect(validateGuestImage(oversized)).toEqual({ ok: false, error: '사진 한 장은 20MB 이하여야 합니다.' })
  })
})
