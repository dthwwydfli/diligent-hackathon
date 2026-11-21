import { useEffect, useRef } from 'react'
import { usePrefersReducedMotion } from './usePrefersReducedMotion'

interface LottieBadgeProps {
  animationData: object
  className?: string
  loop?: boolean
}

export function LottieBadge({
  animationData,
  className = 'h-4 w-4',
  loop = false,
}: LottieBadgeProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const reduced = usePrefersReducedMotion()

  useEffect(() => {
    if (import.meta.env.MODE === 'test' || !containerRef.current || reduced) return
    let destroyed = false
    let anim: { destroy: () => void } | undefined

    void import('lottie-web').then((mod) => {
      if (destroyed || !containerRef.current) return
      anim = mod.default.loadAnimation({
        container: containerRef.current,
        renderer: 'svg',
        loop,
        autoplay: true,
        animationData,
      })
    })

    return () => {
      destroyed = true
      anim?.destroy()
    }
  }, [animationData, loop, reduced])

  if (reduced) {
    return (
      <span
        className={`inline-block rounded-full bg-clear ${className}`}
        aria-hidden
      />
    )
  }

  return <div ref={containerRef} className={className} aria-hidden />
}