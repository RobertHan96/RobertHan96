import { useState } from 'react'

import { wedding } from '../config/wedding'
import { copyText } from '../lib/clipboard'
import { SectionHeading } from './SectionHeading'

export function Share() {
  const [copied, setCopied] = useState(false)
  const copyLink = async () => {
    await copyText(window.location.href)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }
  return (
    <section className="paper-section share-section reveal-section">
      <SectionHeading eyebrow="SHARE" title="소식을 전해주세요" />
      <div className="share-actions">
        <button type="button" className="primary-button" aria-label="청첩장 링크 복사" onClick={copyLink}>
          {copied ? '링크를 복사했어요' : '링크 복사'}
        </button>
        <button type="button" className="kakao-button" disabled={!wedding.share.kakaoJavascriptKey}>
          카카오톡 공유 준비 중
        </button>
      </div>
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
