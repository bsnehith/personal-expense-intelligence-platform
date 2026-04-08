import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Cpu,
  LayoutDashboard,
  Menu,
  Sparkles,
  TriangleAlert,
  Upload,
  X,
  Zap,
} from 'lucide-react'
import { API_BASE } from '../../lib/api'
import { useAppState } from '../../context/AppStateContext'
import ThemeToggle from '../ui/ThemeToggle'
import ToastStack from './ToastStack'

const NAV = [
  { to: '/app', label: 'Live feed', end: true, icon: Zap },
  { to: '/app/upload', label: 'Statements', icon: Upload },
  { to: '/app/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/app/anomalies', label: 'Anomalies', icon: TriangleAlert },
  { to: '/app/coach', label: 'Coach', icon: Sparkles },
  { to: '/app/model', label: 'Model', icon: Cpu },
]

function NavItems({ onNavigate, mobile }) {
  const layoutId = mobile ? 'nav-pill-mobile' : 'nav-pill-desktop'
  return (
    <nav className="flex flex-col gap-1">
      {NAV.map((item) => {
        const Icon = item.icon
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className="group relative block rounded-xl py-2.5 pl-3 pr-3"
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.span
                    layoutId={layoutId}
                    className="absolute inset-0 rounded-xl bg-gradient-to-r from-sky-400/35 via-cyan-400/20 to-teal-400/15 shadow-[inset_0_1px_0_0_rgb(255_255_255/0.5)] ring-1 ring-sky-400/40 dark:from-sky-500/25 dark:via-cyan-500/15 dark:to-teal-500/10 dark:shadow-[inset_0_1px_0_0_rgb(255_255_255/0.08)] dark:ring-sky-400/35"
                    transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                  />
                )}
                <span className="relative z-10 flex items-center gap-3">
                  <span
                    className={
                      isActive
                        ? 'flex h-9 w-9 items-center justify-center rounded-lg bg-sky-500/25 text-sky-800 dark:bg-sky-500/20 dark:text-sky-200'
                        : 'flex h-9 w-9 items-center justify-center rounded-lg text-content-muted transition group-hover:text-content'
                    }
                  >
                    <Icon className="h-[18px] w-[18px]" strokeWidth={2} aria-hidden />
                  </span>
                  <span
                    className={`text-sm font-semibold ${isActive ? 'text-content' : 'text-content-muted'}`}
                  >
                    {item.label}
                  </span>
                </span>
              </>
            )}
          </NavLink>
        )
      })}
    </nav>
  )
}

function MobileBottomDock() {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-40 px-2 pb-[max(0.5rem,env(safe-area-inset-bottom,0px))] md:hidden">
      <nav
        className="pointer-events-auto mx-auto flex max-w-xl items-stretch justify-between gap-0.5 rounded-2xl border border-theme-subtle bg-surface/85 p-1 shadow-[0_18px_45px_-20px_rgb(15_23_42/0.45)] backdrop-blur-2xl dark:bg-surface-elevated/85"
        aria-label="Primary"
      >
        {NAV.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={`dock-${item.to}`}
              to={item.to}
              end={item.end}
              title={item.label}
              className="group relative flex min-h-[48px] min-w-0 flex-1 items-center justify-center rounded-xl px-0.5 py-2 sm:px-1"
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="mobile-bottom-dock-pill"
                      className="absolute inset-0 rounded-xl bg-gradient-to-r from-sky-400/35 via-cyan-400/20 to-teal-400/15 ring-1 ring-sky-400/35 dark:from-sky-500/25 dark:via-cyan-500/15 dark:to-teal-500/10 dark:ring-sky-400/25"
                      transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                    />
                  )}
                  <span className="relative z-10 flex min-w-0 flex-col items-center gap-0.5 max-[420px]:gap-0">
                    <Icon
                      className={`h-[18px] w-[18px] shrink-0 transition ${
                        isActive ? 'text-sky-800 dark:text-sky-200' : 'text-content-muted group-hover:text-content'
                      }`}
                      strokeWidth={2}
                      aria-hidden
                    />
                    <span
                      className={`max-w-full truncate text-center text-[10px] font-semibold leading-tight max-[420px]:sr-only ${
                        isActive ? 'text-content' : 'text-content-muted'
                      }`}
                    >
                      {item.label}
                    </span>
                  </span>
                </>
              )}
            </NavLink>
          )
        })}
      </nav>
    </div>
  )
}

