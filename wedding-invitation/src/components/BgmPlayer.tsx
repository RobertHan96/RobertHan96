import { useCallback, useEffect, useRef, useState } from 'react'

import type { BgmConfig } from '../types/wedding'

type BgmPlayerProps = {
  bgm: BgmConfig
}

export function BgmPlayer({ bgm }: BgmPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [hasError, setHasError] = useState(false)

  const playAudio = useCallback(async () => {
    const audio = audioRef.current
    if (!audio || hasError) return

    try {
      await audio.play()
      setHasError(false)
      setIsPlaying(true)
    } catch {
      setIsPlaying(false)
    }
  }, [hasError])

  useEffect(() => {
    void playAudio()

    const resumePlayback = () => { void playAudio() }
    window.addEventListener('pointerdown', resumePlayback, { once: true })
    window.addEventListener('keydown', resumePlayback, { once: true })
    window.addEventListener('touchstart', resumePlayback, { once: true })

    return () => {
      window.removeEventListener('pointerdown', resumePlayback)
      window.removeEventListener('keydown', resumePlayback)
      window.removeEventListener('touchstart', resumePlayback)
    }
  }, [playAudio])

  const toggleMute = async () => {
    const audio = audioRef.current
    if (!audio) return

    if (!isPlaying) {
      audio.muted = false
      setIsMuted(false)
      await playAudio()
      return
    }

    const nextMuted = !audio.muted
    audio.muted = nextMuted
    setIsMuted(nextMuted)
  }

  return (
    <div className="bgm-player">
      <audio
        ref={audioRef}
        src={bgm.src}
        title={bgm.title}
        autoPlay
        loop
        preload="auto"
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onError={() => {
          setHasError(true)
          setIsPlaying(false)
        }}
      />
      <button
        type="button"
        className="bgm-player-button"
        aria-label={isMuted || !isPlaying ? 'BGM 켜기' : 'BGM 음소거'}
        aria-pressed={!isMuted && isPlaying}
        onClick={() => { void toggleMute() }}
      >
        <svg aria-hidden="true" className="bgm-player-icon" viewBox="0 0 24 24" focusable="false">
          <path d="M4 9v6h4l5 4V5L8 9H4Z" />
          {isMuted || !isPlaying ? (
            <path className="bgm-player-slash" d="M18 9l4 4m0-4-4 4" />
          ) : (
            <path className="bgm-player-wave" d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" />
          )}
        </svg>
      </button>
      {hasError ? <p role="status">음원 파일을 확인해주세요</p> : null}
    </div>
  )
}
