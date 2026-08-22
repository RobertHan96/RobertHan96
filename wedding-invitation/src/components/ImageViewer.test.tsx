import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ImageViewer } from './ImageViewer'

const images = [
  { src: '/first.webp', alt: '첫 번째 사진' },
  { src: '/second.webp', alt: '두 번째 사진' },
]

describe('ImageViewer', () => {
  it('shows only the selected image and close button', () => {
    render(<ImageViewer image={images[0]} onClose={vi.fn()} />)

    expect(screen.getByRole('img', { name: '확대: 첫 번째 사진' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '사진 닫기' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '이전 사진' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '다음 사진' })).not.toBeInTheDocument()
    expect(screen.queryByText('1 / 2')).not.toBeInTheDocument()
  })

  it('closes with the Escape key', () => {
    const onClose = vi.fn()
    render(<ImageViewer image={images[0]} onClose={onClose} />)

    fireEvent.keyDown(window, { key: 'Escape' })

    expect(onClose).toHaveBeenCalledOnce()
  })
})
