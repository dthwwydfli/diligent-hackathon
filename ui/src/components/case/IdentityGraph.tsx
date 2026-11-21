import { motion } from 'motion/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { CasePage } from '../../types/case'
import { linkStroke } from '../../lib/decisionStyles'
import { CountryFlag } from '../icons/CountryFlag'
import { GroupHandle } from '../icons/GroupHandle'
import { ProviderBadge } from '../icons/ProviderBadge'
import { usePrefersReducedMotion } from '../motion/usePrefersReducedMotion'

interface IdentityGraphProps {
  page: CasePage
  highlightLinkIds: string[]
}

interface EdgeSeg {
  key: string
  x1: number
  y1: number
  x2: number
  y2: number
  outcome: import('../../types/case').LinkOutcome
  highlighted: boolean
}

function anchorRight(el: HTMLElement, board: DOMRect): { x: number; y: number } {
  const r = el.getBoundingClientRect()
  return { x: r.right - board.left, y: r.top + r.height / 2 - board.top }
}

function anchorLeft(el: HTMLElement, board: DOMRect): { x: number; y: number } {
  const r = el.getBoundingClientRect()
  return { x: r.left - board.left, y: r.top + r.height / 2 - board.top }
}

function bezierPath(x1: number, y1: number, x2: number, y2: number): string {
  const cx = (x1 + x2) / 2
  return `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`
}

