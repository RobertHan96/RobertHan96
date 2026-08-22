import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ImageViewer } from './ImageViewer'

const images = [
  { src: '/first.webp', alt: '첫 번째 사진', width: 1200, height: 1800 },
  { src: '/second.webp', alt: '두 번째 사진', width: 1800, height: 1200 },
]

describe('ImageViewer', () => {
  it('fills the lightbox with the selected image and no visible controls', async () => {
    const { container } = render(<ImageViewer images={images} index={1} onClose={vi.fn()} />)

    expect(await screen.findByAltText('두 번째 사진')).toBeInTheDocument()
    expect(container.querySelector('.viewer-close')).not.toBeInTheDocument()
    expect(document.querySelectorAll('.yarl__button')).toHaveLength(0)
    expect(document.querySelector('.yarl__container')).toHaveStyle({ backgroundColor: '#fff' })
  })

  it('closes with the Escape key', async () => {
    const onClose = vi.fn()
    render(<ImageViewer images={images} index={0} onClose={onClose} />)
    await screen.findByAltText('첫 번째 사진')

    const lightbox = document.querySelector('.yarl__container')
    expect(lightbox).toBeInTheDocument()
    fireEvent.keyDown(lightbox!, { key: 'Escape', code: 'Escape', keyCode: 27 })

    await waitFor(() => expect(onClose).toHaveBeenCalledOnce())
  })

  it('closes when the empty backdrop around the image is tapped', async () => {
    const onClose = vi.fn()
    render(<ImageViewer images={images} index={0} onClose={onClose} />)
    await screen.findByAltText('첫 번째 사진')
    const backdrop = document.querySelector('.yarl__slide_current .yarl__slide_wrapper')
    expect(backdrop).toBeInTheDocument()

    fireEvent.pointerDown(backdrop!, { pointerId: 1, pointerType: 'touch' })
    fireEvent.pointerUp(backdrop!, { pointerId: 1, pointerType: 'touch' })

    await waitFor(() => expect(onClose).toHaveBeenCalledOnce())
  })
})
