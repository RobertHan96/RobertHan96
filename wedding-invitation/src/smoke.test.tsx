import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('mobile wedding invitation', () => {
  it('renders the couple and invitation title', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: '이다예 그리고 한영신' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '서로의 오늘이 되어' })).toBeInTheDocument()
  })
})
