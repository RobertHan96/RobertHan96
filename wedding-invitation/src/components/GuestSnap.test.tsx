import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { GuestSnap } from './GuestSnap'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

const config = {
  enabled: true,
  uploadOpensAt: '2026-11-15T00:00:00+09:00',
  maxFiles: 10,
  maxFileSizeBytes: 20 * 1024 * 1024,
  turnstileSiteKey: '',
}

describe('GuestSnap', () => {
  it('shows a disabled upload button before uploads open', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)))
    render(<GuestSnap config={config} now={new Date('2026-08-17T00:00:00Z')} />)

    expect(screen.getByRole('heading', { name: '게스트 스냅' })).toBeInTheDocument()
    expect(screen.getByText('여러분의 시선으로 담은 사진을 공유해주세요.')).toBeInTheDocument()
    expect(screen.getByText('예식 당일부터 사진을 남길 수 있습니다.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '사진 보내기' })).toBeDisabled()
    expect(screen.queryByLabelText('게스트 사진 선택')).not.toBeInTheDocument()
    expect(screen.queryByText(/사진 제공과 신랑·신부의 보관 및 공개에 동의합니다/)).not.toBeInTheDocument()
  })

  it('does not initialize Turnstile while uploads are closed', async () => {
    const renderTurnstile = vi.fn(() => 'widget-1')
    window.turnstile = { render: renderTurnstile, reset: vi.fn() }

    render(<GuestSnap
      config={{ ...config, turnstileSiteKey: 'site-key' }}
      now={new Date('2026-08-17T00:00:00Z')}
    />)

    await waitFor(() => expect(screen.getByRole('button', { name: '사진 보내기' })).toBeDisabled())
    expect(renderTurnstile).not.toHaveBeenCalled()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('uploads selected photos without collecting personal text', async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify({ ok: true, id: 'photo-1' }), { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<GuestSnap config={config} forceOpen />)

    const photo = new File(['photo'], '친구사진.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText('게스트 사진 선택'), photo)
    expect(screen.queryByLabelText('이름 (선택)')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('메시지 (선택)')).not.toBeInTheDocument()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '사진 1장 보내기' }))

    await waitFor(() => expect(screen.getByText('사진 1장을 잘 받았습니다.')).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const uploadRequest = fetchMock.mock.calls[0]
    expect(uploadRequest![0]).toBe('/api/guest-snap/photos')
    const uploadOptions = uploadRequest![1] as RequestInit
    expect((uploadOptions.body as FormData).get('guestName')).toBeNull()
    expect((uploadOptions.body as FormData).get('message')).toBeNull()
  })

  it('uploads multiple photos in one Turnstile-verified request', async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify({ ok: true, ids: ['photo-1', 'photo-2'] }), { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<GuestSnap config={config} forceOpen />)

    const photos = [
      new File(['photo-1'], '첫번째.jpg', { type: 'image/jpeg' }),
      new File(['photo-2'], '두번째.jpg', { type: 'image/jpeg' }),
    ]
    await user.upload(screen.getByLabelText('게스트 사진 선택'), photos)
    await user.click(screen.getByRole('button', { name: '사진 2장 보내기' }))

    await waitFor(() => expect(screen.getByText('사진 2장을 잘 받았습니다.')).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const uploadOptions = fetchMock.mock.calls[0]![1] as RequestInit
    expect((uploadOptions.body as FormData).getAll('photo')).toHaveLength(2)
  })

  it('automatically enables uploads when the opening time arrives', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-11-14T14:59:30Z'))
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)))

    render(<GuestSnap config={config} />)
    expect(screen.getByRole('button', { name: '사진 보내기' })).toBeDisabled()

    await act(async () => { vi.advanceTimersByTime(60_000) })

    expect(screen.getByLabelText('게스트 사진 선택')).toBeInTheDocument()
  })

  it('renders Turnstile explicitly when a site key is configured', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ photos: [] }), { status: 200 })))
    const renderTurnstile = vi.fn(() => 'widget-1')
    window.turnstile = { render: renderTurnstile, reset: vi.fn() }

    render(<GuestSnap config={{ ...config, turnstileSiteKey: 'site-key' }} forceOpen />)

    await waitFor(() => expect(renderTurnstile).toHaveBeenCalledWith('#guest-snap-turnstile', expect.objectContaining({ sitekey: 'site-key' })))
  })
})
