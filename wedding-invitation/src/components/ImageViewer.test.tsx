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

  it('moves to adjacent photos with a horizontal swipe', () => {
    const onNext = vi.fn()
    render(<ImageViewer image={images[0]} onClose={vi.fn()} onNext={onNext} />)
    const viewer = screen.getByRole('dialog', { name: '사진 크게 보기' })

    fireEvent.touchStart(viewer, {
      touches: [{ clientX: 220, clientY: 200 }],
      changedTouches: [{ clientX: 220, clientY: 200 }],
    })
    fireEvent.touchEnd(viewer, {
      touches: [],
      changedTouches: [{ clientX: 120, clientY: 205 }],
    })

    expect(onNext).toHaveBeenCalledOnce()
  })

  it('does not move photos when a pinch gesture ends', () => {
    const onPrevious = vi.fn()
    const onNext = vi.fn()
    render(
      <ImageViewer
        image={images[0]}
        onClose={vi.fn()}
        onPrevious={onPrevious}
        onNext={onNext}
      />,
    )
    const viewer = screen.getByRole('dialog', { name: '사진 크게 보기' })

    fireEvent.touchStart(viewer, {
      touches: [{ clientX: 90, clientY: 200 }, { clientX: 210, clientY: 200 }],
      changedTouches: [{ clientX: 90, clientY: 200 }, { clientX: 210, clientY: 200 }],
    })
    fireEvent.touchEnd(viewer, {
      touches: [],
      changedTouches: [{ clientX: 190, clientY: 200 }, { clientX: 110, clientY: 200 }],
    })

    expect(onPrevious).not.toHaveBeenCalled()
    expect(onNext).not.toHaveBeenCalled()
  })

  it('moves to adjacent photos with keyboard arrows', () => {
    const onPrevious = vi.fn()
    const onNext = vi.fn()
    render(
      <ImageViewer
        image={images[0]}
        onClose={vi.fn()}
        onPrevious={onPrevious}
        onNext={onNext}
      />,
    )

    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    fireEvent.keyDown(window, { key: 'ArrowRight' })

    expect(onPrevious).toHaveBeenCalledOnce()
    expect(onNext).toHaveBeenCalledOnce()
  })
})
