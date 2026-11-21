import type { Decision, LinkOutcome } from '../types/case'

export function verdictTitle(decision: Decision): string {
  switch (decision) {
    case 'DIFFERENT_ENTITY':
      return 'Different person'
    case 'SAME_ENTITY':
      return 'Same person'
    case 'REVIEW':
      return 'Needs review'
  }
}

export function decisionChipLabel(decision: Decision): string {
  switch (decision) {
    case 'DIFFERENT_ENTITY':
      return 'Cleared'
    case 'SAME_ENTITY':
      return 'Same'
    case 'REVIEW':
      return 'Review'
  }
}

export function verdictPanelClass(decision: Decision): string {
  switch (decision) {
    case 'DIFFERENT_ENTITY':
      return 'bg-clear-soft text-clear-ink'
    case 'SAME_ENTITY':
      return 'bg-match-soft text-match-ink'
    case 'REVIEW':
      return 'bg-review-soft text-review-ink'
  }
}

export function strongChipClass(decision: Decision): string {
  switch (decision) {
    case 'DIFFERENT_ENTITY':
      return 'bg-clear text-clear-ink'
    case 'SAME_ENTITY':
      return 'bg-match text-white'
    case 'REVIEW':
      return 'bg-review text-review-ink'
  }
}

export function linkStroke(outcome: LinkOutcome): { stroke: string; dash?: string } {
  switch (outcome) {
    case 'match':
      return { stroke: 'var(--color-match)' }
    case 'clear':
      return { stroke: 'var(--color-clear)' }
    case 'review':
      return { stroke: 'var(--color-review)', dash: '6 4' }
    case 'source':
      return { stroke: 'var(--color-source)', dash: '4 3' }
  }
}
// Reason codes arrive as SCREAMING_SNAKE from the engine; DOB stays an acronym.
export function reasonLabel(code: string): string {
  const words = code.toLowerCase().split('_').map((w) => (w === 'dob' ? 'DOB' : w))
  const text = words.join(' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export const decisionColorVar: Record<Decision, string> = {
  DIFFERENT_ENTITY: 'var(--color-clear)',
  SAME_ENTITY: 'var(--color-match)',
  REVIEW: 'var(--color-review)',
}
