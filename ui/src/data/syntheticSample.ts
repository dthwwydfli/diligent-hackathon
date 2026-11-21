import type { CasePage, Decision, QueueRow, RunSummary } from '../types/case'

export const runSummary: RunSummary = {
  hits: 3,
  unsafe_practice: 0,
  practice_labels: 3,
  identical_runs: 5,
  runs: 5,
  seconds: 12,
  cost_usd: 0,
  split: {
    SAME_ENTITY: 1,
    DIFFERENT_ENTITY: 1,
    REVIEW: 1,
  },
}

export const queueRows: QueueRow[] = [
  {
    hit_id: 'H-000003',
    alert_id: 'A-000001',
    customer_name: 'Sam Chen',
    customer_country_iso2: 'gb',
    listed_name: 'Sam Chen',
    listed_country_iso2: 'gb',
    category: 'PEP',
    decision: 'REVIEW',
    reason_code: 'INSUFFICIENT_DATA',
  },
  {
    hit_id: 'H-000001',
    alert_id: 'A-000001',
    customer_name: 'Alex Rivera',
    customer_country_iso2: 'br',
    listed_name: 'Alex Rivera',
    listed_country_iso2: 'br',
    category: 'Sanctions',
    decision: 'SAME_ENTITY',
    reason_code: 'NAME_DOB_LOCATION_MATCH',
  },
  {
    hit_id: 'H-000002',
    alert_id: 'A-000001',
    customer_name: 'Jordan Blake',
    customer_country_iso2: 'us',
    listed_name: 'Jordan Blake',
    listed_country_iso2: 'us',
    category: 'Adverse media',
    decision: 'DIFFERENT_ENTITY',
    reason_code: 'DOB_MISMATCH',
  },
]

const sameEntityCase: CasePage = {
  hit_id: 'H-000001',
  alert_id: 'A-000001',
  screened_at: '2026-03-15',
  hit_index: [1, 3],
  customer_name: 'Alex Rivera',
  customer_country_iso2: 'br',
  found_via: { kind: 'account', id: 'ACC-000042', holders: 1 },
  persons: [
    {
      label: 'Person',
      fits: true,
      records: ['CUS-000001'],
      name: { id: 'N-CUS-001', display: 'Alex Rivera', country_iso2: 'br' },
      verified: {
        provider: 'onfido',
        source: 'KYC-000011',
        date: '2025-11-02',
        facts: [
          { id: 'F-DOB-C', display: '1990-04-12', line: 'Birth date' },
          { id: 'F-CTY-C', display: 'Brazil', country_iso2: 'br', line: 'Country' },
        ],
      },
    },
  ],
  ghosts: [],
  profile: {
    category: 'Sanctions',
    score: 98,
    name: { id: 'N-WL-001', display: 'Alex Rivera', country_iso2: 'br' },
    facts: [
      { id: 'F-DOB-P', display: '1990-04-12', line: 'Birth date' },
      { id: 'F-CTY-P', display: 'Brazil', country_iso2: 'br', line: 'Country' },
    ],
    sources: [
      {
        id: 'SR-000201',
        label: 'Open sanctions feed',
        note: 'Listed entity record',
        supports: 'N-WL-001',
      },
    ],
  },
  links: [
    ['N-CUS-001', 'N-WL-001', 'match'],
    ['F-DOB-C', 'F-DOB-P', 'match'],
    ['F-CTY-C', 'F-CTY-P', 'match'],
    ['SR-000201', 'N-WL-001', 'source'],
  ],
  ladder: [
    {
      check: 'Type',
      phrase: 'Individual ↔ Individual',
      outcome: 'agrees',
      link_ids: ['N-CUS-001', 'N-WL-001'],
    },
    {
      check: 'Time',
      phrase: 'Screened on same day as alert',
      outcome: 'agrees',
    },
    {
      check: 'Birth date',
      phrase: '1990-04-12 matches on both sides',
      outcome: 'agrees',
      link_ids: ['F-DOB-C', 'F-DOB-P'],
    },
    {
      check: 'Country',
      phrase: 'Brazil (BR) on both sides',
      outcome: 'agrees',
      link_ids: ['F-CTY-C', 'F-CTY-P'],
    },
    {
      check: 'Name',
      phrase: 'Alex Rivera matches exactly',
      outcome: 'agrees',
      link_ids: ['N-CUS-001', 'N-WL-001'],
    },
    {
      check: 'Result',
      phrase: 'Same person — all decisive checks agree',
      outcome: 'result',
      result_chip: 'Same',
    },
  ],
  decision: 'SAME_ENTITY',
  reason_code: 'NAME_DOB_LOCATION_MATCH',
  reason: 'Name, date of birth, and country all agree between customer and watchlist profile.',
  status: { kind: 'certain', text: 'Every fact used is certain' },
  missing: [],
  output_line: {
    hit_id: 'H-000001',
    decision: 'SAME_ENTITY',
    reason_code: 'NAME_DOB_LOCATION_MATCH',
  },
}

