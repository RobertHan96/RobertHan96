import { useState } from 'react'
import { wedding } from '../config/wedding'
import { copyText } from '../lib/clipboard'
import type { Account } from '../types/wedding'
import { SectionHeading } from './SectionHeading'

function AccountGroup({
  side,
  label,
  accounts,
}: {
  side: '신랑' | '신부'
  label: string
  accounts: Account[]
}) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)

  const handleCopy = async (account: Account, index: number) => {
    await copyText(account.number)
    setCopiedIndex(index)
    window.setTimeout(() => setCopiedIndex(null), 1800)
  }

  return (
    <div className="account-group">
      <p className="account-side-title">{label}</p>
      <div className="account-items">
        {accounts.map((account, index) => (
          <div className="account-row" key={`${account.bank}-${account.number}`}>
            <div>
              <p className="account-meta">{account.bank} · {account.holder}</p>
              <p className="account-number">{account.number}</p>
            </div>
            <button
              aria-label={`${side} ${account.holder} 계좌번호 복사`}
              className="account-copy-button"
              onClick={() => void handleCopy(account, index)}
              type="button"
            >
              {copiedIndex === index ? '복사됨' : '복사'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

export function PendingDetails() {
  return (
    <section className="paper-section account-section reveal-section">
      <SectionHeading eyebrow="ACCOUNT" title="♥ 마음 전하실 곳 ♥" />
      <div className="account-list">
        <AccountGroup side="신랑" label="신랑측" accounts={wedding.accounts.groom} />
        <AccountGroup side="신부" label="신부측" accounts={wedding.accounts.bride} />
      </div>
      <p className="account-notice">화환은 정중히 사양하오니 너른 양해 부탁드립니다.</p>
    </section>
  )
}
