import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'

afterEach(() => vi.unstubAllGlobals())

describe('wedding content', () => {
  it('renders the ceremony, invitation, and family information', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: '한영신 그리고 이다예' })).toBeInTheDocument()
    expect(screen.getAllByText('2026. 11. 15').length).toBeGreaterThan(0)
    expect(screen.getAllByText('더컨벤션 잠실').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: '서로의 오늘이 되어' })).toBeInTheDocument()
    expect(screen.getByText('한성용 · 황진심의 아들')).toBeInTheDocument()
    expect(screen.getByText('이성환 · 오영근의 딸')).toBeInTheDocument()
  })

  it('renders telephone and message links for the couple', () => {
    render(<App />)

    expect(screen.getByRole('link', { name: '신랑에게 전화' })).toHaveAttribute('href', 'tel:01022345619')
    expect(screen.getByRole('link', { name: '신랑에게 문자' })).toHaveAttribute('href', 'sms:01022345619')
    expect(screen.getByRole('link', { name: '신부에게 전화' })).toHaveAttribute('href', 'tel:01071685132')
    expect(screen.getByRole('link', { name: '신부에게 문자' })).toHaveAttribute('href', 'sms:01071685132')
  })

  it('reveals a section when it enters the viewport', () => {
    let reveal: IntersectionObserverCallback | undefined
    const observe = vi.fn()
    const disconnect = vi.fn()

    class MockIntersectionObserver {
      root = null
      rootMargin = ''
      thresholds: number[] = []
      observe = observe
      disconnect = disconnect
      unobserve = vi.fn()
      takeRecords = vi.fn(() => [])

      constructor(callback: IntersectionObserverCallback) {
        reveal = callback
      }
    }
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver)

    const { container } = render(<App />)
    const section = container.querySelector<HTMLElement>('.reveal-section')
    expect(section).not.toBeNull()
    expect(observe).toHaveBeenCalledWith(section)

    reveal?.([{ target: section!, isIntersecting: true } as unknown as IntersectionObserverEntry], {} as IntersectionObserver)
    expect(section).toHaveClass('is-visible')

  })
})
