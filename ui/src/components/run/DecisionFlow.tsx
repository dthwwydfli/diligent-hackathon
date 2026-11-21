import { motion } from 'motion/react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { decisionChipLabel, decisionColorVar, reasonLabel } from '../../lib/decisionStyles'
import type { Decision, QueueRow } from '../../types/case'

const ORDER: Decision[] = ['DIFFERENT_ENTITY', 'SAME_ENTITY', 'REVIEW']
// Reasons this rare get folded into "Other" so their labels do not collide.
const MIN_REASON = 12
const W = 1000
const NODE_W = 10
const GAP = 14
const SLOT = 22
const COL = { all: 0, decision: 360, reason: 700 }

interface Node {
  key: string
  label: string
  count: number
  decision?: Decision
  y: number
  h: number
}

// Labels sit over ribbons; a surface-coloured outline keeps them readable.
const halo = { stroke: 'var(--color-surface)', strokeWidth: 4, paintOrder: 'stroke' as const, strokeLinejoin: 'round' as const }

function band(x0: number, y0: number, x1: number, y1: number, h: number): string {
  const xm = (x0 + x1) / 2
  return `M${x0},${y0} C${xm},${y0} ${xm},${y1} ${x1},${y1} L${x1},${y1 + h} C${xm},${y1 + h} ${xm},${y0 + h} ${x0},${y0 + h} Z`
}

// Three columns: every hit, the decision it got, and the reason the engine gave.
export function DecisionFlow({ rows, reduced }: { rows: QueueRow[]; reduced: boolean }) {
  const navigate = useNavigate()
  const [focus, setFocus] = useState<Decision | null>(null)

  const layout = useMemo(() => {
    const reasons: { decision: Decision; code: string; count: number }[] = []
    for (const d of ORDER) {
      const counts = new Map<string, number>()
      for (const r of rows) if (r.decision === d) counts.set(r.reason_code, (counts.get(r.reason_code) ?? 0) + 1)
      let other = 0
      for (const [code, count] of [...counts].sort((a, b) => b[1] - a[1])) {
        if (count < MIN_REASON) other += count
        else reasons.push({ decision: d, code, count })
      }
      if (other) reasons.push({ decision: d, code: 'OTHER', count: other })
    }

    // Reason slots are at least SLOT tall so every label gets its own line.
    const scale = 300 / rows.length
    const reasonNodes: Node[] = []
    let y = 0
    for (const r of reasons) {
      const h = Math.max(r.count * scale, 2)
      const slot = Math.max(h, SLOT)
      reasonNodes.push({
        key: `${r.decision}:${r.code}`,
        label: r.code === 'OTHER' ? 'Other' : reasonLabel(r.code),
        count: r.count,
        decision: r.decision,
        y: y + (slot - h) / 2,
        h,
      })
      y += slot + 4
    }
    const height = y

    const decisionNodes: Node[] = []
    const decisionsH = rows.length * scale + GAP * 2
    y = (height - decisionsH) / 2
    for (const d of ORDER) {
      const count = rows.filter((r) => r.decision === d).length
      decisionNodes.push({ key: d, label: decisionChipLabel(d), count, decision: d, y, h: count * scale })
      y += count * scale + GAP
    }

    const allNode: Node = { key: 'all', label: 'Hits', count: rows.length, y: (height - rows.length * scale) / 2, h: rows.length * scale }
    return { reasonNodes, decisionNodes, allNode, height, scale }
  }, [rows])

  const { reasonNodes, decisionNodes, allNode, height } = layout
  const dim = (d?: Decision) => (focus && d !== focus ? 0.12 : 1)

  let fromAll = allNode.y
  const inner = decisionNodes.map((n) => {
    const path = band(COL.all + NODE_W, fromAll, COL.decision, n.y, n.h)
    fromAll += n.h
    return { n, path }
  })
  const outerFrom = new Map(decisionNodes.map((n) => [n.decision, n.y]))
  const outer = reasonNodes.map((n) => {
    const y0 = outerFrom.get(n.decision!)!
    outerFrom.set(n.decision!, y0 + n.h)
    return { n, path: band(COL.decision + NODE_W, y0, COL.reason, n.y, n.h) }
  })

  return (
    <svg viewBox={`-4 -4 ${W + 8} ${height + 8}`} className="h-full w-full" role="img" aria-label="How every hit was decided, and why">
      <defs>
        {ORDER.map((d) => (
          <linearGradient key={d} id={`flow-${d}`} x1={COL.all} x2={COL.decision} gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="var(--color-ink-4)" stopOpacity="0.35" />
            <stop offset="1" stopColor={decisionColorVar[d]} stopOpacity="0.55" />
          </linearGradient>
        ))}
      </defs>

      {[...inner.map(({ n, path }) => ({ key: `in-${n.key}`, d: n.decision!, path, fill: `url(#flow-${n.decision})` })),
        ...outer.map(({ n, path }) => ({ key: `out-${n.key}`, d: n.decision!, path, fill: decisionColorVar[n.decision!] }))].map((b, i) => (
        <motion.path
          key={b.key}
          d={b.path}
          fill={b.fill}
          fillOpacity={b.key.startsWith('out') ? 0.35 : 1}
          initial={reduced ? false : { opacity: 0 }}
          animate={{ opacity: dim(b.d) }}
          transition={{ duration: 0.5, delay: reduced ? 0 : i * 0.04 }}
          onMouseEnter={() => setFocus(b.d)}
          onMouseLeave={() => setFocus(null)}
        />
      ))}

      <rect x={COL.all} y={allNode.y} width={NODE_W} height={allNode.h} rx={3} fill="var(--color-ink)" />
      <text x={COL.all + NODE_W + 10} y={allNode.y + allNode.h / 2} dominantBaseline="middle" {...halo} className="fill-ink text-[13px] font-semibold">
        {allNode.count} hits
      </text>

      {decisionNodes.map((n) => (
        <g
          key={n.key}
          className="cursor-pointer"
          opacity={dim(n.decision)}
          onMouseEnter={() => setFocus(n.decision!)}
          onMouseLeave={() => setFocus(null)}
          onClick={() => navigate(`/?decision=${n.label}`)}
        >
          <rect x={COL.decision} y={n.y} width={NODE_W} height={n.h} rx={3} fill={decisionColorVar[n.decision!]} />
          <text x={COL.decision + NODE_W + 10} y={n.y + n.h / 2 - 8} dominantBaseline="middle" {...halo} className="fill-ink text-[13px] font-semibold">
            {n.label}
          </text>
          <text x={COL.decision + NODE_W + 10} y={n.y + n.h / 2 + 9} dominantBaseline="middle" {...halo} className="fill-ink-3 text-[12px]">
            {n.count} · {Math.round((n.count / allNode.count) * 100)}%
          </text>
        </g>
      ))}

      {reasonNodes.map((n) => (
        <g key={n.key} opacity={dim(n.decision)}>
          <rect x={COL.reason} y={n.y} width={NODE_W} height={n.h} rx={2} fill={decisionColorVar[n.decision!]} />
          <text x={COL.reason + NODE_W + 10} y={n.y + n.h / 2} dominantBaseline="middle" {...halo} className="fill-ink-2 text-[12px]">
            {n.label} <tspan className="fill-ink-3">{n.count}</tspan>
          </text>
        </g>
      ))}
    </svg>
  )
}
