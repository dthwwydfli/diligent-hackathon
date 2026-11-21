import { Check, ChevronLeft, ChevronRight, Copy } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { loadQueue, useCase } from '../data/loadData'
import type { QueueRow } from '../types/case'
import { DecisionPanel } from '../components/case/DecisionPanel'
import { IdentityGraph } from '../components/case/IdentityGraph'
import { CountryFlag } from '../components/icons/CountryFlag'
import { AppShell } from '../components/layout/AppShell'

export function CasePage() {
  const { hitId } = useParams<{ hitId: string }>()
  const { page, loading } = useCase(hitId)
  const navigate = useNavigate()
  const [highlightLinkIds, setHighlightLinkIds] = useState<string[]>([])
  const [copied, setCopied] = useState(false)
  const [queue, setQueue] = useState<QueueRow[]>([])

  useEffect(() => {
    void loadQueue().then(setQueue)
  }, [])

  const pager = useMemo(() => {
    if (!page) return { index: 1, total: 1, prev: null as string | null, next: null as string | null }
    const siblings = queue
      .filter((row) => row.alert_id === page.alert_id)
      .map((row) => row.hit_id)
    const ids = siblings.length > 0 ? siblings : [page.hit_id]
    const idx = Math.max(0, ids.indexOf(page.hit_id))
    return {
      index: page.hit_index[0] || idx + 1,
      total: page.hit_index[1] || ids.length,
      prev: idx > 0 ? ids[idx - 1] : null,
      next: idx >= 0 && idx < ids.length - 1 ? ids[idx + 1] : null,
    }
  }, [page, queue])

  if (loading) {
    return (
      <AppShell>
        <p className="text-ink-3">Loading case…</p>
      </AppShell>
    )
  }

  if (!page) {
    return (
      <AppShell>
        <p className="text-ink-3">Case not found.</p>
        <Link to="/" className="text-source">
          Back to queue
        </Link>
      </AppShell>
    )
  }

  const copyResult = async () => {
    await navigator.clipboard.writeText(JSON.stringify(page.output_line))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <AppShell>
      <header className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Link
            to="/"
            className="flex h-[34px] w-[34px] items-center justify-center rounded-full bg-surface text-ink"
            aria-label="Back to queue"
          >
            <ChevronLeft size={18} />
          </Link>
          <div>
            <h1 className="flex items-center gap-2 text-[28px] font-normal tracking-[-0.6px] text-ink">
              <CountryFlag iso2={page.customer_country_iso2} size={22} />
              {page.customer_name}
            </h1>
            <p className="mt-1 font-mono text-[11.5px] text-ink-3">
              Alert {page.alert_id} · Hit {page.hit_id} · screened {page.screened_at}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <p className="text-[12.5px] text-ink-2">
            Hit {pager.index} of {pager.total} in alert
          </p>
          <button
            type="button"
            disabled={!pager.prev}
            onClick={() => pager.prev && navigate(`/case/${pager.prev}`)}
            className="flex h-[30px] w-[30px] items-center justify-center rounded-full bg-surface text-ink disabled:opacity-45"
            aria-label="Previous hit in alert"
          >
            <ChevronLeft size={14} />
          </button>
          <button
            type="button"
            disabled={!pager.next}
            onClick={() => pager.next && navigate(`/case/${pager.next}`)}
            className="flex h-[30px] w-[30px] items-center justify-center rounded-full bg-surface text-ink disabled:opacity-45"
            aria-label="Next hit in alert"
          >
            <ChevronRight size={14} />
          </button>
          <button
            type="button"
            onClick={() => void copyResult()}
            className="ml-3 inline-flex h-[34px] items-center gap-2 rounded-[10px] bg-ink px-4 text-[13px] font-medium text-white"
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
            Copy result
          </button>
        </div>
      </header>

      <div className="flex gap-3">
        <IdentityGraph page={page} highlightLinkIds={highlightLinkIds} />
        <DecisionPanel
          page={page}
          highlightLinkIds={highlightLinkIds}
          onHoverLinks={setHighlightLinkIds}
        />
      </div>
    </AppShell>
  )
}