import { motion } from 'framer-motion'
import { CATEGORY_BY_ID, categoryColor } from '../../lib/categories'
import { formatCurrency } from '../../lib/format'

export default function TopMerchants({ items }) {
  return (
    <ul className="space-y-2">
      {items.map((m, i) => (
        <motion.li
          key={m.name}
          initial={{ opacity: 0, x: -6 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.04 }}
          className="interactive-lift-sm flex items-center justify-between gap-3 rounded-xl border border-theme-subtle bg-surface-muted/40 px-3 py-2.5 transition hover:border-sky-400/40 hover:bg-sky-500/10 dark:hover:border-sky-400/20 dark:hover:bg-sky-500/[0.06]"
        >
          <div className="flex min-w-0 items-center gap-2">
            <span
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg font-display text-xs font-bold text-content"
              style={{ backgroundColor: `${categoryColor(m.category)}33` }}
            >
              {i + 1}
            </span>
            <div className="min-w-0">
              <p className="truncate font-medium text-content">{m.name}</p>
              <p className="truncate text-xs text-content-muted">
                {CATEGORY_BY_ID[m.category]?.label ?? m.category}
              </p>
            </div>
          </div>
          <p className="shrink-0 font-display text-sm font-bold tabular-nums text-sky-800 dark:text-sky-100/90">
            {formatCurrency(m.total)}
          </p>
        </motion.li>
      ))}
      {!items.length && (
        <li className="rounded-xl border border-dashed border-border py-8 text-center text-sm text-content-muted">
          No merchant spend yet
        </li>
      )}
    </ul>
  )
}
