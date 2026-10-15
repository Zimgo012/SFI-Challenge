import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router'
import { navigation } from '../config/navigation'
import ThemeToggle from '../components/ThemeToggle'
import SimulationClock from '../components/SimulationClock'

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(() =>
    window.matchMedia('(min-width: 1024px)').matches,
  )
  const { pathname } = useLocation()
  const mainRef = useRef<HTMLElement>(null)
  const previousPath = useRef(pathname)
  const currentPage = navigation.find((item) => item.path === pathname)

  useEffect(() => {
    document.title = `${currentPage?.label ?? 'Page not found'} | SFI Challenge`
    if (previousPath.current !== pathname) {
      mainRef.current?.focus()
      window.scrollTo(0, 0)
      previousPath.current = pathname
    }
  }, [pathname, currentPage])

  return (
    <div className={`min-h-screen bg-base-200 lg:grid ${sidebarOpen ? 'lg:grid-cols-[16rem_1fr]' : 'lg:grid-cols-1'}`}>
      <a href="#main-content" className="btn btn-primary fixed top-2 left-2 z-50 -translate-y-24 focus:translate-y-0">
        Skip to content
      </a>
      <aside id="app-sidebar" hidden={!sidebarOpen} className="border-b border-base-300 bg-base-100 lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto lg:border-r lg:border-b-0">
        <div className="px-6 pt-7 pb-5">
          <p className="text-lg font-bold tracking-tight text-primary">SFI Challenge</p>
          <p className="mt-1 text-sm text-base-content/60">Transport operations</p>
        </div>
        <nav aria-label="Main navigation" className="px-3 pb-4">
          <ul className="menu w-full gap-1">
            {navigation.map((item) => (
              <li key={item.path}>
                <NavLink to={item.path} end onClick={() => {
                  if (!window.matchMedia('(min-width: 1024px)').matches) setSidebarOpen(false)
                }} className={({ isActive }) =>
                  `rounded-lg px-4 py-3 ${isActive ? 'bg-primary text-primary-content font-semibold hover:bg-primary hover:text-primary-content' : 'hover:bg-primary/10 hover:text-primary'}`
                }>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex min-h-18 flex-wrap items-center justify-between gap-4 border-b border-base-300 bg-base-100 px-6 py-4 lg:px-10">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              className="btn btn-ghost btn-square btn-sm shrink-0"
              onClick={() => setSidebarOpen((open) => !open)}
              aria-expanded={sidebarOpen}
              aria-controls="app-sidebar"
              aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
              title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            >
              <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className="size-5">
                <rect x="3" y="4" width="18" height="16" rx="2" />
                <path strokeLinecap="round" strokeLinejoin="round" d={sidebarOpen ? 'M9 4v16m7-11-3 3 3 3' : 'M9 4v16m4-11 3 3-3 3'} />
              </svg>
            </button>
            <p className="truncate text-sm font-medium">Operations / {currentPage?.label ?? 'Page not found'}</p>
          </div>
          <div className="flex w-full items-center justify-between gap-4 sm:w-auto sm:justify-end">
            <SimulationClock />
            <ThemeToggle />
          </div>
        </header>
        <main id="main-content" ref={mainRef} tabIndex={-1} className="mx-auto max-w-7xl p-6 outline-none lg:p-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
