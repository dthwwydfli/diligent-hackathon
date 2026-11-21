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
      return { stroke: '#E2D400', dash: '6 4' }
    case 'source':
      return { stroke: 'var(--color-source)', dash: '4 3' }
  }
}