import { describe, expect, it, vi } from 'vitest'

import { onRequestGet, onRequestPost } from './photos'

function createEnv(rateCount = 0) {
  const inserted: unknown[][] = []
  const stored: Array<{ key: string; body: unknown }> = []
  const rows = [{
    id: 'approved-photo',
    guest_name: '친구',
    message: '축하해!',
    created_at: '2026-11-15T08:00:00.000Z',
  }]

  return {
    inserted,
    stored,
    env: {
      GUEST_SNAP_ADMIN_PASSWORD: 'secret',
      GUEST_SNAP_BUCKET: {
        put: vi.fn(async (key: string, body: unknown) => { stored.push({ key, body }) }),
        get: vi.fn(),
        delete: vi.fn(),
      },
      GUEST_SNAP_DB: {
        prepare: (query: string) => ({
          bind(...values: unknown[]) {
            if (query.includes('INSERT INTO guest_photos')) inserted.push(values)
            return this
          },
          run: vi.fn(async () => ({})),
          first: vi.fn(async () => query.includes('COUNT(*)') ? { count: rateCount } : null),
          all: vi.fn(async () => ({ results: query.includes("status = 'approved'") ? rows : [] })),
        }),
      },
    },
  }
}

describe('guest snap photo API', () => {
  it('stores a valid upload in R2 and D1', async () => {
    const { env, inserted, stored } = createEnv()
    const photo = {
      name: 'guest.jpg',
      type: 'image/jpeg',
      size: 5,
      stream: () => new ReadableStream(),
    }
    const fields = new Map<string, FormDataEntryValue | typeof photo>([
      ['photo', photo],
      ['guestName', ' 친구 '],
      ['message', ' 축하해! '],
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
    expect(inserted).toHaveLength(1)
    expect(inserted[0]).toContain('친구')
    expect(inserted[0]).toContain('pending')
  })

  it('returns only approved photo metadata with protected media URLs', async () => {
    const { env } = createEnv()
    const response = await onRequestGet({
      request: new Request('https://example.com/api/guest-snap/photos'),
      env,
      params: {},
    })

    expect(response.status).toBe(200)
    await expect(response.json()).resolves.toEqual({
      photos: [{
        id: 'approved-photo',
        guestName: '친구',
        message: '축하해!',
        createdAt: '2026-11-15T08:00:00.000Z',
        mediaUrl: '/api/guest-snap/media/approved-photo',
      }],
    })
  })

  it('limits repeated uploads from the same address', async () => {
    const { env, stored } = createEnv(30)
    const photo = { name: 'guest.jpg', type: 'image/jpeg', size: 5, stream: () => new ReadableStream() }
    const response = await onRequestPost({
      request: {
        url: 'http://localhost/api/guest-snap/photos',
        headers: new Headers({ 'CF-Connecting-IP': '203.0.113.5' }),
        formData: async () => ({ get: (key: string) => key === 'photo' ? photo : null }) as FormData,
      } as Request,
      env,
      params: {},
    })

    expect(response.status).toBe(429)
    expect(stored).toHaveLength(0)
  })
})