export default function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { pathname } = useLocation()
  const current =
    NAV.find((n) => {
      if (n.end) return pathname === n.to
      return pathname === n.to || pathname.startsWith(`${n.to}/`)
    }) ?? NAV[0]

  return (
    <div className="flex min-h-svh min-w-0 overflow-x-clip">
      <aside className="relative hidden w-[17.5rem] shrink-0 flex-col border-r border-theme-subtle bg-surface-muted/40 px-4 py-7 backdrop-blur-xl dark:bg-surface-muted/30 md:flex">
        <div
          className="pointer-events-none absolute inset-y-0 right-0 w-px bg-gradient-to-b from-transparent via-sky-400/25 to-transparent"
          aria-hidden
        />
        <div className="mb-10 px-2">
          <div className="flex items-center gap-3">
            <img
              src="/logo-mark.svg"
              alt="Expense Intelligence"
              className="animate-float-slow h-11 w-11 rounded-2xl shadow-lg shadow-sky-500/30 glow-ring-hover"
            />
            <div>
              <p className="font-display text-[11px] font-bold uppercase tracking-[0.18em] text-sky-700 dark:text-sky-300/90">
                Expense IQ
              </p>
              <h1 className="font-display text-base font-bold leading-tight text-content">
                Intelligence
              </h1>
            </div>
          </div>
          <p className="mt-4 text-xs leading-relaxed text-content-muted">
            Live ML categorisation · multi-format statements · GenAI coach
          </p>
        </div>
        <NavItems />
        <div className="mt-6">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-content-muted">Appearance</p>
          <ThemeToggle />
        </div>
        <DataSourceStatus className="mt-4" />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-40 flex items-center justify-between gap-2 border-b border-theme-subtle bg-surface/85 px-3 pb-3 pt-[max(0.75rem,env(safe-area-inset-top,0px))] backdrop-blur-xl md:hidden">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <img src="/logo-mark.svg" alt="Expense Intelligence" className="h-9 w-9 rounded-xl shadow-md shadow-sky-500/25" />
            <div>
              <p className="font-display text-[9px] font-bold uppercase tracking-wider text-sky-700 dark:text-sky-300/90">
                Expense IQ
              </p>
              <p className="font-display text-sm font-bold text-content">{current?.label ?? 'App'}</p>
            </div>
          </div>
          <div className="hidden min-[380px]:block w-[9.25rem] shrink-0 sm:w-[10.5rem]">
            <ThemeToggle />
          </div>
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="btn-ghost interactive-press shrink-0 rounded-xl p-2.5"
            aria-expanded={mobileOpen}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>
        </header>

        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              className="fixed inset-0 z-50 md:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <button
                type="button"
                className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm dark:bg-slate-950/70"
                aria-label="Close menu"
                onClick={() => setMobileOpen(false)}
              />
              <motion.aside
                initial={{ x: '104%' }}
                animate={{ x: 0 }}
                exit={{ x: '104%' }}
                transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                className="absolute right-0 top-0 flex h-full w-[min(20rem,90vw)] flex-col border-l border-theme bg-white/95 p-6 shadow-2xl backdrop-blur-2xl dark:bg-surface-elevated/95"
              >
                <div className="mb-8 flex items-center justify-between">
                  <span className="font-display text-sm font-bold text-content">Navigate</span>
                  <button
                    type="button"
                    onClick={() => setMobileOpen(false)}
                    className="rounded-xl p-2 text-content-muted transition hover:bg-slate-200/80 hover:text-content dark:hover:bg-white/5"
                    aria-label="Close"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
                <div className="mb-6 min-[380px]:hidden">
                  <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-content-muted">Appearance</p>
                  <ThemeToggle />
                </div>
                <NavItems onNavigate={() => setMobileOpen(false)} mobile />
                <DataSourceStatus className="mt-auto border-t border-theme-subtle pt-5" />
              </motion.aside>
            </motion.div>
          )}
        </AnimatePresence>

        <main className="flex-1 overflow-auto pb-[calc(5.75rem+env(safe-area-inset-bottom,0px))] scrollbar-thin md:pb-0">
          <motion.div
            key={pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="mx-auto w-full min-w-0 max-w-6xl px-3 py-5 sm:px-6 sm:py-10"
          >
            <Outlet />
          </motion.div>
        </main>
      </div>

      <MobileBottomDock />
      <ToastStack />
    </div>
  )
}

function DataSourceStatus({ className = '' }) {
  const { gatewayReachable } = useAppState()
  const hasUrl = Boolean(API_BASE)
  const live = hasUrl && gatewayReachable === true
  const checking = hasUrl && gatewayReachable === null
  const unreachable = hasUrl && gatewayReachable === false

  let label = 'No API URL'
  let dotClass = 'bg-amber-500 shadow-[0_0_8px_rgb(245_158_11/0.45)]'
  if (checking) {
    label = 'Checking API…'
    dotClass = 'animate-pulse bg-slate-400 shadow-[0_0_6px_rgb(148_163_184/0.45)]'
  } else if (live) {
    label = 'API gateway'
    dotClass = 'bg-emerald-500 shadow-[0_0_10px_rgb(34_197_94/0.55)]'
  } else if (unreachable) {
    label = 'API unreachable'
    dotClass = 'bg-rose-500 shadow-[0_0_8px_rgb(244_63_94/0.45)]'
  }

  let hint =
    'Add VITE_API_BASE_URL to frontend/.env (e.g. http://localhost:8000) and restart Vite to use the API gateway.'
  if (checking) {
    hint = 'Verifying docker compose / api-gateway at your VITE_API_BASE_URL…'
  } else if (live) {
    hint = 'Corrections, uploads, and streaming use your deployed backend.'
  } else if (unreachable) {
    hint = 'Run docker compose up so the gateway responds; the live feed stays empty until it does.'
  }

  return (
    <div
      className={`rounded-2xl border border-theme-subtle bg-surface-elevated/60 p-3.5 shadow-inner-glow dark:bg-surface-elevated/40 ${className}`}
    >
      <p className="text-[10px] font-bold uppercase tracking-wider text-content-muted">Data source</p>
      <div className="mt-2 flex items-center gap-2">
        <span className={`h-2 w-2 shrink-0 rounded-full ${dotClass}`} aria-hidden />
        <p className="text-xs font-bold text-content">{label}</p>
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-content-muted">{hint}</p>
    </div>
  )
}
