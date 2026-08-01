import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { wedding } from '../config/wedding'
import { Gallery } from './Gallery'

describe('Gallery', () => {
  it('shows both childhood photos and the coming-soon message', () => {
    render(<Gallery gallery={wedding.gallery} />)

    expect(screen.getByAltText('신랑 한영신의 어린 시절')).toBeInTheDocument()
    expect(screen.getByAltText('신부 이다예의 어린 시절')).toBeInTheDocument()
    expect(screen.getByText('아이들은 자라서')).toBeInTheDocument()
    expect(screen.getByText('서로의 가장 좋은 친구가 되었습니다.')).toBeInTheDocument()
    expect(screen.getByText('TO BE CONTINUED...')).toBeInTheDocument()
    expect(screen.getByText('Wedding photos coming soon')).toBeInTheDocument()
  })

  it('opens the viewer and moves to the next photo', async () => {
    const user = userEvent.setup()
    render(<Gallery gallery={wedding.gallery} />)

    await user.click(screen.getByRole('button', { name: '신랑 한영신의 어린 시절 크게 보기' }))
    const viewer = screen.getByRole('dialog', { name: '사진 크게 보기' })
    expect(viewer).toBeInTheDocument()
    expect(viewer.parentElement).toBe(document.body)
    expect(screen.getByAltText('확대: 신랑 한영신의 어린 시절')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '다음 사진' }))
    expect(screen.getByAltText('확대: 신부 이다예의 어린 시절')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '사진 닫기' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
