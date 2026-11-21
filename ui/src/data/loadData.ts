import { useCallback, useEffect, useState } from 'react'
import type { CasePage, QueueRow, RunSummary } from '../types/case'
import { casesByHitId, queueRows } from './syntheticSample'

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url)
    if (!res.ok) return null
    return (await res.json()) as T
  } catch {
    return null
  }
}

export async function loadQueue(): Promise<QueueRow[]> {
  const live = await fetchJson<QueueRow[]>('/data/queue.json')
  return live ?? queueRows
}

export async function loadRunSummary(): Promise<RunSummary | null> {
  const live = await fetchJson<RunSummary>('/data/summary.json')
  return live
}

export async function loadCase(hitId: string): Promise<CasePage | null> {
  const live = await fetchJson<CasePage>(`/data/cases/${encodeURIComponent(hitId)}.json`)
  return live ?? casesByHitId[hitId] ?? null
}

export function useQueue() {
  const [rows, setRows] = useState<QueueRow[]>(queueRows)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    loadQueue().then((data) => {
      if (!cancelled) {
        setRows(data)
        setLoading(false)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  return { rows, loading }
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