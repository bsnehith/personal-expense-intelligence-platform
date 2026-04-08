import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, Radar, ShieldAlert } from 'lucide-react'
import { useAppState } from '../context/AppStateContext'
import { formatCurrency, formatDateTime } from '../lib/format'
import CategoryBadge from '../components/CategoryBadge'
import PageHeader from '../components/ui/PageHeader'

/** Backend sends { reason, types: string[] }; legacy may use type. */
function anomalyTypeLabel(anomaly) {
  if (!anomaly) return 'Anomaly'
  if (anomaly.type) return String(anomaly.type).replace(/_/g, ' ')
  const types = anomaly.types
  if (Array.isArray(types) && types.length) {
    return types.map((x) => String(x).replace(/_/g, ' ')).join(' · ')
  }
  return 'Anomaly'
}

export default function AnomaliesPage() {
  const { transactions, markAnomalyAction } = useAppState()

  const flagged = useMemo(
    () => transactions.filter((t) => t.anomaly && !t.user_anomaly_action),
    [transactions],
  )

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Risk signals"
        title="Anomaly command centre"
        description="Isolation Forest, Z-score, first-time merchant, and temporal pattern detectors converge here — mirrored as global toasts. Resolve alerts to keep your audit trail honest."
      />

      <div className="grid gap-5">
        {flagged.map((t, i) => (
          <motion.article
            key={t.txn_id}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="group relative overflow-hidden rounded-3xl border border-rose-500/30 bg-gradient-to-br from-rose-500/[0.12] via-surface-elevated/50 to-orange-500/[0.06] p-6 shadow-[0_8px_40px_-12px_rgb(244_63_94/0.25)] backdrop-blur-md"
          >
            <div className="absolute right-0 top-0 h-32 w-32 translate-x-1/3 -translate-y-1/3 rounded-full bg-rose-500/20 blur-3xl" />
            <div className="relative flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-500/25 text-rose-100 ring-1 ring-rose-400/35">
                    <Radar className="h-5 w-5" strokeWidth={2} />
                  </span>
                  <h2 className="font-display text-xl font-bold text-content">{t.merchant_clean}</h2>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <CategoryBadge categoryId={t.category} />
                  <span className="rounded-full bg-rose-500/25 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-rose-100 ring-1 ring-rose-400/30">
                    {anomalyTypeLabel(t.anomaly)}
                  </span>
                </div>
                <p className="max-w-2xl text-sm font-medium leading-relaxed text-rose-100/95">
                  {t.anomaly.reason}
                </p>
                <p className="text-xs font-medium text-content-muted">{formatDateTime(t.date)}</p>
                <p
                  className="max-w-xl truncate font-mono text-xs text-content-muted/80"
                  title={t.merchant_raw}
                >
                  {t.merchant_raw}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="font-display text-3xl font-bold tabular-nums tracking-tight text-content">
                  {formatCurrency(t.amount, t.currency)}
                </p>
              </div>
            </div>
            <div className="relative mt-6 flex flex-wrap gap-3 border-t border-theme-subtle pt-5">
              <button
                type="button"
                onClick={() => markAnomalyAction(t.txn_id, 'expected')}
                className="btn-ghost rounded-xl border-emerald-500/25 bg-emerald-500/10 py-2.5 text-emerald-100 hover:border-emerald-400/40 hover:bg-emerald-500/15"
              >
                <CheckCircle2 className="h-4 w-4" />
                Expected
              </button>
              <button
                type="button"
                onClick={() => markAnomalyAction(t.txn_id, 'review')}
                className="inline-flex items-center gap-2 rounded-xl border border-rose-400/40 bg-rose-500/15 px-4 py-2.5 text-sm font-bold text-rose-50 transition hover:bg-rose-500/25"
              >
                <ShieldAlert className="h-4 w-4" />
                Flag for review
              </button>
            </div>
          </motion.article>
        ))}
        {!flagged.length && (
          <div className="glass-panel-muted flex flex-col items-center py-20 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/25">
              <CheckCircle2 className="h-7 w-7" strokeWidth={1.75} />
            </div>
            <p className="font-display text-lg font-bold text-content">All clear</p>
            <p className="mt-2 max-w-sm text-sm text-content-muted">
              No open anomalies — keep the stream running to surface the next statistical outlier.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
