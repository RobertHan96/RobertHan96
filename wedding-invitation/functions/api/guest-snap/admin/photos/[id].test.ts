import { describe, expect, it, vi } from 'vitest'

import { createAdminSession } from '../../_shared'
import { onRequestDelete, onRequestPatch } from './[id]'

async function createContext(method: 'PATCH' | 'DELETE') {
  const password = 'secret'
  const token = await createAdminSession(password)
  const deleted = vi.fn()
  const runs: string[] = []
  const record = {
    id: 'photo-1',
    object_key: 'guest-snap/photo-1.jpg',
    content_type: 'image/jpeg',
    size_bytes: 5,
    guest_name: null,
    message: null,
    status: 'pending',
    created_at: '2026-11-15T08:00:00Z',
  }
  return {
    deleted,
    runs,
    context: {
      request: new Request('https://example.com/api/guest-snap/admin/photos/photo-1', {
        method,
        headers: { Cookie: `guest_snap_admin=${token}`, 'Content-Type': 'application/json' },
        body: method === 'PATCH' ? JSON.stringify({ status: 'approved' }) : undefined,
      }),
      params: { id: 'photo-1' },
      env: {
        GUEST_SNAP_ADMIN_PASSWORD: password,
        GUEST_SNAP_BUCKET: { put: vi.fn(), get: vi.fn(), delete: deleted },
        GUEST_SNAP_DB: {
          prepare: (query: string) => ({
            bind() { return this },
            first: vi.fn(async () => record),
            all: vi.fn(),
            run: vi.fn(async () => { runs.push(query); return {} }),
          }),
        },
      },
    },
  }
}

describe('guest snap admin photo API', () => {
  it('approves a pending photo', async () => {
    const { context, runs } = await createContext('PATCH')
    const response = await onRequestPatch(context)

    expect(response.status).toBe(200)
    expect(runs.some((query) => query.includes('UPDATE guest_photos'))).toBe(true)
  })

  it('deletes both metadata and the R2 object', async () => {
    const { context, deleted, runs } = await createContext('DELETE')
    const response = await onRequestDelete(context)

    expect(response.status).toBe(200)
    expect(deleted).toHaveBeenCalledWith('guest-snap/photo-1.jpg')
    expect(runs.some((query) => query.includes('DELETE FROM guest_photos'))).toBe(true)
  })
})
