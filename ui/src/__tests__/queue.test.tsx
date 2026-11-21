import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { QueuePage } from '../pages/QueuePage'

describe('QueuePage', () => {
  it('filters by decision segment', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <QueuePage />
      </MemoryRouter>,
    )

    expect(screen.getAllByText('Sam Chen').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Jordan Blake').length).toBeGreaterThan(0)

    await user.click(screen.getByRole('button', { name: /Same ·/ }))

    expect(screen.getAllByText('Alex Rivera').length).toBeGreaterThan(0)
    expect(screen.queryAllByText('Jordan Blake')).toHaveLength(0)
  })

  it('filters rows by search', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <QueuePage />
      </MemoryRouter>,
    )

    const search = screen.getByPlaceholderText('Search customer or listed name')
    await user.type(search, 'Jordan')

    expect(screen.getAllByText('Jordan Blake').length).toBeGreaterThan(0)
    expect(screen.queryAllByText('Alex Rivera')).toHaveLength(0)
  })
})