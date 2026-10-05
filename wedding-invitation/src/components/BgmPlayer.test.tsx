import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { BgmPlayer } from './BgmPlayer'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('BgmPlayer', () => {
  it('autoplays the configured music and toggles mute', async () => {
    const play = vi.spyOn(window.HTMLMediaElement.prototype, 'play').mockResolvedValue()
    const pause = vi.spyOn(window.HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined)

    render(<BgmPlayer bgm={{ title: 'Love wins all 피아노 ver.', src: '/audio/love-wins-all-piano.mp3' }} />)

    const button = await screen.findByRole('button', { name: 'BGM 음소거' })
    const audio = screen.getByTitle('Love wins all 피아노 ver.')

    expect(audio).toHaveAttribute('src', '/audio/love-wins-all-piano.mp3')
    expect(audio).toHaveAttribute('autoplay')
    expect(audio).toHaveAttribute('loop')
    await waitFor(() => expect(play).toHaveBeenCalledTimes(1))

    fireEvent.click(button)
    expect(screen.getByRole('button', { name: 'BGM 켜기' })).toBeInTheDocument()
    expect((audio as HTMLAudioElement).muted).toBe(true)
    expect(pause).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'BGM 켜기' }))
    expect(screen.getByRole('button', { name: 'BGM 음소거' })).toBeInTheDocument()
    expect((audio as HTMLAudioElement).muted).toBe(false)
  })
})
