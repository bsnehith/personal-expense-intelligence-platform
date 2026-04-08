import { motion } from 'framer-motion'

export default function PageHeader({ eyebrow, title, description, children }) {
  return (
    <header className="mb-8 flex w-full min-w-0 flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0 max-w-2xl flex-1">
        {eyebrow && (
          <motion.p
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            className="mb-3 flex items-center gap-3 text-[11px] font-bold uppercase tracking-[0.22em] text-accent"
          >
            <span className="h-px w-10 bg-gradient-to-r from-accent to-transparent" aria-hidden />
            {eyebrow}
          </motion.p>
        )}
        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="font-display text-2xl font-bold tracking-tight heading-gradient sm:text-3xl md:text-4xl"
        >
          {title}
        </motion.h1>
        {description && (
          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mt-3 break-words text-sm leading-relaxed text-content-muted"
          >
            {description}
          </motion.p>
        )}
      </div>
      {children && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12 }}
          className="w-full min-w-0 shrink-0 sm:w-auto sm:max-w-md"
        >
          {children}
        </motion.div>
      )}
    </header>
  )
}
