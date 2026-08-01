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
    expect(screen.getByText('계좌 안내를 준비하고 있습니다')).toBeInTheDocument()
    expect(
      screen.getByText('축하의 마음만 감사히 받겠습니다. 화환은 정중히 사양하오니 너른 양해 부탁드립니다.'),
    ).toBeInTheDocument()
    expect(screen.getByText('참석 여부 전달은 추후 오픈됩니다')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '카카오톡 공유 준비 중' })).toBeDisabled()
  })

  it('shows transportation details and map service links', () => {
    render(<App />)

    expect(screen.getByText('2호선 잠실역 8번 출구 약 300m')).toBeInTheDocument()
    expect(screen.getByText('8호선 잠실역 9번 출구 약 30m')).toBeInTheDocument()
    expect(screen.getByText('간선 302, 310, 341, 360')).toBeInTheDocument()
    expect(screen.getByText('지선 2311, 3411')).toBeInTheDocument()
    expect(screen.getByText('광역·직행 1000, 1100, 1700')).toBeInTheDocument()
    expect(screen.getByText('신주소 송파구 올림픽로 319')).toBeInTheDocument()
    expect(screen.getByText('구주소 송파구 신천동 11-7')).toBeInTheDocument()
    expect(screen.getByText('교통회관 지상·지하 주차장 이용')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '네이버지도' })).toHaveAttribute('href', 'https://naver.me/F1rxJcrX')
    expect(screen.getByRole('link', { name: '카카오맵' })).toHaveAttribute('href', 'https://place.map.kakao.com/17651361')
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
