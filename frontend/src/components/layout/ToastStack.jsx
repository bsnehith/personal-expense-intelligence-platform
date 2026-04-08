import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, X } from 'lucide-react'
import { useAppState } from '../../context/AppStateContext'

export default function ToastStack() {
  const { toasts, dismissToast } = useAppState()

  return (
    <div
      className="pointer-events-none fixed left-3 right-3 top-[max(0.75rem,env(safe-area-inset-top,0px))] z-[100] mx-auto flex max-w-md flex-col gap-3 sm:left-auto sm:right-5 sm:top-5"
      aria-live="polite"
    >
      <AnimatePresence initial={false}>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            layout
            initial={{ opacity: 0, x: 40, scale: 0.94 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 24, scale: 0.94 }}
            transition={{ type: 'spring', stiffness: 400, damping: 28 }}
            className="pointer-events-auto overflow-hidden rounded-2xl border border-rose-500/30 bg-surface-elevated/95 shadow-[0_8px_40px_-8px_rgb(244_63_94/0.35)] backdrop-blur-xl"
          >
            <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-rose-500 via-orange-400 to-amber-400" />
            <div className="flex gap-3 p-4 pt-5">
              <div
                className={
                  t.variant === 'error'
                    ? 'mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-500/20 text-slate-300'
                    : 'mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-rose-500/20 text-rose-200'
                }
              >
                <AlertTriangle className="h-[18px] w-[18px]" strokeWidth={2.2} aria-hidden />
              </div>
              <div className="min-w-0 flex-1 text-left">
                <p className="font-display text-sm font-bold text-content">{t.title}</p>
                <p className="mt-1 text-sm leading-snug text-content-muted">{t.body}</p>
              </div>
              <button
                type="button"
                onClick={() => dismissToast(t.id)}
                className="shrink-0 rounded-xl p-2 text-content-muted transition hover:bg-slate-200/90 hover:text-content dark:hover:bg-white/10"
                aria-label="Dismiss"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
