import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { wedding } from '../config/wedding'
import { Gallery } from './Gallery'

describe('Gallery', () => {
  it('shows every wedding photo in a compact thumbnail grid', () => {
    const { container } = render(<Gallery gallery={wedding.gallery} />)

    expect(screen.getByAltText('신랑 한영신의 어린 시절')).toBeInTheDocument()
    expect(screen.getByAltText('신부 이다예의 어린 시절')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '오늘의 우리' })).toBeInTheDocument()
    expect(screen.getByAltText('정원에서 함께 웃는 한영신과 이다예')).toBeInTheDocument()
    expect(screen.getByAltText('베일 아래 마주 보는 한영신과 이다예')).toBeInTheDocument()
    expect(screen.getByAltText('베일 아래 함께 웃는 한영신과 이다예')).toBeInTheDocument()
    expect(container.querySelectorAll('.wedding-thumbnail')).toHaveLength(wedding.gallery.wedding.length)
    expect(container.querySelector('.wedding-photo-grid')).toBeInTheDocument()
    expect(screen.queryByText('TO BE CONTINUED...')).not.toBeInTheDocument()
    expect(screen.queryByText('Wedding photos coming soon')).not.toBeInTheDocument()
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
