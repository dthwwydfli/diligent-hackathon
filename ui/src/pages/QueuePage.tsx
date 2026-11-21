import { motion } from 'motion/react'
import { Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { sortedQueueRows, useQueue } from '../data/loadData'
import { decisionFilterKey } from '../data/syntheticSample'
import type { Decision } from '../types/case'
import { decisionChipLabel, strongChipClass } from '../lib/decisionStyles'
import { CountryFlag } from '../components/icons/CountryFlag'
import { AppShell } from '../components/layout/AppShell'

type FilterKey = 'All' | 'Review' | 'Same' | 'Cleared'

const filters: FilterKey[] = ['All', 'Review', 'Same', 'Cleared']

function filterDecision(f: FilterKey, d: Decision): boolean {
  if (f === 'All') return true
  if (f === 'Review') return d === 'REVIEW'
  if (f === 'Same') return d === 'SAME_ENTITY'
  return d === 'DIFFERENT_ENTITY'
}

export function QueuePage() {
  const { rows } = useQueue()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const decisionParam = searchParams.get('decision') as FilterKey | null
  const [filter, setFilter] = useState<FilterKey>(
    decisionParam && filters.includes(decisionParam) ? decisionParam : 'All',
  )
  const [query, setQuery] = useState('')

  useEffect(() => {
    if (decisionParam && filters.includes(decisionParam)) setFilter(decisionParam)
  }, [decisionParam])

  const sorted = useMemo(() => sortedQueueRows(rows), [rows])

  const counts = useMemo(() => {
    const c: Record<FilterKey, number> = {
      All: rows.length,
      Review: 0,
      Same: 0,
      Cleared: 0,
    }
    for (const r of rows) {
      c[decisionFilterKey(r.decision) as FilterKey] += 1
    }
    return c
  }, [rows])

  const visible = sorted.filter((r) => {
    if (!filterDecision(filter, r.decision)) return false
    if (!query.trim()) return true
    const q = query.toLowerCase()
    return (
      r.customer_name.toLowerCase().includes(q) ||
      r.listed_name.toLowerCase().includes(q)
    )
  })

  return (
    <AppShell>
      <div className="rounded-[20px] bg-surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <nav className="relative flex rounded-[10px] bg-plot p-1" aria-label="Queue filter">
            {filters.map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={`relative z-10 rounded-[8px] px-3 py-1.5 text-[13px] font-medium ${
                  filter === f ? 'text-ink' : 'text-ink-3'
                }`}
              >
                {f} · {counts[f]}
                {filter === f && (
                  <motion.span
                    layoutId="queue-filter-pill"
                    className="absolute inset-0 -z-10 rounded-[8px] bg-surface shadow-[0_1px_2px_rgba(0,0,0,0.06)]"
                    transition={{ type: 'spring', stiffness: 380, damping: 28 }}
                  />
                )}
              </button>
            ))}
          </nav>

          <label className="flex items-center gap-2 rounded-[10px] bg-plot px-3 py-2">
            <Search size={16} className="text-ink-3" aria-hidden />
            <input
              type="search"
              placeholder="Search customer or listed name"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-[240px] border-0 bg-transparent text-[13px] text-ink outline-none placeholder:text-ink-4"
            />
          </label>
        </div>

        <table className="mt-5 w-full border-collapse text-left text-[13px]">
          <thead>
            <tr className="text-[11px] font-medium uppercase tracking-[0.06em] text-ink-3">
              <th className="pb-3 font-medium">Customer</th>
              <th className="pb-3 font-medium">Listed as</th>
              <th className="pb-3 font-medium">Decision</th>
              <th className="pb-3 font-medium">Reason</th>
              <th className="pb-3 font-medium">Alert</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr
                key={row.hit_id}
                onClick={() => navigate(`/case/${row.hit_id}`)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') navigate(`/case/${row.hit_id}`)
                }}
                tabIndex={0}
                className="cursor-pointer border-t border-plot transition-colors hover:bg-plot/50"
              >
                <td className="py-3 font-medium text-ink">
                  <span className="inline-flex items-center gap-2">
                    <CountryFlag iso2={row.customer_country_iso2} />
                    {row.customer_name}
                  </span>
                </td>
                <td className="py-3 text-ink-2">
                  <span className="inline-flex items-center gap-2">
                    <CountryFlag iso2={row.listed_country_iso2} />
                    {row.listed_name}
                  </span>
                </td>
                <td className="py-3">
                  <span
                    className={`inline-block rounded-[6px] px-2 py-0.5 text-[11.5px] font-semibold ${strongChipClass(row.decision)}`}
                  >
                    {decisionChipLabel(row.decision)}
                  </span>
                </td>
                <td className="py-3 text-ink-2">
                  <span className="font-mono text-[11.5px] text-ink-3">{row.reason_code}</span>
                </td>
                <td className="py-3 font-mono text-[11.5px] text-ink-3">{row.alert_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  )
}
