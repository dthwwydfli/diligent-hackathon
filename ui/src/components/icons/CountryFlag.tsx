import type { ComponentType, SVGProps } from 'react'
import { useState } from 'react'
import { FlagGlassIcon } from '@thesvg/ui-react'
import { FlagBr } from '@thesvg/flags/react/br'
import { FlagDe } from '@thesvg/flags/react/de'
import { FlagFr } from '@thesvg/flags/react/fr'
import { FlagGb } from '@thesvg/flags/react/gb'
import { FlagUs } from '@thesvg/flags/react/us'

type FlagComp = ComponentType<
  SVGProps<SVGSVGElement> & { variant?: 'circle' | '4x3' | 'square'; size?: number }
>

const BUNDLED: Record<string, FlagComp> = {
  br: FlagBr,
  us: FlagUs,
  fr: FlagFr,
  de: FlagDe,
  gb: FlagGb,
}

interface CountryFlagProps {
  iso2?: string | null
  size?: number
  className?: string
}

function MissingFlag({ size = 18, className }: { size?: number; className?: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-full bg-plot text-ink-4 ${className ?? ''}`}
      style={{ width: size, height: size }}
      title="No country on record"
      aria-hidden
    >
      <FlagGlassIcon width={Math.max(12, size - 4)} height={Math.max(12, size - 4)} />
    </span>
  )
}

function RemoteFlag({
  code,
  size,
  className,
}: {
  code: string
  size: number
  className?: string
}) {
  const [failed, setFailed] = useState(false)
  if (failed) return <MissingFlag size={size} className={className} />
  return (
    <img
      src={`https://thesvg.org/icons/flag-${code}/circle.svg`}
      alt=""
      width={size}
      height={size}
      className={className}
      aria-hidden
      loading="lazy"
      onError={() => setFailed(true)}
    />
  )
}

export function CountryFlag({ iso2, size = 18, className }: CountryFlagProps) {
  if (!iso2) return <MissingFlag size={size} className={className} />
  const code = iso2.toLowerCase()
  const Bundled = BUNDLED[code]

  if (Bundled) {
    return (
      <Bundled variant="circle" size={size} className={className} aria-hidden />
    )
  }

  return <RemoteFlag code={code} size={size} className={className} />
}
