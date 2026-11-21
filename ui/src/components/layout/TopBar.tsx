import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { NavLink, useLocation, useMatch } from 'react-router-dom'
import { loadQueue } from '../../data/loadData'

export function TopBar() {
  const { pathname } = useLocation()
  // The bar lives in the layout route, so it reads the hit id from the URL, not route params.
  const hitId = useMatch('/case/:hitId')?.params.hitId
  const [caseTo, setCaseTo] = useState('/case/H-000001')

  useEffect(() => {
    if (hitId) {
      setCaseTo(`/case/${hitId}`)
      return
    }
    let cancelled = false
    loadQueue().then(({ rows }) => {
      if (!cancelled && rows[0]) setCaseTo(`/case/${rows[0].hit_id}`)
    })
    return () => {
      cancelled = true
    }
  }, [hitId])

  const tabs = [
    { to: '/', label: 'Queue', match: (p: string) => p === '/' },
    { to: caseTo, label: 'Case', match: (p: string) => p.startsWith('/case') },
    { to: '/run', label: 'Run', match: (p: string) => p === '/run' },
  ]

  return (
    <header className="flex items-center justify-between gap-6 py-4">
      <div className="flex items-center gap-3">
        <motion.img
          src="/logo.svg"
          alt=""
          className="h-7 w-7"
          initial={{ opacity: 0, scale: 0.85, rotate: -40 }}
          animate={{ opacity: 1, scale: 1, rotate: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
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

      <div className="w-[120px]" aria-hidden />
    </header>
  )
}