export function IdentityGraph({ page, highlightLinkIds }: IdentityGraphProps) {
  const boardRef = useRef<HTMLDivElement>(null)
  const nodeRefs = useRef<Map<string, HTMLDivElement>>(new Map())
  const [edges, setEdges] = useState<EdgeSeg[]>([])
  const reduced = usePrefersReducedMotion()

  const setNodeRef = useCallback((id: string, el: HTMLDivElement | null) => {
    if (el) nodeRefs.current.set(id, el)
    else nodeRefs.current.delete(id)
  }, [])

  const redraw = useCallback(() => {
    const board = boardRef.current
    if (!board) return
    const rect = board.getBoundingClientRect()
    const next: EdgeSeg[] = []
    for (const [from, to, outcome] of page.links) {
      const a = nodeRefs.current.get(from)
      const b = nodeRefs.current.get(to)
      if (!a || !b) continue
      const left = anchorRight(a, rect)
      const right = anchorLeft(b, rect)
      const hl =
        highlightLinkIds.length === 0 ||
        (highlightLinkIds.includes(from) && highlightLinkIds.includes(to))
      next.push({
        key: `${from}-${to}`,
        x1: left.x,
        y1: left.y,
        x2: right.x,
        y2: right.y,
        outcome,
        highlighted: highlightLinkIds.length > 0 && hl,
      })
    }
    setEdges(next)
  }, [page.links, highlightLinkIds])

  useEffect(() => {
    redraw()
    const board = boardRef.current
    if (!board) return
    const ro = new ResizeObserver(() => redraw())
    ro.observe(board)
    return () => ro.disconnect()
  }, [redraw])

  const foundSentence = useMemo(() => {
    const f = page.found_via
    if (f.kind === 'account' && f.id) {
      const holders = f.holders ?? 0
      const fit = f.fit ?? 0
      if (holders > 1) {
        return `Found via joint account ${f.id} · ${holders} holders, ${fit} fits the screened details`
      }
      return `Found via account ${f.id}`
    }
    if (f.kind === 'login' && f.id) return `Found via login ${f.id}`
    if (f.kind === 'email' && f.id) return `Found via email`
    if (f.kind === 'search') return 'No link: matched on name, DOB, country, city'
    return 'No record fits: decided on screened details only'
  }, [page.found_via])

  const person = page.persons[0]
  const profile = page.profile

  return (
    <section className="min-w-0 flex-1 rounded-[20px] bg-plot p-5">
      <motion.div
        initial={reduced ? false : { opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <h2 className="text-[22px] font-normal tracking-[-0.4px] text-ink">
          Identity Graph
        </h2>
        <div className="mt-4 grid grid-cols-2 gap-4 text-[11px] font-medium uppercase tracking-[0.06em] text-ink-3">
          <div>
            <p>Our customer</p>
            <p className="mt-1 text-[12px] font-normal normal-case tracking-normal text-ink-2">
              {foundSentence}
            </p>
          </div>
          <p className="text-right">Watchlist profile</p>
        </div>
      </motion.div>

      <div
        ref={boardRef}
        className="relative mt-4 h-[560px] w-full overflow-hidden rounded-[20px] bg-plot"
      >
        <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden>
          {edges.map((e) => {
            const { stroke, dash } = linkStroke(e.outcome)
            const dim =
              highlightLinkIds.length > 0 && !e.highlighted ? 0.2 : 1
            return (
              <g key={e.key} opacity={dim}>
                <motion.path
                  d={bezierPath(e.x1, e.y1, e.x2, e.y2)}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={2}
                  strokeDasharray={dash}
                  initial={reduced ? false : { pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: reduced ? 0 : 0.45, ease: 'easeOut' }}
                />
                <circle cx={e.x2} cy={e.y2} r={3.5} fill={stroke} />
              </g>
            )
          })}
        </svg>

        <div className="absolute left-6 top-6 w-[280px] space-y-3">
          {person && (
            <div className="rounded-[14px] border border-white/80 bg-white/75 p-3 backdrop-blur-[6px]">
              <div className="flex items-center gap-2">
                <GroupHandle kind="person" />
                <p className="text-[13px] font-semibold">{person.label}</p>
              </div>
              <div
                ref={(el) => {
                  if (el) setNodeRef(person.name.id, el)
                }}
                className="mt-2 rounded-[10px] bg-surface px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <CountryFlag iso2={person.name.country_iso2} />
                  <p className="text-[13px] font-medium text-ink">{person.name.display}</p>
                </div>
                <p className="mt-0.5 font-mono text-[11.5px] text-ink-3">
                  {person.records.length > 0 ? person.records.join(' · ') : person.name.id}
                </p>
                {person.merged_by ? (
                  <p className="mt-1 text-[12px] text-ink-3">{person.merged_by}</p>
                ) : null}
              </div>
              {person.verified && (
                <div className="mt-2 rounded-[14px] border border-white/80 bg-white/60 p-2 backdrop-blur-[6px]">
                  <div className="flex items-center gap-2">
                    <GroupHandle kind="verified" />
                    <ProviderBadge provider={person.verified.provider} />
                    <span className="text-[11.5px] text-ink-3">{person.verified.date}</span>
                  </div>
                  <div className="mt-2 space-y-2">
                    {person.verified.facts.map((f) => (
                      <div
                        key={f.id}
                        ref={(el) => {
                          if (el) setNodeRef(f.id, el)
                        }}
                        className={`rounded-[10px] bg-surface px-3 py-2 ${
                          f.certain === false
                            ? 'outline outline-[1.5px] outline-caution'
                            : ''
                        }`}
                      >
                        <p className="text-[11px] text-ink-3">{f.line ?? 'Fact'}</p>
                        <div className="flex items-center gap-2">
                          {f.country_iso2 && <CountryFlag iso2={f.country_iso2} size={16} />}
                          <p className="text-[13px] font-medium">{f.display}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {page.ghosts.map((g, i) => (
            <motion.div
              key={g.label + i}
              className="rounded-[14px] border border-white/60 bg-white/50 p-3 opacity-60 backdrop-blur-[6px]"
              initial={reduced ? false : { opacity: 0 }}
              animate={{ opacity: 0.6 }}
            >
              <div className="flex items-center gap-2">
                <GroupHandle kind="ghost" />
                <p className="text-[13px] font-semibold">{g.label}</p>
              </div>
              <p className="mt-1 text-[12px] text-ink-3">{g.line}</p>
            </motion.div>
          ))}
        </div>

        <div className="absolute right-6 top-6 w-[290px] space-y-3">
          <div className="rounded-[14px] border border-white/80 bg-white/75 p-3 backdrop-blur-[6px]">
            <div className="flex items-center gap-2">
              <GroupHandle kind="profile" />
              <p className="text-[13px] font-semibold">{profile.category}</p>
            </div>
            <div
              ref={(el) => {
                if (el) setNodeRef(profile.name.id, el)
              }}
              className="mt-2 rounded-[10px] bg-surface px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <CountryFlag iso2={profile.name.country_iso2} />
                <p className="text-[13px] font-medium text-ink">{profile.name.display}</p>
              </div>
              <p className="mt-0.5 font-mono text-[11.5px] text-ink-3">{profile.name.id}</p>
            </div>
            <div className="mt-2 space-y-2">
              {profile.facts.map((f) => {
                const missing = f.display === '—'
                return (
                  <div
                    key={f.id}
                    ref={(el) => {
                      if (el) setNodeRef(f.id, el)
                    }}
                    className={`rounded-[10px] bg-surface px-3 py-2 ${
                      missing ? 'border border-dashed border-ink-4' : ''
                    }`}
                  >
                    <p className="text-[11px] text-ink-3">{f.line ?? 'Fact'}</p>
                    <div className="flex items-center gap-2">
                      {f.country_iso2 && <CountryFlag iso2={f.country_iso2} size={16} />}
                      <p className="text-[13px] font-medium">{f.display}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {profile.sources.map((s) => (
            <div
              key={s.id}
              className="rounded-[14px] border border-white/80 bg-white/75 p-3 backdrop-blur-[6px]"
            >
              <div className="flex items-center gap-2">
                <GroupHandle kind="source" />
                <p className="text-[13px] font-semibold text-source">{s.label}</p>
              </div>
              <motion.div
                ref={(el) => {
                  if (el) setNodeRef(s.id, el)
                }}
                className="mt-2 rounded-[10px] bg-source-soft px-3 py-2"
                initial={reduced ? false : { opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <p className="text-[12px] text-ink-2">{s.note}</p>
                <p className="mt-1 font-mono text-[11.5px] text-ink-3">{s.id}</p>
              </motion.div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}