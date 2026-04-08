import { memo } from 'react'
import { ArrowDownRight, Tag } from 'lucide-react'
import CategoryBadge from './CategoryBadge'
import ConfidenceBadge from './ConfidenceBadge'
import { CATEGORIES } from '../lib/categories'
import { formatCurrency, formatDateTime } from '../lib/format'

function TransactionCard({ txn, onCorrect, showCorrection = true }) {
  const review = txn.review_required || txn.confidence < 0.65

  return (
    <article
      className="card-shine group relative animate-cardEnter overflow-hidden rounded-2xl border border-theme bg-gradient-to-br from-white/95 to-slate-100/80 p-4 shadow-[0_4px_24px_-8px_rgb(15_23_42/0.12)] backdrop-blur-md transition-[border-color,box-shadow,transform] duration-300 hover:-translate-y-px hover:border-sky-400/45 hover:shadow-lg hover:shadow-sky-500/10 sm:p-5 dark:from-surface-elevated/90 dark:to-surface-muted/40 dark:shadow-card dark:hover:border-sky-400/20 dark:hover:shadow-card-hover"
    >
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sky-400/40 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        aria-hidden
      />

      {txn.anomaly && (
        <div className="absolute right-4 top-4 flex items-center gap-1.5" title={txn.anomaly.reason}>
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-400 opacity-40" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-rose-500 shadow-[0_0_14px_rgba(244,63,94,0.85)]" />
          </span>
        </div>
      )}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-sky-500/20 text-sky-800 ring-1 ring-sky-400/35 dark:bg-sky-500/15 dark:text-sky-300 dark:ring-sky-400/20">
              <Tag className="h-4 w-4" strokeWidth={2} aria-hidden />
            </span>
            <h3 className="truncate font-display text-lg font-bold tracking-tight text-content">
              {txn.merchant_clean}
            </h3>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <CategoryBadge categoryId={txn.category} />
            <ConfidenceBadge value={txn.confidence} />
            {review && (
              <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/35 bg-amber-500/15 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-amber-100">
                Review required
              </span>
            )}
          </div>
          <p className="truncate font-mono text-xs text-content-muted/90" title={txn.merchant_raw}>
            {txn.merchant_raw}
          </p>
          <p className="text-xs font-medium text-content-muted">{formatDateTime(txn.date)}</p>
          {txn.anomaly && (
            <p className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-200/95">
              {txn.anomaly.reason}
            </p>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1 sm:text-right">
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-rose-300/90 ring-1 ring-rose-500/25">
            <ArrowDownRight className="h-3 w-3" aria-hidden />
            {txn.debit_credit}
          </span>
          <p className="font-display text-2xl font-bold tabular-nums tracking-tight text-content">
            {formatCurrency(txn.amount, txn.currency)}
          </p>
        </div>
      </div>

      {showCorrection && review && (
        <div className="mt-4 flex flex-col gap-3 border-t border-theme-subtle pt-4 sm:flex-row sm:flex-wrap sm:items-center">
          <label htmlFor={`cat-${txn.txn_id}`} className="flex shrink-0 items-center gap-2 text-xs font-semibold text-content-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
            Recategorise
          </label>
          <select
            id={`cat-${txn.txn_id}`}
            value={txn.category}
            onChange={(e) => onCorrect?.(txn.txn_id, e.target.value)}
            className="select-premium min-w-0 w-full flex-1 sm:w-auto sm:min-w-[200px]"
          >
            {CATEGORIES.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
      )}
    </article>
  )
}

export default memo(TransactionCard)
