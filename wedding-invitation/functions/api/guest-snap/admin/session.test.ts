import { describe, expect, it } from 'vitest'

import { onRequestPost } from './session'

describe('guest snap admin session API', () => {
  it('sets an HTTP-only cookie only for the configured password', async () => {
    const env = { GUEST_SNAP_ADMIN_PASSWORD: 'correct-password' }
    const response = await onRequestPost({
      request: new Request('https://example.com/api/guest-snap/admin/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: 'correct-password' }),
      }),
      env,
      params: {},
    })

    expect(response.status).toBe(200)
    expect(response.headers.get('Set-Cookie')).toContain('guest_snap_admin=')
    expect(response.headers.get('Set-Cookie')).toContain('HttpOnly')
    expect(response.headers.get('Set-Cookie')).toContain('SameSite=Strict')
  })
})
