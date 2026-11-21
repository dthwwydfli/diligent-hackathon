import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { RunPage } from '../pages/RunPage'

describe('RunPage', () => {
  it('shows empty state without summary.json', async () => {
    render(
      <MemoryRouter>
        <RunPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('No run yet')).toBeInTheDocument()
    })
  })
})