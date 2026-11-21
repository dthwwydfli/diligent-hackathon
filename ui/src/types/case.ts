export type Decision = 'DIFFERENT_ENTITY' | 'SAME_ENTITY' | 'REVIEW'
export type LinkOutcome = 'match' | 'clear' | 'review' | 'source'

export interface CasePage {
  hit_id: string
  alert_id: string
  screened_at: string
  hit_index: [number, number]
  customer_name: string
  customer_country_iso2?: string | null
  found_via: {
    kind: 'account' | 'login' | 'email' | 'search' | 'none'
    id?: string | null
    holders?: number
    fit?: number
  }
  persons: PersonBlock[]
  ghosts: GhostBlock[]
  profile: ProfileBlock
  links: [string, string, LinkOutcome][]
  ladder: LadderRow[]
  decision: Decision
  reason_code: string
  reason: string
  status: { kind: 'certain' | 'blocked' | 'none'; text: string }
  missing: { side: 'profile' | 'customer'; display: string }[]
  output_line: Record<string, unknown>
}

export interface PersonBlock {
  label: string
  fits: boolean
  records: string[]
  merged_by?: string | null
  name: { id: string; display: string; country_iso2?: string | null }
  verified?: {
    provider: string
    source: string
    date: string
    facts: FactNode[]
  } | null
}

export interface FactNode {
  id: string
  display: string
  line?: string
  certain?: boolean
  country_iso2?: string | null
  source?: string | null
}

export interface GhostBlock {
  label: string
  line: string
}

export interface ProfileBlock {
  category: string
  score?: number | null
  name: { id: string; display: string; country_iso2?: string | null }
  facts: FactNode[]
  sources: { id: string; label: string; note: string; supports: string }[]
}

export interface LadderRow {
  check: string
  phrase: string
  outcome: 'agrees' | 'contradicts' | 'unknown' | 'result'
  result_chip?: 'Same' | 'Cleared' | 'Review'
  link_ids?: string[]
}

export interface QueueRow {
  hit_id: string
  alert_id: string
  customer_name: string
  customer_country_iso2?: string | null
  listed_name: string
  listed_country_iso2?: string | null
  category: string
  decision: Decision
  reason_code: string
}

export interface RunSummary {
  hits: number
  unsafe_practice: number
  practice_labels: number
  identical_runs: number
  runs: number
  seconds: number
  cost_usd: number
  split: Record<Decision, number>
}