import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { wedding } from '../config/wedding'
import { Gallery } from './Gallery'

describe('Gallery', () => {
  it('shows every wedding photo in a compact thumbnail grid', () => {
    const { container } = render(<Gallery gallery={wedding.gallery} />)
    const expectedOrder = [8, 9, 10, 11, 12, 13, 14, 15, 4, 5, 7, 6, 1, 2, 3, 16, 17, 18]
      .map((number) => `/images/wedding/photo-${String(number).padStart(2, '0')}.webp`)

    expect(screen.getByAltText('신랑 한영신의 어린 시절')).toBeInTheDocument()
    expect(screen.getByAltText('신부 이다예의 어린 시절')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '오늘의 우리' })).toBeInTheDocument()
    expect(wedding.gallery.hero.src).toBe('/images/wedding/photo-14.webp')
    expect(wedding.gallery.wedding.map((image) => image.src)).toEqual(expectedOrder)
    expect(container.querySelectorAll('.wedding-thumbnail')).toHaveLength(18)
    expect(container.querySelector('.wedding-photo-grid')).toHaveAttribute('data-layout', '3x6')
    expect(screen.queryByText('TO BE CONTINUED...')).not.toBeInTheDocument()
    expect(screen.queryByText('Wedding photos coming soon')).not.toBeInTheDocument()
  })

  it('opens only the selected photo and closes the viewer', async () => {
    const user = userEvent.setup()
    render(<Gallery gallery={wedding.gallery} />)

    await user.click(screen.getByRole('button', { name: '신랑 한영신의 어린 시절 크게 보기' }))
    const viewer = screen.getByRole('dialog', { name: '사진 크게 보기' })
    expect(viewer).toBeInTheDocument()
    expect(viewer.parentElement).toBe(document.body)
    expect(screen.getByAltText('확대: 신랑 한영신의 어린 시절')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '이전 사진' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '다음 사진' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '사진 닫기' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