const differentEntityCase: CasePage = {
  hit_id: 'H-000002',
  alert_id: 'A-000001',
  screened_at: '2026-03-15',
  hit_index: [2, 3],
  customer_name: 'Jordan Blake',
  customer_country_iso2: 'us',
  found_via: { kind: 'login', id: 'ACC-000088' },
  persons: [
    {
      label: 'Person',
      fits: true,
      records: ['CUS-000002'],
      name: { id: 'N-CUS-002', display: 'Jordan Blake', country_iso2: 'us' },
      verified: {
        provider: 'jumio',
        source: 'KYC-000022',
        date: '2025-08-14',
        facts: [
          { id: 'F-DOB-C2', display: '1988-07-03', line: 'Birth date' },
          { id: 'F-CTY-C2', display: 'United States', country_iso2: 'us', line: 'Country' },
        ],
      },
    },
  ],
  ghosts: [],
  profile: {
    category: 'Adverse media',
    score: 72,
    name: { id: 'N-WL-002', display: 'Jordan Blake', country_iso2: 'us' },
    facts: [
      { id: 'F-DOB-P2', display: '1971-01-19', line: 'Birth date' },
      { id: 'F-CTY-P2', display: 'United States', country_iso2: 'us', line: 'Country' },
    ],
    sources: [
      {
        id: 'SR-000302',
        label: 'Media archive',
        note: 'Press mention',
        supports: 'N-WL-002',
      },
    ],
  },
  links: [
    ['N-CUS-002', 'N-WL-002', 'match'],
    ['F-DOB-C2', 'F-DOB-P2', 'clear'],
    ['F-CTY-C2', 'F-CTY-P2', 'match'],
    ['SR-000302', 'N-WL-002', 'source'],
  ],
  ladder: [
    {
      check: 'Type',
      phrase: 'Individual ↔ Individual',
      outcome: 'agrees',
      link_ids: ['N-CUS-002', 'N-WL-002'],
    },
    { check: 'Time', phrase: 'Alert within screening window', outcome: 'agrees' },
    {
      check: 'Birth date',
      phrase: '1988-07-03 vs 1971-01-19 — contradicts',
      outcome: 'contradicts',
      link_ids: ['F-DOB-C2', 'F-DOB-P2'],
    },
    {
      check: 'Country',
      phrase: 'United States on both sides',
      outcome: 'agrees',
      link_ids: ['F-CTY-C2', 'F-CTY-P2'],
    },
    {
      check: 'Name',
      phrase: 'Jordan Blake — same spelling',
      outcome: 'agrees',
      link_ids: ['N-CUS-002', 'N-WL-002'],
    },
    {
      check: 'Result',
      phrase: 'Different person — birth date contradicts',
      outcome: 'result',
      result_chip: 'Cleared',
    },
  ],
  decision: 'DIFFERENT_ENTITY',
  reason_code: 'DOB_MISMATCH',
  reason: 'Date of birth on the customer record contradicts the watchlist profile.',
  status: { kind: 'certain', text: 'Every fact used is certain' },
  missing: [],
  output_line: {
    hit_id: 'H-000002',
    decision: 'DIFFERENT_ENTITY',
    reason_code: 'DOB_MISMATCH',
  },
}

