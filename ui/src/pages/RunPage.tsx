import { motion } from 'motion/react'
import { Link } from 'react-router-dom'
import { useRunSummary } from '../data/loadData'
import type { Decision } from '../types/case'
import { AppShell } from '../components/layout/AppShell'
import { usePrefersReducedMotion } from '../components/motion/usePrefersReducedMotion'

function splitLabel(d: Decision): string {
  switch (d) {
    case 'DIFFERENT_ENTITY':
      return 'Cleared'
    case 'SAME_ENTITY':
      return 'Same'
    case 'REVIEW':
      return 'Review'
  }
}

const splitColors: Record<Decision, string> = {
  DIFFERENT_ENTITY: 'bg-clear',
  SAME_ENTITY: 'bg-match',
  REVIEW: 'bg-review',
}

export function RunPage() {
  const { summary, loading } = useRunSummary()
  const reduced = usePrefersReducedMotion()

  if (loading) {
    return (
      <AppShell>
        <p className="text-ink-3">Loading run…</p>
      </AppShell>
    )
  }

  if (!summary) {
    return (
      <AppShell>
        <div className="flex h-[320px] items-center justify-center rounded-[20px] bg-surface">
          <p className="text-[18px] text-ink-3">No run yet</p>
        </div>
      </AppShell>
    )
  }

  const total = summary.hits || 1
  const order: Decision[] = ['DIFFERENT_ENTITY', 'SAME_ENTITY', 'REVIEW']

  return (
    <AppShell>
      <div className="rounded-[20px] bg-surface p-6">
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: 'Hits decided', value: String(summary.hits) },
            {
              label: 'Unsafe clearances',
              value: `${summary.unsafe_practice} / ${summary.practice_labels}`,
            },
            {
              label: 'Identical runs',
              value: `${summary.identical_runs} / ${summary.runs}`,
            },
            {
              label: 'Time and cost',
              value: `${summary.seconds}s · $${summary.cost_usd.toFixed(2)}`,
            },
          ].map((card) => (
            <motion.div
              key={card.label}
              className="rounded-[14px] bg-plot px-4 py-5"
              initial={reduced ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-ink-3">
                {card.label}
              </p>
              <p className="mt-2 text-[28px] font-normal tracking-tight text-ink">{card.value}</p>
            </motion.div>
          ))}
        </div>

        <div className="mt-8">
          <p className="text-[13px] font-medium text-ink-2">Decision split</p>
          <div className="mt-3 flex h-10 w-full overflow-hidden rounded-[10px] bg-plot">
            {order.map((d) => {
              const count = summary.split[d]
              const pct = (count / total) * 100
              if (pct <= 0) return null
              return (
                <motion.div
                  key={d}
                  className={`${splitColors[d]} h-full`}
                  initial={reduced ? false : { width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ type: 'spring', stiffness: 120, damping: 20 }}
                >
                  <Link
                    to={`/?decision=${splitLabel(d)}`}
                    className="flex h-full items-center justify-center text-[11.5px] font-semibold text-ink"
                    title={`${splitLabel(d)}: ${count}`}
                  >
                    {splitLabel(d)} {count}
                  </Link>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>
    </AppShell>
  )
}