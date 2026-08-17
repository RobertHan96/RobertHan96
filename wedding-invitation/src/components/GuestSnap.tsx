import { type FormEvent, useEffect, useRef, useState } from 'react'

import { isGuestSnapOpen, optimizeGuestImage, validateGuestFiles } from '../lib/guestSnap'
import type { GuestSnapConfig } from '../types/wedding'
import { SectionHeading } from './SectionHeading'

declare global {
  interface Window {
    turnstile?: {
      render: (selector: string, options: {
        sitekey: string
        callback: (token: string) => void
        theme: string
        appearance: 'interaction-only'
      }) => string
      reset: (widgetId?: string) => void
    }
  }
}

function loadTurnstile(): Promise<void> {
  if (window.turnstile) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-guest-snap-turnstile]')
    const script = existing ?? document.createElement('script')
    const handleLoad = () => window.turnstile ? resolve() : reject(new Error('Turnstile을 불러오지 못했습니다.'))
    script.addEventListener('load', handleLoad, { once: true })
    script.addEventListener('error', () => reject(new Error('Turnstile을 불러오지 못했습니다.')), { once: true })
    if (!existing) {
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
      script.async = true
      script.defer = true
      script.dataset.guestSnapTurnstile = 'true'
      document.head.appendChild(script)
    }
  })
}

type GuestSnapProps = {
  config: GuestSnapConfig
  forceOpen?: boolean
  now?: Date
}

export function GuestSnap({ config, forceOpen = false, now }: GuestSnapProps) {
  const [clock, setClock] = useState(() => new Date())
  const [files, setFiles] = useState<File[]>([])
  const [turnstileToken, setTurnstileToken] = useState('')
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const turnstileWidgetId = useRef<string | undefined>(undefined)
  const uploadOpen = isGuestSnapOpen(config.enabled, config.uploadOpensAt, now ?? clock, forceOpen)

  useEffect(() => {
    if (now || forceOpen || !config.enabled) return
    const timer = window.setInterval(() => setClock(new Date()), 30_000)
    return () => window.clearInterval(timer)
  }, [config.enabled, forceOpen, now])

  useEffect(() => {
    if (!uploadOpen || !config.turnstileSiteKey) return
    let cancelled = false
    void loadTurnstile()
      .then(() => {
        if (cancelled || !window.turnstile) return
        turnstileWidgetId.current = window.turnstile.render('#guest-snap-turnstile', {
          sitekey: config.turnstileSiteKey,
          callback: setTurnstileToken,
          theme: 'light',
          appearance: 'interaction-only',
        })
      })
      .catch(() => setErrors(['보안 확인을 불러오지 못했습니다. 페이지를 새로고침해주세요.']))
    return () => { cancelled = true }
  }, [config.turnstileSiteKey, uploadOpen])

  const handleSelection = (selected: File[]) => {
    const result = validateGuestFiles(selected, config.maxFiles, config.maxFileSizeBytes)
    setFiles(result.valid)
    setErrors(result.errors)
    setStatus('')
    setProgress(0)
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!files.length || (config.turnstileSiteKey && !turnstileToken)) return
    setUploading(true)
    setErrors([])
    setStatus('')
    setProgress(0)

    let uploadErrorMessage = '사진 업로드에 실패했습니다. 잠시 후 다시 시도해주세요.'
    try {
      const body = new FormData()
      let preparedCount = 0
      for (const file of files) {
        const prepared = await optimizeGuestImage(file)
        body.append('photo', prepared, prepared.name)
        preparedCount += 1
        setProgress(preparedCount)
      }
      body.set('turnstileToken', turnstileToken)
      const response = await fetch('/api/guest-snap/photos', { method: 'POST', body })
      const result = await response.json().catch(() => ({})) as { ok?: boolean; error?: string }
      if (!response.ok || result.ok !== true) {
        uploadErrorMessage = result.error || uploadErrorMessage
        throw new Error(uploadErrorMessage)
      }

      setStatus(`사진 ${files.length}장을 잘 받았습니다.`)
      setFiles([])
      setTurnstileToken('')
      window.turnstile?.reset(turnstileWidgetId.current)
    } catch {
      setTurnstileToken('')
      window.turnstile?.reset(turnstileWidgetId.current)
      setErrors([uploadErrorMessage])
    } finally {
      setUploading(false)
    }
  }

  return (
    <section className="paper-section guest-snap-section reveal-section">
      <SectionHeading eyebrow="GUEST SNAP" title="게스트 스냅" />
      <p className="guest-snap-intro">여러분의 시선으로 담은 사진을 공유해주세요.</p>

      {uploadOpen ? (
        <form className="guest-snap-form" onSubmit={(event) => void handleSubmit(event)}>
          <label className="guest-photo-picker">
            <span>사진 선택</span>
            <small>최대 {config.maxFiles}장 · 장당 20MB</small>
            <input
              aria-label="게스트 사진 선택"
              type="file"
              accept="image/jpeg,image/png,image/webp,image/heic,image/heif"
              multiple
              onChange={(event) => handleSelection(Array.from(event.target.files ?? []))}
            />
          </label>

          {files.length > 0 && (
            <div className="guest-selected-files">
              {files.map((file) => <span key={`${file.name}-${file.lastModified}`}>{file.name}</span>)}
            </div>
          )}

          {config.turnstileSiteKey && (
            <div className="cf-turnstile" id="guest-snap-turnstile" />
          )}
          <button
            className="guest-upload-button"
            type="submit"
            disabled={!files.length || uploading || Boolean(config.turnstileSiteKey && !turnstileToken)}
          >
            {uploading ? `${progress} / ${files.length} 업로드 중` : `사진 ${files.length}장 보내기`}
          </button>
        </form>
      ) : (
        <div className="guest-snap-closed">
          <p>예식 당일부터 사진을 남길 수 있습니다.</p>
          <button className="guest-upload-button" type="button" disabled>사진 보내기</button>
        </div>
      )}

      {errors.length > 0 && <div className="guest-snap-errors" role="alert">{errors.map((error) => <p key={error}>{error}</p>)}</div>}
      {status && <p className="guest-snap-status" role="status">{status}</p>}
    </section>
  )
}
