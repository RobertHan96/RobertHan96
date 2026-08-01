import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

describe('wedding details', () => {
  beforeEach(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    })
  })

  it('renders the calendar, selected date, venue, and map', () => {
    render(<App />)

    expect(screen.getByText('NOVEMBER 2026')).toBeInTheDocument()
    expect(screen.getByText('15', { selector: '[aria-current="date"]' })).toBeInTheDocument()
    expect(screen.getByText('서울 송파구 올림픽로 319 3층')).toBeInTheDocument()
    expect(screen.getByAltText('더컨벤션 잠실 오시는 길 약도')).toBeInTheDocument()
  })

  it('copies the venue address and current invitation link', async () => {
    const user = userEvent.setup()
    const writeText = vi.spyOn(navigator.clipboard, 'writeText')
    render(<App />)

    await user.click(screen.getByRole('button', { name: '예식장 주소 복사' }))
    expect(writeText).toHaveBeenCalledWith('서울 송파구 올림픽로 319 3층')

    await user.click(screen.getByRole('button', { name: '청첩장 링크 복사' }))
    expect(writeText).toHaveBeenCalledWith(window.location.href)
  })

  it('shows preparation states for details that are not provided yet', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: '교통 안내' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '마음 전하실 곳' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '참석 여부 전달' })).toBeInTheDocument()
    expect(screen.getAllByText('안내를 준비하고 있습니다')).toHaveLength(2)
    expect(screen.getByText('참석 여부 전달은 추후 오픈됩니다')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '카카오톡 공유 준비 중' })).toBeDisabled()
  })

  it('opens the single map image without gallery navigation controls', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '약도 크게 보기' }))

    expect(screen.getByRole('dialog', { name: '사진 크게 보기' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '이전 사진' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '다음 사진' })).not.toBeInTheDocument()
  })
})
