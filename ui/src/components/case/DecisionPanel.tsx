import { motion } from 'motion/react'
import { useState } from 'react'
import dotAnimation from '../../assets/lottie/dot.json'
import type { CasePage, LadderRow } from '../../types/case'
import {
  strongChipClass,
  verdictPanelClass,
  verdictTitle,
} from '../../lib/decisionStyles'
import { LottieBadge } from '../motion/LottieBadge'
import { usePrefersReducedMotion } from '../motion/usePrefersReducedMotion'

interface DecisionPanelProps {
  page: CasePage
  highlightLinkIds: string[]
  onHoverLinks: (ids: string[]) => void
}

function outcomeLabel(row: LadderRow): string {
  if (row.outcome === 'agrees') return 'Agrees'
  if (row.outcome === 'contradicts') return 'Contradicts'
  if (row.outcome === 'unknown') return 'Unknown'
  return ''
}

export function DecisionPanel({ page, highlightLinkIds, onHoverLinks }: DecisionPanelProps) {
  const reduced = usePrefersReducedMotion()
  const [_highlight, setHighlight] = useState<string[]>(highlightLinkIds)

  return (
    <aside className="w-[360px] shrink-0 rounded-[20px] bg-surface p-5">
      <motion.div
        initial={reduced ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className={`rounded-[14px] p-4 ${verdictPanelClass(page.decision)}`}
      >
        <p className="text-[11px] font-medium uppercase tracking-[0.06em] opacity-80">
          Decision
        </p>
        <h2 className="mt-1 text-[22px] font-medium tracking-[-0.4px]">
          {verdictTitle(page.decision)}
        </h2>
        <p className="mt-2 font-mono text-[11.5px] opacity-70">{page.reason_code}</p>
        <p className="mt-2 text-[13px] leading-snug">{page.reason}</p>
        {page.status.kind !== 'none' && page.status.text && (
          <motion.div
            className="mt-3 flex items-center gap-2 text-[12px]"
            initial={reduced ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <LottieBadge animationData={dotAnimation} className="h-3 w-3" />
            <span>{page.status.text}</span>
          </motion.div>
        )}
      </motion.div>

      <h3 className="mt-6 text-[18px] font-normal tracking-[-0.3px] text-ink">
        How it was decided
      </h3>

      <ul className="mt-3 space-y-2">
        {page.ladder.map((row, i) => {
          const isResult = row.outcome === 'result'
          return (
            <motion.li
              key={`${row.check}-${i}`}
              initial={reduced ? false : { opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: reduced ? 0 : i * 0.04 }}
              onMouseEnter={() => {
                const ids = row.link_ids ?? []
                setHighlight(ids)
                onHoverLinks(ids)
              }}
              onMouseLeave={() => {
                setHighlight([])
                onHoverLinks([])
              }}
              className={`flex items-start justify-between gap-3 rounded-[10px] px-3 py-2.5 text-[13px] ${
                isResult
                  ? 'border border-ink bg-surface'
                  : 'bg-plot/60 hover:bg-plot'
              }`}
            >
              <div className="min-w-0">
                <p className="font-semibold text-ink">{row.check}</p>
                <p className="mt-0.5 truncate text-ink-2">{row.phrase}</p>
              </div>
              {isResult && row.result_chip ? (
                <span
                  className={`shrink-0 rounded-[6px] px-2 py-0.5 text-[11.5px] font-semibold ${strongChipClass(page.decision)}`}
                >
                  {row.result_chip}
                </span>
              ) : (
                <span className="shrink-0 text-[11.5px] font-medium text-ink-3">
                  {outcomeLabel(row)}
                </span>
              )}
            </motion.li>
          )
        })}
      </ul>
    </aside>
  )
}