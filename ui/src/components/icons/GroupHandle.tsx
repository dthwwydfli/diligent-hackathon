import {
  FlagGlassIcon,
  SearchGlassIcon,
  ShieldCheckGlassIcon,
  UserGlassIcon,
  UserXGlassIcon,
} from '@thesvg/ui-react'

export type GroupHandleKind = 'person' | 'verified' | 'profile' | 'source' | 'ghost'

interface GroupHandleProps {
  kind: GroupHandleKind
  size?: number
  className?: string
}

export function GroupHandle({ kind, size = 22, className }: GroupHandleProps) {
  const props = { width: size, height: size, className, 'aria-hidden': true as const }

  switch (kind) {
    case 'person':
      return <UserGlassIcon {...props} />
    case 'verified':
      return <ShieldCheckGlassIcon {...props} />
    case 'profile':
      return <FlagGlassIcon {...props} />
    case 'source':
      return <SearchGlassIcon {...props} />
    case 'ghost':
      return <UserXGlassIcon {...props} />
    default:
      return (
        <span
          className={`inline-flex h-[22px] w-[22px] items-center justify-center rounded-full bg-surface text-[10px] font-semibold text-ink-3 ${className ?? ''}`}
          aria-hidden
        >
          ?
        </span>
      )
  }
}