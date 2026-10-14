import { useEffect, useRef } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router'
import { navigation } from '../config/navigation'
import ThemeToggle from '../components/ThemeToggle'

export default function AppLayout() {
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
    <div className="min-h-screen bg-base-200 lg:grid lg:grid-cols-[16rem_1fr]">
      <a href="#main-content" className="btn btn-primary fixed top-2 left-2 z-50 -translate-y-24 focus:translate-y-0">
        Skip to content
      </a>
      <aside className="border-b border-base-300 bg-base-100 lg:sticky lg:top-0 lg:h-screen lg:border-r lg:border-b-0">
        <div className="px-6 pt-7 pb-5">
          <p className="text-lg font-bold tracking-tight text-primary">SFI Challenge</p>
          <p className="mt-1 text-sm text-base-content/60">Transport operations</p>
        </div>
        <nav aria-label="Main navigation" className="px-3 pb-4">
          <ul className="menu w-full gap-1">
            {navigation.map((item) => (
              <li key={item.path}>
                <NavLink to={item.path} end className={({ isActive }) =>
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
        <header className="flex min-h-18 items-center justify-between gap-4 border-b border-base-300 bg-base-100 px-6 py-4 lg:px-10">
          <p className="text-sm font-medium">Operations / {currentPage?.label ?? 'Page not found'}</p>
          <ThemeToggle />
        </header>
        <main id="main-content" ref={mainRef} tabIndex={-1} className="mx-auto max-w-7xl p-6 outline-none lg:p-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
