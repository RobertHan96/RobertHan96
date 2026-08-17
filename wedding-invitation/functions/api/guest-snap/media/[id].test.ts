import { describe, expect, it, vi } from 'vitest'

import { onRequestGet } from './[id]'

function contextFor(status: 'pending' | 'approved') {
  const record = {
    id: 'photo-1',
    object_key: 'guest-snap/photo-1.jpg',
    content_type: 'image/jpeg',
    guest_name: null,
    message: null,
    status,
    created_at: '2026-11-15T08:00:00Z',
    size_bytes: 5,
  }
  return {
    request: new Request('https://example.com/api/guest-snap/media/photo-1'),
    params: { id: 'photo-1' },
    env: {
      GUEST_SNAP_ADMIN_PASSWORD: 'secret',
      GUEST_SNAP_DB: {
        prepare: () => ({
          bind() { return this },
          first: vi.fn(async () => record),
          all: vi.fn(),
          run: vi.fn(),
        }),
      },
      GUEST_SNAP_BUCKET: {
        put: vi.fn(),
        delete: vi.fn(),
        get: vi.fn(async () => ({
          body: new ReadableStream({ start(controller) { controller.enqueue(new TextEncoder().encode('photo')); controller.close() } }),
          httpEtag: '"etag"',
          writeHttpMetadata: (headers: Headers) => headers.set('Content-Type', 'image/jpeg'),
        })),
      },
    },
  }
}

describe('guest snap media API', () => {
  it('serves approved photos from the private R2 bucket', async () => {
    const response = await onRequestGet(contextFor('approved'))

    expect(response.status).toBe(200)
    expect(response.headers.get('Content-Type')).toBe('image/jpeg')
    await expect(response.text()).resolves.toBe('photo')
  })

  it('does not expose pending photos without administrator authentication', async () => {
    const response = await onRequestGet(contextFor('pending'))

    expect(response.status).toBe(404)
  })
})
