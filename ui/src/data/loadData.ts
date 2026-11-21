import { useCallback, useEffect, useState } from 'react'
import type { CasePage, QueueRow, RunSummary } from '../types/case'
import { casesByHitId, queueRows } from './syntheticSample'

const isTest = import.meta.env.MODE === 'test'

async function fetchJson<T>(
  url: string,
): Promise<{ data: T | null; reason: 'ok' | 'missing' | 'error' }> {
  try {
    const res = await fetch(url)
    if (res.status === 404) return { data: null, reason: 'missing' }
    if (!res.ok) return { data: null, reason: 'error' }
    return { data: (await res.json()) as T, reason: 'ok' }
  } catch {
    return { data: null, reason: 'error' }
  }
}

// `unreachable` means the fetch itself failed (dev server down), not that the export is missing.
export async function loadQueue(): Promise<{ rows: QueueRow[]; unreachable: boolean }> {
  const { data, reason } = await fetchJson<QueueRow[]>('/data/queue.json')
  if (Array.isArray(data) && data.length > 0) return { rows: data, unreachable: false }
  if (isTest) return { rows: queueRows, unreachable: false }
  return { rows: [], unreachable: reason === 'error' }
}

export async function loadRunSummary(): Promise<RunSummary | null> {
  const { data } = await fetchJson<RunSummary>('/data/summary.json')
  return data
}

export async function loadCase(hitId: string): Promise<CasePage | null> {
  const { data, reason } = await fetchJson<CasePage>(
    `/data/cases/${encodeURIComponent(hitId)}.json`,
  )
  if (data) return data
  if (reason === 'missing' || isTest) return casesByHitId[hitId] ?? null
  return null
}

export function useQueue() {
  const [rows, setRows] = useState<QueueRow[]>([])
  const [loading, setLoading] = useState(true)
  const [live, setLive] = useState(false)
  const [unreachable, setUnreachable] = useState(false)

  useEffect(() => {
    let cancelled = false
    loadQueue().then(({ rows: data, unreachable }) => {
      if (cancelled) return
      setRows(data)
      setUnreachable(unreachable)
      // Sample hit IDs are H-000001…; live export uses real folder IDs.
      setLive(data.length > 0 && !data.every((r) => /^H-00000\d$/.test(r.hit_id)))
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [])

  return { rows, loading, live, unreachable }
}

export function useRunSummary() {
  const [summary, setSummary] = useState<RunSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    loadRunSummary().then((data) => {
      if (!cancelled) {
        setSummary(data)
        setLoading(false)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  return { summary, loading }
}

export function useCase(hitId: string | undefined) {
  const [page, setPage] = useState<CasePage | null>(null)
  const [loading, setLoading] = useState(true)

  const reload = useCallback(() => {
    if (!hitId) {
      setPage(null)
      setLoading(false)
      return
    }
    setLoading(true)
    loadCase(hitId).then((data) => {
      setPage(data)
      setLoading(false)
    })
  }, [hitId])

  useEffect(() => {
    reload()
  }, [reload])

  return { page, loading, reload }
}

export function sortedQueueRows(rows: QueueRow[]): QueueRow[] {
  const order: Record<string, number> = {
    REVIEW: 0,
    SAME_ENTITY: 1,
    DIFFERENT_ENTITY: 2,
  }
  return [...rows].sort((a, b) => {
    const d = order[a.decision] - order[b.decision]
    if (d !== 0) return d
    return a.alert_id.localeCompare(b.alert_id)
  })
}
