import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { CasePage } from '../pages/CasePage'

describe('CasePage', () => {
  it('shows copy control, single decision title, and ladder', async () => {
    render(
      <MemoryRouter initialEntries={['/case/H-000001']}>
        <Routes>
          <Route path="/case/:hitId" element={<CasePage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Copy result/i })).toBeInTheDocument()
    })

    expect(screen.getByRole('heading', { level: 2, name: 'Same person' })).toBeInTheDocument()
    expect(screen.getByText('How it was decided')).toBeInTheDocument()
    expect(screen.getByText('Result')).toBeInTheDocument()
  })
})