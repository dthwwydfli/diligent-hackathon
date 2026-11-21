import { ShieldGlassIcon } from '@thesvg/ui-react'

interface ProviderBadgeProps {
  provider?: string | null
  size?: number
  className?: string
}

// known brands not in bundle yet; shield still reads as KYC
export function ProviderBadge({ provider, size = 20, className }: ProviderBadgeProps) {
  const name = provider?.toLowerCase() ?? ''
  const label = name ? name.charAt(0).toUpperCase() + name.slice(1) : 'KYC'

  return (
    <span className={`inline-flex items-center gap-1 ${className ?? ''}`} title={label}>
      <ShieldGlassIcon width={size} height={size} aria-hidden />
      <span className="sr-only">{label}</span>
    </span>
  )
}