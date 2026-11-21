import { Outlet } from 'react-router-dom'
import { TopBar } from './TopBar'

// Layout route: the top bar stays mounted while pages change, so the tab pill slides instead of jumping.
// The shell is exactly one screen tall; pages scroll inside their own panels, never the window.
export function AppShell() {
  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-canvas px-5 md:px-6">
      <div className="mx-auto flex min-h-0 w-full max-w-[1440px] flex-1 flex-col">
        <TopBar />
        <main className="min-h-0 flex-1 pb-5">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
