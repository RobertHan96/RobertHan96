import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { GuestSnap } from './GuestSnap'

afterEach(() => vi.unstubAllGlobals())

const config = {
  enabled: true,
  uploadOpensAt: '2026-11-15T00:00:00+09:00',
  maxFiles: 10,
  maxFileSizeBytes: 20 * 1024 * 1024,
  turnstileSiteKey: '',
}

describe('GuestSnap', () => {
  it('shows a wedding-day notice before uploads open', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ photos: [] }), { status: 200 })))
    render(<GuestSnap config={config} now={new Date('2026-08-17T00:00:00Z')} />)

    expect(screen.getByRole('heading', { name: '게스트 스냅' })).toBeInTheDocument()
    expect(screen.getByText('예식 당일부터 사진을 남길 수 있습니다.')).toBeInTheDocument()
    expect(screen.queryByLabelText('게스트 사진 선택')).not.toBeInTheDocument()
  })

  it('uploads selected photos one at a time after consent', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ photos: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, id: 'photo-1', status: 'pending' }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ photos: [] }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<GuestSnap config={config} forceOpen />)

    const photo = new File(['photo'], '친구사진.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText('게스트 사진 선택'), photo)
    await user.type(screen.getByLabelText('이름 (선택)'), '친구')
    await user.type(screen.getByLabelText('메시지 (선택)'), '결혼 축하해!')
    await user.click(screen.getByRole('checkbox', { name: /사진 제공과 신랑·신부의 보관 및 공개에 동의합니다/ }))
    await user.click(screen.getByRole('button', { name: '사진 1장 보내기' }))

    await waitFor(() => expect(screen.getByText('사진 1장을 잘 받았습니다.')).toBeInTheDocument())
    const uploadRequest = fetchMock.mock.calls.find((call) => call[1]?.method === 'POST')
    expect(uploadRequest).toBeDefined()
    expect(uploadRequest![0]).toBe('/api/guest-snap/photos')
    const uploadOptions = uploadRequest![1] as RequestInit
    expect((uploadOptions.body as FormData).get('guestName')).toBe('친구')
  })

  it('renders Turnstile explicitly when a site key is configured', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ photos: [] }), { status: 200 })))
    const renderTurnstile = vi.fn(() => 'widget-1')
    window.turnstile = { render: renderTurnstile, reset: vi.fn() }

    render(<GuestSnap config={{ ...config, turnstileSiteKey: 'site-key' }} forceOpen />)

    await waitFor(() => expect(renderTurnstile).toHaveBeenCalledWith('#guest-snap-turnstile', expect.objectContaining({ sitekey: 'site-key' })))
  })
})
