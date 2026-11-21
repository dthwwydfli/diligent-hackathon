import { motion } from 'motion/react'
import { NavLink, useLocation } from 'react-router-dom'

const tabs = [
  { to: '/', label: 'Queue', match: (p: string) => p === '/' },
  { to: '/case/H-000001', label: 'Case', match: (p: string) => p.startsWith('/case') },
  { to: '/run', label: 'Run', match: (p: string) => p === '/run' },
] as const

interface TopBarProps {
  meta?: string
}

export function TopBar({ meta = 'Synthetic sample · 3 hits · 12s' }: TopBarProps) {
  const { pathname } = useLocation()

  return (
    <header className="flex items-center justify-between gap-6 py-4">
      <div className="flex items-center gap-3">
        <div className="relative flex h-5 w-5 items-center justify-center rounded-[6px] bg-ink" aria-hidden>
          <span className="absolute bottom-0.5 right-0.5 h-1.5 w-1.5 rounded-full bg-clear" />
        </div>
        <span className="text-base font-semibold tracking-[-0.02em] text-ink">Namesake</span>
      </div>

      <nav className="relative flex rounded-[10px] bg-plot p-1" aria-label="Main">
        {tabs.map((tab) => {
          const active = tab.match(pathname)
          return (
            <NavLink
              key={tab.label}
              to={tab.to}
              className={`relative z-10 rounded-[8px] px-4 py-1.5 text-[13px] font-medium ${
                active ? 'text-ink' : 'text-ink-3 hover:text-ink-2'
              }`}
            >
              {tab.label}
              {active && (
                <motion.span
                  layoutId="top-segment-pill"
                  className="absolute inset-0 -z-10 rounded-[8px] bg-surface shadow-[0_1px_2px_rgba(0,0,0,0.06)]"
                  transition={{ type: 'spring', stiffness: 380, damping: 28 }}
                />
              )}
            </NavLink>
          )
        })}
      </nav>

      <p className="max-w-[280px] truncate text-right text-xs text-ink-3">{meta}</p>
    </header>
  )
}