const reviewCase: CasePage = {
  hit_id: 'H-000003',
  alert_id: 'A-000001',
  screened_at: '2026-03-15',
  hit_index: [3, 3],
  customer_name: 'Sam Chen',
  customer_country_iso2: 'gb',
  found_via: { kind: 'email', id: 'NOTE-000055' },
  persons: [
    {
      label: 'Person',
      fits: true,
      records: ['CUS-000003'],
      name: { id: 'N-CUS-003', display: 'Sam Chen', country_iso2: 'gb' },
      verified: {
        provider: 'sumsub',
        source: 'KYC-000033',
        date: '2026-01-09',
        facts: [
          { id: 'F-DOB-C3', display: '1995-12-01', line: 'Birth date' },
          { id: 'F-CTY-C3', display: 'United Kingdom', country_iso2: 'gb', line: 'Country' },
        ],
      },
    },
  ],
  ghosts: [{ label: 'Birth date', line: 'Not found on watchlist profile' }],
  profile: {
    category: 'PEP',
    score: 61,
    name: { id: 'N-WL-003', display: 'Sam Chen', country_iso2: 'gb' },
    facts: [
      { id: 'F-DOB-MISS', display: '—', line: 'Birth date' },
      { id: 'F-CTY-P3', display: 'United Kingdom', country_iso2: 'gb', line: 'Country' },
    ],
    sources: [
      {
        id: 'SR-000401',
        label: 'PEP registry',
        note: 'Domestic listing',
        supports: 'N-WL-003',
      },
    ],
  },
  links: [
    ['N-CUS-003', 'N-WL-003', 'match'],
    ['F-DOB-C3', 'F-DOB-MISS', 'review'],
    ['F-CTY-C3', 'F-CTY-P3', 'match'],
    ['SR-000401', 'N-WL-003', 'source'],
  ],
  ladder: [
    {
      check: 'Type',
      phrase: 'Individual ↔ Individual',
      outcome: 'agrees',
      link_ids: ['N-CUS-003', 'N-WL-003'],
    },
    { check: 'Time', phrase: 'Same screening batch', outcome: 'agrees' },
    {
      check: 'Birth date',
      phrase: 'Customer DOB present; profile DOB missing',
      outcome: 'unknown',
      link_ids: ['F-DOB-C3', 'F-DOB-MISS'],
    },
    {
      check: 'Country',
      phrase: 'United Kingdom on both sides',
      outcome: 'agrees',
      link_ids: ['F-CTY-C3', 'F-CTY-P3'],
    },
    {
      check: 'Name',
      phrase: 'Sam Chen matches',
      outcome: 'agrees',
      link_ids: ['N-CUS-003', 'N-WL-003'],
    },
    {
      check: 'Result',
      phrase: 'Needs review — birth date unknown on profile',
      outcome: 'result',
      result_chip: 'Review',
    },
  ],
  decision: 'REVIEW',
  reason_code: 'INSUFFICIENT_DATA',
  reason: 'Watchlist profile has no date of birth; cannot confirm or clear automatically.',
  status: { kind: 'none', text: '' },
  missing: [{ side: 'profile', display: 'No birth date found' }],
  output_line: {
    hit_id: 'H-000003',
    decision: 'REVIEW',
    reason_code: 'INSUFFICIENT_DATA',
  },
}

export const casesByHitId: Record<string, CasePage> = {
  'H-000001': sameEntityCase,
  'H-000002': differentEntityCase,
  'H-000003': reviewCase,
}

export function decisionFilterKey(d: Decision): 'Same' | 'Cleared' | 'Review' {
  switch (d) {
    case 'SAME_ENTITY':
      return 'Same'
    case 'DIFFERENT_ENTITY':
      return 'Cleared'
    case 'REVIEW':
      return 'Review'
  }
}