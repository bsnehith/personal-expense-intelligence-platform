import { motion } from 'framer-motion'
import { CATEGORIES } from '../../lib/categories'
import { formatCurrency } from '../../lib/format'

export default function BudgetBars({ spentByCategory, budgetByCategory }) {
  return (
    <div className="space-y-4">
      {CATEGORIES.map((c, i) => {
        const spent = spentByCategory[c.id] ?? 0
        const budget = budgetByCategory[c.id] ?? 1
        const pct = Math.min(100, Math.round((spent / budget) * 100))
        const over = spent > budget
        return (
          <motion.div
            key={c.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
          >
            <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="font-medium text-content">{c.label}</span>
              <span className="tabular-nums text-content-muted">
                {formatCurrency(spent)} / {formatCurrency(budget)}
                <span className={over ? ' ml-2 font-semibold text-rose-300' : ' ml-2 text-emerald-300'}>
                  {pct}%
                </span>
              </span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-surface-muted">
              <motion.div
                className="h-full rounded-full"
                style={{ backgroundColor: over ? '#f43f5e' : c.chartColor }}
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(100, pct)}%` }}
                transition={{ type: 'spring', stiffness: 200, damping: 22 }}
              />
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
