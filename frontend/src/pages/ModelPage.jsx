import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Cpu, RefreshCw, ServerOff } from 'lucide-react'
import { useAppState } from '../context/AppStateContext'
import { API_BASE, postTriggerRetrain } from '../lib/api'
import { CATEGORIES } from '../lib/categories'
import PageHeader from '../components/ui/PageHeader'

export default function ModelPage() {
  const { modelInfo, correctionsTotal, updateModelAfterRetrain } = useAppState()
  const [busy, setBusy] = useState(false)
  const [busyBestFit, setBusyBestFit] = useState(false)
  const [msg, setMsg] = useState(null)

  const heat = modelInfo.confusionMatrix ?? []
  const maxVal = useMemo(() => (heat.length ? Math.max(...heat.flat(), 1) : 1), [heat])
  const hasData = modelInfo.training_rows > 0

  const trigger = async () => {
    setBusy(true)
    setMsg(null)
    try {
      await postTriggerRetrain('fast')
      updateModelAfterRetrain()
      setMsg('Retrain job queued — model info will refresh shortly.')
    } catch (e) {
      setMsg(e.message ?? 'Retrain failed')
    } finally {
      setBusy(false)
    }
  }

  const triggerBestFit = async () => {
    setBusyBestFit(true)
    setMsg(null)
    try {
      await postTriggerRetrain('best_fit')
      updateModelAfterRetrain()
      setMsg('Best-fit retrain queued (all model families) — this may take longer.')
    } catch (e) {
      setMsg(e.message ?? 'Best-fit retrain failed')
    } finally {
      setBusyBestFit(false)
    }
  }

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="ML observability"
        title="Model performance"
        description={
          <>
            Live data from <code className="code-inline text-xs">GET /model-info</code> and the MLflow registry.
            Heat tiles expose category confusion; correction counts hint where to gather more labels.
          </>
        }
      >
        {API_BASE && (
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={trigger}
              disabled={busy || busyBestFit}
              className="btn-ghost rounded-2xl border-sky-400/40 bg-sky-500/15 py-3 font-bold text-sky-900 hover:bg-sky-500/25 disabled:opacity-50 dark:border-sky-400/30 dark:bg-sky-500/10 dark:text-sky-100 dark:hover:bg-sky-500/20"
            >
              <RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} />
              {busy ? 'Queuing…' : 'Fast retrain'}
            </button>
            <button
              type="button"
              onClick={triggerBestFit}
              disabled={busyBestFit || busy}
              className="btn-ghost rounded-2xl border-violet-400/45 bg-violet-500/15 py-3 font-bold text-violet-900 hover:bg-violet-500/25 disabled:opacity-50 dark:border-violet-400/30 dark:bg-violet-500/10 dark:text-violet-100 dark:hover:bg-violet-500/20"
            >
              <RefreshCw className={`h-4 w-4 ${busyBestFit ? 'animate-spin' : ''}`} />
              {busyBestFit ? 'Queuing…' : 'Best-fit retrain'}
            </button>
          </div>
        )}
      </PageHeader>

      {msg && (
        <motion.p
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-sky-400/35 bg-sky-500/15 px-4 py-3 text-sm font-medium text-sky-900 dark:border-sky-400/25 dark:bg-sky-500/10 dark:text-sky-100"
        >
          {msg}
        </motion.p>
      )}

      {/* Not connected state */}
      {!API_BASE && (
        <div className="flex flex-col items-center gap-4 rounded-3xl border border-dashed border-theme py-16 text-center">
          <ServerOff className="h-12 w-12 text-content-muted/40" strokeWidth={1.5} />
          <p className="text-base font-semibold text-content-muted">Backend not connected</p>
          <p className="max-w-sm text-sm text-content-muted/70">
            Set <code className="code-inline text-xs">VITE_API_BASE_URL=http://localhost:8000</code> in{' '}
            <code className="code-inline text-xs">frontend/.env</code> and restart the dev server.
          </p>
        </div>
      )}

      {API_BASE && !hasData && (
        <div className="flex flex-col items-center gap-4 rounded-3xl border border-dashed border-theme py-16 text-center">
          <Cpu className="h-12 w-12 text-content-muted/40" strokeWidth={1.5} />
          <p className="text-base font-semibold text-content-muted">No model info yet</p>
          <p className="max-w-sm text-sm text-content-muted/70">
            Train the ML model first — run <code className="code-inline text-xs">python ml-service/model/train.py</code> then restart the ml-service.
          </p>
        </div>
      )}

      {hasData && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Stat label="Model version" value={modelInfo.version} delay={0} />
            <Stat label="Training rows" value={modelInfo.training_rows.toLocaleString()} delay={0.04} />
            <Stat label="Eval accuracy" value={`${Math.round(modelInfo.eval_accuracy * 100)}%`} delay={0.08} highlight />
            <Stat
              label="Last retrained"
              value={modelInfo.last_retrained ? new Date(modelInfo.last_retrained).toLocaleString() : '—'}
              delay={0.12}
            />
            <Stat label="Corrections (session)" value={String(correctionsTotal)} delay={0.16} />
            <Stat label="Registry stage" value="Staging → Prod gate" delay={0.2} />
          </div>

          {heat.length > 0 && (
            <section className="glass-panel">
              <div className="mb-5 flex items-center gap-2.5">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-500/20 text-violet-900 ring-1 ring-violet-400/35 dark:bg-violet-500/15 dark:text-violet-200 dark:ring-violet-400/25">
                  <Cpu className="h-[18px] w-[18px]" strokeWidth={2} />
                </span>
                <div>
                  <h2 className="font-display text-lg font-bold text-content">Confusion heatmap</h2>
                  <p className="mt-1 text-xs text-content-muted">Predicted (columns) vs Actual (rows)</p>
                </div>
              </div>
              <div className="overflow-x-auto scrollbar-thin">
                <table className="w-full min-w-[400px] border-separate border-spacing-1.5 text-xs">
                  <thead>
                    <tr>
                      <th className="p-1" />
                      {heat[0].map((_, ci) => (
                        <th
                          key={`h-${ci}`}
                          className="truncate p-1 text-center text-[10px] font-bold uppercase tracking-wide text-content-muted"
                          title={CATEGORIES[ci]?.label}
                        >
                          {CATEGORIES[ci]?.label.slice(0, 3) ?? ci}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {heat.map((row, ri) => (
                      <tr key={ri}>
                        <th
                          className="truncate p-2 text-left text-[10px] font-bold uppercase tracking-wide text-content-muted"
                          title={CATEGORIES[ri]?.label}
                        >
                          {CATEGORIES[ri]?.label.slice(0, 6) ?? ri}
                        </th>
                        {row.map((cell, ci) => (
                          <td key={`${ri}-${ci}`} className="p-0">
                            <motion.div
                              initial={false}
                              whileHover={{ scale: 1.06 }}
                              className="h-10 rounded-lg border border-theme-subtle"
                              style={{ background: `rgba(56,189,248,${0.1 + (cell / maxVal) * 0.88})` }}
                              title={`${CATEGORIES[ri]?.label} → ${CATEGORIES[ci]?.label}: ${cell}`}
                            />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {Object.keys(modelInfo.correctionCounts).length > 0 && (
            <section className="glass-panel-muted">
              <h2 className="font-display text-lg font-bold text-content">Corrections by category</h2>
              <p className="mt-1 text-xs text-content-muted">Higher counts → prioritise fresh labels & data aug</p>
              <ul className="mt-5 grid gap-3 sm:grid-cols-2">
                {Object.entries(modelInfo.correctionCounts).map(([k, v], i) => (
                  <motion.li
                    key={k}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="interactive-lift-sm flex items-center justify-between rounded-2xl border border-theme-subtle bg-surface-elevated/70 px-4 py-3.5 transition hover:border-sky-400/35 dark:bg-surface-elevated/40 dark:hover:border-sky-400/25"
                  >
                    <span className="text-sm font-semibold text-content">
                      {CATEGORIES.find((c) => c.id === k)?.label ?? k}
                    </span>
                    <span className="font-display text-lg font-bold tabular-nums text-sky-800 dark:text-sky-200/90">{v}</span>
                  </motion.li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  )
}

function Stat({ label, value, delay = 0, highlight }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className={
        highlight
          ? 'rounded-2xl border border-sky-400/45 bg-gradient-to-br from-sky-100/90 to-cyan-50/80 p-5 shadow-inner-glow dark:border-sky-400/35 dark:from-sky-500/15 dark:to-cyan-600/5 dark:shadow-[inset_0_1px_0_0_rgb(255_255_255/0.06)]'
          : 'rounded-2xl border border-theme-subtle bg-surface-elevated/70 p-5 shadow-inner-glow transition hover:border-sky-400/30 dark:border-white/[0.08] dark:bg-surface-elevated/40 dark:hover:border-white/[0.12]'
      }
    >
      <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-content-muted">{label}</p>
      <p className="mt-2 break-words font-display text-xl font-bold text-content">{value}</p>
    </motion.div>
  )
}
