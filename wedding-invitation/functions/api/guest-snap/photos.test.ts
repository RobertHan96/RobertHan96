import { afterEach, describe, expect, it, vi } from 'vitest'

import { onRequestPost } from './photos'

function createEnv() {
  const stored: Array<{ key: string; body: unknown; options: Record<string, unknown> }> = []

  return {
    stored,
    env: {
      GUEST_SNAP_BUCKET: {
        put: vi.fn(async (key: string, body: unknown, options: Record<string, unknown>) => {
          stored.push({ key, body, options })
        }),
      },
    },
  }
}

describe('guest snap photo API', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('uses the shared build variable to decide when production uploads open', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-11-16T00:00:00+09:00'))
    const { env, stored } = createEnv()

    const response = await onRequestPost({
      request: new Request('https://roberthan96.pages.dev/api/guest-snap/photos', { method: 'POST' }),
      env: {
        ...env,
        VITE_GUEST_SNAP_UPLOAD_OPENS_AT: '2026-11-17T00:00:00+09:00',
      },
      params: {},
    })

    expect(response.status).toBe(403)
    expect(stored).toHaveLength(0)
  })

  it('stores a valid upload only in private R2', async () => {
    const { env, stored } = createEnv()
    const photo = {
      name: 'guest.jpg',
      type: 'image/jpeg',
      size: 5,
      stream: () => new ReadableStream(),
    }
    const fields = new Map<string, FormDataEntryValue | typeof photo>([
      ['photo', photo],
    ])

    const response = await onRequestPost({
      request: {
        url: 'http://localhost/api/guest-snap/photos',
        headers: new Headers(),
        formData: async () => ({ get: (key: string) => fields.get(key) ?? null }) as FormData,
      } as Request,
      env,
      params: {},
    })

    expect(response.status).toBe(201)
    expect(stored).toHaveLength(1)
    expect(stored[0].key).toMatch(/^guest-snap\/2026-/)
    expect(stored[0].options).toEqual(expect.objectContaining({
      httpMetadata: { contentType: 'image/jpeg', cacheControl: 'private, max-age=0' },
      customMetadata: expect.objectContaining({ photoId: expect.any(String), uploadedAt: expect.any(String) }),
    }))
    await expect(response.json()).resolves.toEqual({ ok: true, id: expect.any(String) })
  })
})
