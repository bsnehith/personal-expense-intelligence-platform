import { useRef } from 'react'
import { motion } from 'framer-motion'
import { useVirtualizer } from '@tanstack/react-virtual'
import { Activity, AlertCircle, Info, Radio } from 'lucide-react'
import { useAppState } from '../context/AppStateContext'
import TransactionCard from '../components/TransactionCard'
import PageHeader from '../components/ui/PageHeader'

const ROW_GAP_PX = 16

export default function LiveFeedPage() {
  const {
    transactions,
    streamOn,
    setStreamOn,
    correctCategory,
    liveFeedMeta,
    liveFeedReady,
    gatewayReachable,
  } = useAppState()

  const parentRef = useRef(null)

  // TanStack Virtual returns non-memoizable internals; safe here (local scroll container only).
  // eslint-disable-next-line react-hooks/incompatible-library -- virtualizer scroll state is intentional
  const virtualizer = useVirtualizer({
    count: transactions.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 200,
    overscan: 6,
    getItemKey: (index) => transactions[index]?.txn_id ?? index,
    gap: ROW_GAP_PX,
  })

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Path A · Streaming"
        title="Live transaction feed"
        description={
          <>
            Live feed via SSE — each card lands with ML category + confidence.{' '}
            <span className="font-medium text-sky-800 dark:text-sky-200/90">Low confidence</span> unlocks inline
            correction → <code className="code-inline text-xs">POST /correct</code>{' '}
            when your API is wired. Cadence follows your backend (e.g. Docker <code className="code-inline text-xs">simulator</code> /{' '}
            <code className="code-inline text-xs">TX_INTERVAL_SEC</code>).
          </>
        }
      >
        <div className="control-well w-full max-w-full sm:max-w-md">
          <label className="flex w-full min-w-0 cursor-pointer items-center gap-3 text-sm font-semibold text-content">
            <input
              type="checkbox"
              checked={streamOn}
              onChange={(e) => setStreamOn(e.target.checked)}
              className="h-5 w-5 shrink-0 rounded-md border-slate-300 bg-white text-sky-600 shadow-inner-glow focus:ring-2 focus:ring-sky-500/40 dark:border-white/20 dark:bg-surface-muted dark:text-sky-500"
            />
            <Radio className="h-4 w-4 text-sky-400" aria-hidden />
            Stream live
          </label>
        </div>
      </PageHeader>

      {liveFeedMeta?.kind === 'waiting_kafka' && (
        <div
          role="status"
          className="flex gap-3 rounded-xl border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-sm text-amber-100/95"
        >
          <Info className="h-5 w-5 shrink-0 text-amber-400" aria-hidden />
          <div>
            <p className="font-semibold">Connecting to Kafka for the live feed…</p>
            <p className="mt-1 text-xs text-amber-200/80">
              Broker: <code className="code-inline">{liveFeedMeta.bootstrap}</code>
              {liveFeedMeta.error ? ` — ${liveFeedMeta.error}` : null}
            </p>
          </div>
        </div>
      )}

      {liveFeedMeta?.kind === 'kafka_unavailable' && (
        <div
          role="alert"
          className="flex gap-3 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-100/95"
        >
          <AlertCircle className="h-5 w-5 shrink-0 text-rose-400" aria-hidden />
          <div>
            <p className="font-semibold">Kafka is not reachable — the feed cannot start.</p>
            <p className="mt-1 text-xs text-rose-200/85">{liveFeedMeta.hint}</p>
            <p className="mt-1 text-xs text-rose-200/70">
              Bootstrap: <code className="code-inline">{liveFeedMeta.bootstrap}</code>
            </p>
          </div>
        </div>
      )}

      {liveFeedMeta?.kind === 'sse_error' && gatewayReachable && (
        <div className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-xs text-content-muted">
          Live feed connection interrupted — browser will retry. If this persists, restart the API gateway and
          ensure Kafka is healthy.
        </div>
      )}

      <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs font-semibold uppercase tracking-wider text-content-muted">
        <Activity className={`h-4 w-4 shrink-0 ${streamOn ? 'animate-pulse text-emerald-400' : 'text-content-muted'}`} />
        <span className="min-w-0">{streamOn ? 'Receiving events' : 'Stream paused'}</span>
        <span className="tabular-nums text-content-muted/70">· {transactions.length} in buffer</span>
      </div>

      <section className="grid gap-3 sm:grid-cols-3">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel glass-hover-ring rounded-2xl p-4"
        >
          <p className="text-[11px] font-bold uppercase tracking-wide text-content-muted">Feed status</p>
          <p className="mt-2 text-sm font-semibold text-content">
            {streamOn ? 'Live stream enabled' : 'Stream stopped'}
          </p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="glass-panel glass-hover-ring rounded-2xl p-4"
        >
          <p className="text-[11px] font-bold uppercase tracking-wide text-content-muted">Transactions</p>
          <p className="mt-2 font-display text-2xl font-bold tabular-nums text-content">{transactions.length}</p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-panel glass-hover-ring rounded-2xl p-4"
        >
          <p className="text-[11px] font-bold uppercase tracking-wide text-content-muted">Gateway</p>
          <p className="mt-2 text-sm font-semibold text-content">
            {gatewayReachable === true ? 'Connected' : gatewayReachable === false ? 'Disconnected' : 'Checking'}
          </p>
        </motion.div>
      </section>

      <section aria-label="Transaction feed">
        <div
          ref={parentRef}
          className="h-[min(62vh,560px)] overflow-auto rounded-2xl border border-theme-subtle bg-surface-elevated/35 p-2 pr-1 shadow-inner-glow scrollbar-thin sm:h-[min(68vh,640px)] sm:p-3"
        >
          {transactions.length === 0 &&
            liveFeedReady &&
            streamOn &&
            gatewayReachable &&
            liveFeedMeta?.kind !== 'waiting_kafka' &&
            liveFeedMeta?.kind !== 'connecting' &&
            liveFeedMeta?.kind !== 'kafka_unavailable' && (
            <div className="m-4 space-y-4 rounded-2xl border border-sky-500/25 bg-sky-500/5 p-6 text-sm text-content-muted">
              <p className="font-display text-base font-semibold text-content">
                No transactions in the buffer yet
              </p>
              <p>
                The gateway streams from Kafka topic <code className="code-inline">categorised_transactions</code>.
                It only shows <strong className="text-content">new</strong> events produced <strong>after</strong> this
                page connected (default offset: latest).
              </p>
              <ol className="list-decimal space-y-2 pl-5 text-content-muted">
                <li>
                  <strong className="text-content">Kafka + Zookeeper</strong> running (
                  <code className="code-inline">docker compose up -d zookeeper kafka</code>).
                </li>
                <li>
                  <strong className="text-content">ml-service</strong> on port 8001 — classifies messages and publishes
                  to the topic above.
                </li>
                <li>
                  <strong className="text-content">Simulator</strong> (
                  <code className="code-inline">python simulator/generator.py</code>) or other producers writing to{' '}
                  <code className="code-inline">raw_transactions</code>.
                </li>
              </ol>
            </div>
          )}
          <div
            className="relative w-full"
            style={{ height: `${virtualizer.getTotalSize()}px` }}
          >
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const txn = transactions[virtualRow.index]
              if (!txn) return null
              return (
                <div
                  key={virtualRow.key}
                  data-index={virtualRow.index}
                  ref={virtualizer.measureElement}
                  className="absolute left-0 top-0 w-full"
                  style={{ transform: `translateY(${virtualRow.start}px)` }}
                >
                  <TransactionCard txn={txn} onCorrect={correctCategory} />
                </div>
              )
            })}
          </div>
        </div>
      </section>
    </div>
  )
}
