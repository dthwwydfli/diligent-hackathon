import type { ComponentType, SVGProps } from 'react'
import { FlagBr } from '@thesvg/flags/react/br'
import { FlagDe } from '@thesvg/flags/react/de'
import { FlagFr } from '@thesvg/flags/react/fr'
import { FlagGb } from '@thesvg/flags/react/gb'
import { FlagUs } from '@thesvg/flags/react/us'

type FlagComp = ComponentType<SVGProps<SVGSVGElement> & { variant?: 'circle' | '4x3' | 'square'; size?: number }>

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

export function CountryFlag({ iso2, size = 18, className }: CountryFlagProps) {
  if (!iso2) return null
  const code = iso2.toLowerCase()
  const Bundled = BUNDLED[code]

  if (Bundled) {
    return (
      <Bundled
        variant="circle"
        size={size}
        className={className}
        aria-hidden
      />
    )
  }

  return (
    <img
      src={`https://thesvg.org/icons/flag-${code}/circle.svg`}
      alt=""
      width={size}
      height={size}
      className={className}
      aria-hidden
      loading="lazy"
    />
  )
}