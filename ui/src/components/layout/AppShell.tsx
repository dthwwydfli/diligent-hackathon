import type { ReactNode } from 'react'
import { TopBar } from './TopBar'

interface AppShellProps {
  children: ReactNode
  meta?: string
}

export function AppShell({ children, meta }: AppShellProps) {
  return (
    <div className="min-h-screen bg-canvas px-5 py-0 md:px-6">
      <div className="mx-auto max-w-[1440px]">
        <TopBar meta={meta} />
        <main>{children}</main>
      </div>
    </div>
  )
}