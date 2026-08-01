import { useState } from 'react'

import { wedding } from '../config/wedding'
import { copyText } from '../lib/clipboard'
import { sendKakaoShare } from '../lib/kakao'
import { SectionHeading } from './SectionHeading'

export function Share() {
  const [copied, setCopied] = useState(false)
  const [shareStatus, setShareStatus] = useState('')
  const copyLink = async () => {
    await copyText(wedding.share.url)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }
  const shareOnKakao = async () => {
    setShareStatus('')
    try {
      sendKakaoShare(wedding.share)
    } catch {
      await copyText(wedding.share.url)
      setShareStatus('카카오톡 공유를 열지 못해 링크를 복사했습니다.')
    }
  }

  const hasKakaoKey = Boolean(wedding.share.kakaoJavascriptKey)
  return (
    <section className="paper-section share-section reveal-section">
      <SectionHeading eyebrow="SHARE" title="소식을 전해주세요" />
      <div className="share-actions">
        <button type="button" className="primary-button" aria-label="청첩장 링크 복사" onClick={copyLink}>
          {copied ? '링크를 복사했어요' : '링크 복사'}
        </button>
        <button type="button" className="kakao-button" disabled={!hasKakaoKey} onClick={shareOnKakao}>
          {hasKakaoKey ? '카카오톡으로 공유' : '카카오 JavaScript 키 설정 필요'}
        </button>
      </div>
      {shareStatus && <p className="share-status" aria-live="polite">{shareStatus}</p>}
    </section>
  )
}

export function Footer() {
  return (
    <footer className="invitation-footer">
      <p>{wedding.groom.name} <span>♥</span> {wedding.bride.name}</p>
      <time dateTime={wedding.date.iso}>{wedding.date.display}</time>
    </footer>
  )
}
