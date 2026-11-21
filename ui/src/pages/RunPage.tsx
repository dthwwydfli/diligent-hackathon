import { motion } from 'motion/react'
import { useMemo, type ReactNode } from 'react'
import { useQueue, useRunSummary } from '../data/loadData'
import type { Decision, QueueRow } from '../types/case'
import { DecisionFlow } from '../components/run/DecisionFlow'
import { usePrefersReducedMotion } from '../components/motion/usePrefersReducedMotion'
import { decisionChipLabel, decisionColorVar } from '../lib/decisionStyles'

const ORDER: Decision[] = ['DIFFERENT_ENTITY', 'SAME_ENTITY', 'REVIEW']
const TOP_CATEGORIES = 6

function byCategory(rows: QueueRow[]) {
  const map = new Map<string, Record<Decision, number>>()
  for (const r of rows) {
    const c = map.get(r.category) ?? { DIFFERENT_ENTITY: 0, SAME_ENTITY: 0, REVIEW: 0 }
    c[r.decision] += 1
    map.set(r.category, c)
  }
  return [...map]
    .map(([name, split]) => ({ name, split, total: split.DIFFERENT_ENTITY + split.SAME_ENTITY + split.REVIEW }))
    .sort((a, b) => b.total - a.total)
    .slice(0, TOP_CATEGORIES)
}

function Stat({ label, value, children }: { label: string; value: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col justify-between rounded-[14px] bg-plot px-4 py-3">
      <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-ink-3">{label}</p>
      <p className="mt-1 text-[26px] font-normal tracking-tight text-ink">{value}</p>
      {children}
    </div>
  )
}

export function RunPage() {
  const { summary, loading } = useRunSummary()
  const { rows } = useQueue()
  const reduced = usePrefersReducedMotion()
  const categories = useMemo(() => byCategory(rows), [rows])

  if (loading) return <p className="text-ink-3">Loading run…</p>

  if (!summary) {
    return (
      <div className="flex h-full items-center justify-center rounded-[20px] bg-surface">
        <p className="text-[18px] text-ink-3">No run yet</p>
      </div>
    )
  }

  const settled = summary.split.DIFFERENT_ENTITY + summary.split.SAME_ENTITY
  const settledPct = Math.round((settled / (summary.hits || 1)) * 100)
  const msPerHit = Math.round((summary.seconds * 1000) / (summary.hits || 1))

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="grid shrink-0 grid-cols-2 gap-3 rounded-[20px] bg-surface p-3 lg:grid-cols-4">
        <Stat label="Settled without an analyst" value={`${settledPct}%`}>
          <p className="text-[12px] text-ink-3">
            {settled} of {summary.hits} hits
          </p>
        </Stat>
        <Stat label="Unsafe clearances" value={`${summary.unsafe_practice} / ${summary.practice_labels}`}>
          {/* One dot per labelled practice hit; a wrongly cleared one turns violet. */}
          <div className="mt-1 flex flex-wrap gap-[3px]" aria-hidden>
            {Array.from({ length: summary.practice_labels }, (_, i) => (
              <motion.span
                key={i}
                className={`h-[6px] w-[6px] rounded-full ${i < summary.unsafe_practice ? 'bg-match' : 'bg-clear'}`}
                initial={reduced ? false : { scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: reduced ? 0 : i * 0.012 }}
              />
            ))}
          </div>
        </Stat>
        <Stat label="Identical runs" value={`${summary.identical_runs} / ${summary.runs}`}>
          <p className="text-[12px] text-ink-3">Same input, same answers</p>
        </Stat>
        <Stat label="Time and cost" value={`${summary.seconds}s · $${summary.cost_usd.toFixed(2)}`}>
          <p className="text-[12px] text-ink-3">{msPerHit} ms per hit</p>
        </Stat>
      </div>

      <div className="flex min-h-0 flex-1 gap-3">
        <section className="flex min-w-0 flex-1 flex-col rounded-[20px] bg-surface p-5">
          <div className="flex items-baseline justify-between gap-4">
            <h2 className="text-[18px] font-normal tracking-[-0.3px] text-ink">Where every hit went</h2>
            <p className="text-[12px] text-ink-3">Hover a stream · click a decision to open it</p>
          </div>
          <div className="mt-3 flex min-h-0 flex-1 items-center">
            {rows.length > 0 && <DecisionFlow rows={rows} reduced={reduced} />}
          </div>
        </section>

        <aside className="hidden w-[320px] shrink-0 flex-col overflow-y-auto rounded-[20px] bg-surface p-5 lg:flex">
          <h2 className="text-[18px] font-normal tracking-[-0.3px] text-ink">By watchlist category</h2>
          <ul className="mt-4 space-y-3.5">
            {categories.map((c, ci) => (
              <li key={c.name}>
                <div className="flex justify-between text-[12.5px]">
                  <span className="font-medium text-ink">{c.name}</span>
                  <span className="text-ink-3">{c.total}</span>
                </div>
                <div className="mt-1.5 flex h-2 overflow-hidden rounded-full bg-plot">
                  {ORDER.map((d) =>
                    c.split[d] ? (
                      <motion.div
                        key={d}
                        title={`${decisionChipLabel(d)} ${c.split[d]}`}
                        style={{ background: decisionColorVar[d] }}
                        initial={reduced ? false : { width: 0 }}
                        animate={{ width: `${(c.split[d] / c.total) * 100}%` }}
                        transition={{ delay: reduced ? 0 : 0.2 + ci * 0.05, type: 'spring', stiffness: 120, damping: 20 }}
                      />
                    ) : null,
                  )}
                </div>
              </li>
            ))}
          </ul>
          <div className="mt-auto flex gap-4 pt-5 text-[12px] text-ink-2">
            {ORDER.map((d) => (
              <span key={d} className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ background: decisionColorVar[d] }} />
                {decisionChipLabel(d)}
              </span>
            ))}
          </div>
        </aside>
      </div>
    </div>
  )
}
