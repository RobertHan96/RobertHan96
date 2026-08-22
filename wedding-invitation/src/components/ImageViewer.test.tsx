import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ImageViewer } from './ImageViewer'

const images = [
  { src: '/first.webp', alt: '첫 번째 사진' },
  { src: '/second.webp', alt: '두 번째 사진' },
]

describe('ImageViewer', () => {
  it('does not move photos when a pinch gesture ends', () => {
    const onMove = vi.fn()
    render(<ImageViewer images={images} index={0} onMove={onMove} onClose={vi.fn()} />)
    const viewer = screen.getByRole('dialog', { name: '사진 크게 보기' })

    fireEvent.touchStart(viewer, {
      touches: [{ clientX: 90, clientY: 200 }, { clientX: 210, clientY: 200 }],
      changedTouches: [{ clientX: 90, clientY: 200 }, { clientX: 210, clientY: 200 }],
    })
    fireEvent.touchEnd(viewer, {
      touches: [],
      changedTouches: [{ clientX: 190, clientY: 200 }, { clientX: 110, clientY: 200 }],
    })

    expect(onMove).not.toHaveBeenCalled()
  })

  it('moves photos for a single-finger horizontal swipe', () => {
    const onMove = vi.fn()
    render(<ImageViewer images={images} index={0} onMove={onMove} onClose={vi.fn()} />)
    const viewer = screen.getByRole('dialog', { name: '사진 크게 보기' })

    fireEvent.touchStart(viewer, {
      touches: [{ clientX: 220, clientY: 200 }],
      changedTouches: [{ clientX: 220, clientY: 200 }],
    })
    fireEvent.touchEnd(viewer, {
      touches: [],
      changedTouches: [{ clientX: 120, clientY: 205 }],
    })

    expect(onMove).toHaveBeenCalledWith(1)
  })

  it('does not move photos for a mostly vertical drag', () => {
    const onMove = vi.fn()
    render(<ImageViewer images={images} index={0} onMove={onMove} onClose={vi.fn()} />)
    const viewer = screen.getByRole('dialog', { name: '사진 크게 보기' })

    fireEvent.touchStart(viewer, {
      touches: [{ clientX: 160, clientY: 100 }],
      changedTouches: [{ clientX: 160, clientY: 100 }],
    })
    fireEvent.touchEnd(viewer, {
      touches: [],
      changedTouches: [{ clientX: 220, clientY: 260 }],
    })

    expect(onMove).not.toHaveBeenCalled()
  })
})
