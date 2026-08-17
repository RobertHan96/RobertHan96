import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { GuestSnapAdmin } from './GuestSnapAdmin'

afterEach(() => vi.unstubAllGlobals())

describe('GuestSnapAdmin', () => {
  it('logs in and shows photos waiting for review', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        photos: [{
          id: 'photo-1',
          guestName: '친구',
          message: '축하해!',
          status: 'pending',
          createdAt: '2026-11-15T08:00:00Z',
          sizeBytes: 1024,
          mediaUrl: '/api/guest-snap/media/photo-1?admin=1',
        }],
      }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<GuestSnapAdmin />)

    await user.type(screen.getByLabelText('관리자 비밀번호'), 'secret')
    await user.click(screen.getByRole('button', { name: '관리자 로그인' }))

    await waitFor(() => expect(screen.getByAltText('친구님이 올린 사진')).toBeInTheDocument())
    expect(screen.getByText('축하해!')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '사진 승인' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '사진 제외' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '사진 삭제' })).toBeInTheDocument()
  })
})
