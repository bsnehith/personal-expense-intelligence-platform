import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertCircle, CloudUpload, FileSpreadsheet, Filter } from 'lucide-react'
import { useAppState } from '../context/AppStateContext'
import { API_BASE, streamStatementSummary, uploadStatement } from '../lib/api'
import { CATEGORIES } from '../lib/categories'
import { formatCurrency, formatDateTime } from '../lib/format'
import CategoryBadge from '../components/CategoryBadge'
import ConfidenceBadge from '../components/ConfidenceBadge'
import PageHeader from '../components/ui/PageHeader'

const MAX_UPLOAD_BYTES = 20 * 1024 * 1024
const ALLOWED_EXTENSIONS = new Set(['pdf', 'csv', 'xlsx', 'xls'])

export default function UploadPage() {
  const {
    transactions,
    parseJob,
    startParseJob,
    updateParseJob,
    finishParseJob,
    addTransaction,
    gatewayReachable,
  } = useAppState()

  const [drag, setDrag] = useState(false)
  const [catFilter, setCatFilter] = useState('all')
  const [minAmt, setMinAmt] = useState('')
  const [maxAmt, setMaxAmt] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [uploadError, setUploadError] = useState(null)
  const [statementInsight, setStatementInsight] = useState('')
  const [statementInsightLoading, setStatementInsightLoading] = useState(false)
  const [elapsedSec, setElapsedSec] = useState(0)
  const fileInputRef = useRef(null)
  const lastBatchRef = useRef([])

  const uploaded = useMemo(
    () => transactions.filter((t) => t.source === 'statement_upload'),
    [transactions],
  )

  const filtered = useMemo(() => {
    return uploaded.filter((t) => {
      if (catFilter !== 'all' && t.category !== catFilter) return false
      const min = minAmt ? Number(minAmt) : null
      const max = maxAmt ? Number(maxAmt) : null
      if (min != null && Number.isFinite(min) && t.amount < min) return false
      if (max != null && Number.isFinite(max) && t.amount > max) return false
      if (dateFrom) {
        const d = new Date(t.date)
        const lo = new Date(dateFrom)
        if (!Number.isNaN(lo.getTime()) && d < lo) return false
      }
      if (dateTo) {
        const d = new Date(t.date)
        const hi = new Date(dateTo)
        if (!Number.isNaN(hi.getTime()) && d > hi) return false
      }
      return true
    })
  }, [uploaded, catFilter, minAmt, maxAmt, dateFrom, dateTo])

  const handleFile = useCallback(
    async (file) => {
      if (!file) return
      const ext = (file.name?.split('.').pop() || '').toLowerCase()
      if (!ALLOWED_EXTENSIONS.has(ext)) {
        setUploadError('Only PDF, CSV, and Excel files (.xlsx/.xls) are allowed.')
        return
      }
      if (file.size > MAX_UPLOAD_BYTES) {
        setUploadError('File too large (max 20 MB).')
        return
      }
      if (!API_BASE) {
        setUploadError('Backend not connected. Set VITE_API_BASE_URL in frontend/.env and restart.')
        return
      }
      if (gatewayReachable === false) {
        setUploadError(
          'API gateway unreachable. Run: docker compose up -d (and wait until services are healthy).',
        )
        return
      }
      setUploadError(null)
      setStatementInsight('')
      lastBatchRef.current = []
      setElapsedSec(0)
      startParseJob(0)

      try {
        await uploadStatement(file, (data) => {
          updateParseJob({
            step: data.step,
            label: data.label,
            done: data.done ?? 0,
            total: data.total ?? 0,
            running: data.step !== 'done' && data.step !== 'error',
            uploadBytes: data.step === 'upload' ? data.done : null,
            uploadTotal: data.step === 'upload' ? data.total : null,
            ...(data.indeterminate !== undefined ? { indeterminate: data.indeterminate } : {}),
          })
          if (data.txn) {
            const row = { ...data.txn, source: 'statement_upload', source_file: file.name }
            lastBatchRef.current.push(row)
            addTransaction(row)
          }
          if (data.step === 'done') {
            finishParseJob('success')
            const batch = lastBatchRef.current
            if (API_BASE && batch.length > 0) {
              setStatementInsightLoading(true)
              setStatementInsight('')
              streamStatementSummary(batch, file.name, (tok) => {
                setStatementInsight((prev) => prev + tok)
              })
                .catch(() => {
                  setStatementInsight(
                    (prev) =>
                      prev ||
                      '[Coach unavailable — check GEMINI_API_KEY on genai-service or gateway connectivity.]',
                  )
                })
                .finally(() => setStatementInsightLoading(false))
            }
          }
          if (data.step === 'error') {
            setUploadError(data.label || 'Parse error')
            finishParseJob('error')
          }
        })
      } catch (err) {
        setUploadError(err.message || 'Upload failed')
        finishParseJob('error')
      }
    },
    [startParseJob, updateParseJob, finishParseJob, addTransaction, gatewayReachable],
  )

  useEffect(() => {
    if (!parseJob?.running) return undefined
    const id = window.setInterval(() => {
      setElapsedSec((s) => s + 1)
    }, 1000)
    return () => window.clearInterval(id)
  }, [parseJob?.running])

  // Safety net: if terminal SSE event is missed but all rows are already rendered,
  // mark the upload as complete so the UI does not remain stuck in "running".
  useEffect(() => {
    if (!parseJob?.running) return
    if (!parseJob?.total || parseJob.total <= 0) return
    if (uploaded.length < parseJob.total) return

    updateParseJob({
      step: 'done',
      label: 'Done',
      done: parseJob.total,
      total: parseJob.total,
      running: false,
      indeterminate: false,
    })
    finishParseJob('success')
  }, [parseJob, uploaded.length, updateParseJob, finishParseJob])

  const onDrop = useCallback(
    (e) => {
      e.preventDefault()
      setDrag(false)
      const file = e.dataTransfer?.files?.[0]
      handleFile(file)
    },
    [handleFile],
  )

  const onFileInput = useCallback(
    (e) => {
      const file = e.target.files?.[0]
      handleFile(file)
      e.target.value = ''
    },
    [handleFile],
  )

  const progressIndeterminate = useMemo(() => {
    if (!parseJob?.running) return false
    if (parseJob.step === 'upload' && parseJob.uploadTotal > 0) return false
    return Boolean(parseJob.indeterminate) || parseJob.total === 0
  }, [parseJob])

  const progressPct = useMemo(() => {
    if (!parseJob) return 0
    if (!parseJob.running) return parseJob.total ? 100 : 0
    if (parseJob.step === 'upload' && parseJob.uploadTotal > 0 && parseJob.uploadBytes != null) {
      return Math.min(100, Math.round((parseJob.uploadBytes / parseJob.uploadTotal) * 100))
    }
    if (progressIndeterminate) return 40
    if (parseJob.total > 0) {
      return Math.min(100, Math.round((parseJob.done / parseJob.total) * 100))
    }
    return 0
  }, [parseJob, progressIndeterminate])

  const phaseHint = useMemo(() => {
    if (!parseJob?.running) return null
    const s = parseJob.step
    if (s === 'upload') return 'Step 1/4 · Sending bytes to API gateway'
    if (s === 'detect') return 'Step 2/4 · Parser detected format'
    if (s === 'extract') return 'Step 3/4 · Reading rows from file (PDFs/OCR can take a while)'
    if (s === 'categorise') return 'Step 4/4 · ML categorisation (batch)'
    if (s === 'progress') return 'Step 4/4 · Applying categories'
    return null
  }, [parseJob])

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="Path B · Documents"
        title="Statement ingestion"
        description="Drop or click to upload a PDF, CSV, or XLSX bank statement. Progress shows file upload %, parsing, then batch ML categorisation — large PDFs may take time to extract."
      />

      {/* Upload zone */}
      <motion.div
        role="button"
        tabIndex={0}
        onDragEnter={(e) => { e.preventDefault(); setDrag(true) }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            fileInputRef.current?.click()
          }
        }}
        whileHover={{ scale: 1.005 }}
        whileTap={{ scale: 0.995 }}
        onClick={() => fileInputRef.current?.click()}
        className={[
          'relative flex min-h-[220px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-3xl border-2 border-dashed p-12 text-center transition-colors duration-300',
          drag
            ? 'border-sky-400/70 bg-sky-500/10 shadow-[0_0_0_1px_rgb(56_189_248/0.3),0_0_48px_-8px_rgb(56_189_248/0.35)]'
            : 'border-theme bg-surface-elevated/70 hover:border-sky-400/50 hover:bg-sky-500/10 dark:border-white/[0.12] dark:bg-surface-elevated/40 dark:hover:border-sky-400/35 dark:hover:bg-sky-500/5',
        ].join(' ')}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.csv,.xlsx,.xls"
          className="sr-only"
          onChange={onFileInput}
        />
        <div
          className={`pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 ${drag ? 'opacity-100' : ''}`}
          style={{ background: 'radial-gradient(ellipse 80% 60% at 50% 0%, rgb(56 189 248 / 0.15), transparent 70%)' }}
        />
        <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500/30 to-cyan-600/20 ring-1 ring-sky-400/30">
          <CloudUpload className="h-8 w-8 text-sky-600 dark:text-sky-200" strokeWidth={1.75} />
        </div>
        <p className="relative mt-6 font-display text-xl font-bold text-content">
          Drop or click to upload
        </p>
        <p className="relative mt-2 flex flex-wrap items-center justify-center gap-2 text-sm text-content-muted">
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-200/80 px-2 py-0.5 text-xs font-medium ring-1 ring-slate-300/80 dark:bg-white/5 dark:ring-white/10">
            <FileSpreadsheet className="h-3.5 w-3.5" />
            PDF · CSV · XLSX
          </span>
          <span>· max 20MB</span>
        </p>
      </motion.div>

      {/* Error banner */}
      {uploadError && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start gap-3 rounded-2xl border border-red-400/35 bg-red-500/10 px-4 py-3 text-sm text-red-800 dark:text-red-200"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {uploadError}
        </motion.div>
      )}

      {/* Progress bar */}
      {parseJob && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel border-sky-400/20"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-bold text-content">
                {parseJob.label}
                {parseJob.running ? ` · ${elapsedSec}s` : ''}
              </p>
              {phaseHint && (
                <p className="mt-1 text-xs text-content-muted">{phaseHint}</p>
              )}
            </div>
            {parseJob.total > 0 && parseJob.step !== 'upload' && (
              <p className="text-sm font-semibold tabular-nums text-sky-800 dark:text-sky-200/90">
                {parseJob.done} / {parseJob.total} rows
              </p>
            )}
            {parseJob.step === 'upload' &&
              parseJob.uploadTotal > 0 &&
              parseJob.uploadBytes != null && (
                <p className="text-sm font-semibold tabular-nums text-sky-800 dark:text-sky-200/90">
                  {((parseJob.uploadBytes / parseJob.uploadTotal) * 100).toFixed(0)}% sent
                </p>
              )}
          </div>
          <div className="relative mt-4 h-3 overflow-hidden rounded-full bg-surface-muted ring-1 ring-slate-200/80 dark:ring-white/5">
            {progressIndeterminate && (
              <motion.div
                className="absolute inset-y-0 left-0 w-[40%] rounded-full bg-gradient-to-r from-sky-400/60 to-cyan-300/80"
                animate={{ x: ['-35%', '235%'] }}
                transition={{ repeat: Infinity, duration: 1.2, ease: 'easeInOut' }}
              />
            )}
            {!progressIndeterminate && (
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-sky-500 via-cyan-400 to-teal-400"
                initial={false}
                animate={{ width: `${parseJob.running ? progressPct : 100}%` }}
                transition={{ type: 'spring', stiffness: 120, damping: 20 }}
              />
            )}
          </div>
        </motion.div>
      )}

      {/* Auto GenAI statement summary (spec §6.1 Screen 2) */}
      {(statementInsight || statementInsightLoading) && (
        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel border-violet-400/25"
        >
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-bold text-content">GenAI statement summary</p>
            {statementInsightLoading && (
              <span className="text-xs font-medium text-violet-600 dark:text-violet-300">
                Streaming…
              </span>
            )}
          </div>
          <pre className="mt-4 max-h-80 overflow-y-auto whitespace-pre-wrap rounded-2xl border border-theme-subtle bg-surface-muted/40 p-4 font-sans text-sm leading-relaxed text-content scrollbar-thin">
            {statementInsight}
            {statementInsightLoading && (
              <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-violet-400" />
            )}
          </pre>
        </motion.section>
      )}

      {/* Preview table */}
      <section className="space-y-5">
        <div className="flex items-center gap-2 text-sm font-bold text-content">
          <Filter className="h-4 w-4 text-sky-400" />
          Uploaded transactions
          {uploaded.length > 0 && (
            <span className="ml-1 rounded-full bg-sky-500/15 px-2 py-0.5 text-xs font-semibold text-sky-800 dark:text-sky-200">
              {uploaded.length}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-4 rounded-2xl border border-theme-subtle bg-surface-muted/30 p-4 sm:flex-row sm:flex-wrap sm:items-end dark:bg-surface-muted/20">
          <label className="flex min-w-[140px] flex-1 flex-col gap-1.5 text-xs font-semibold uppercase tracking-wide text-content-muted">
            Category
            <select
              value={catFilter}
              onChange={(e) => setCatFilter(e.target.value)}
              className="select-premium"
            >
              <option value="all">All categories</option>
              {CATEGORIES.map((c) => (
                <option key={c.id} value={c.id}>{c.label}</option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[120px] flex-1 flex-col gap-1.5 text-xs font-semibold uppercase tracking-wide text-content-muted">
            Min ₹
            <input
              type="number"
              value={minAmt}
              onChange={(e) => setMinAmt(e.target.value)}
              className="input-premium"
              placeholder="0"
            />
          </label>
          <label className="flex min-w-[120px] flex-1 flex-col gap-1.5 text-xs font-semibold uppercase tracking-wide text-content-muted">
            Max ₹
            <input
              type="number"
              value={maxAmt}
              onChange={(e) => setMaxAmt(e.target.value)}
              className="input-premium"
              placeholder="Any"
            />
          </label>
          <label className="flex min-w-[150px] flex-1 flex-col gap-1.5 text-xs font-semibold uppercase tracking-wide text-content-muted">
            From date
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="input-premium"
            />
          </label>
          <label className="flex min-w-[150px] flex-1 flex-col gap-1.5 text-xs font-semibold uppercase tracking-wide text-content-muted">
            To date
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="input-premium"
            />
          </label>
        </div>

        <div className="overflow-hidden rounded-2xl border border-theme shadow-card">
          <div className="overflow-x-auto scrollbar-thin">
            <table className="min-w-full divide-y divide-white/[0.06] text-left text-sm">
              <thead className="bg-surface-muted/50 text-[11px] font-bold uppercase tracking-wider text-content-muted">
                <tr>
                  <th className="px-4 py-3.5">When</th>
                  <th className="px-4 py-3.5">Merchant</th>
                  <th className="px-4 py-3.5">Category</th>
                  <th className="px-4 py-3.5">Confidence</th>
                  <th className="px-4 py-3.5 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/80 dark:divide-white/[0.05]">
                {filtered.map((t) => (
                  <tr
                    key={t.txn_id}
                    className="bg-surface-elevated/30 transition-colors hover:bg-sky-500/[0.06]"
                  >
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-content-muted">
                      {formatDateTime(t.date)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-content">{t.merchant_clean}</div>
                      <div className="max-w-xs truncate font-mono text-xs text-content-muted">
                        {t.merchant_raw}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <CategoryBadge categoryId={t.category} />
                    </td>
                    <td className="px-4 py-3">
                      <ConfidenceBadge value={t.confidence} />
                    </td>
                    <td className="px-4 py-3 text-right font-display text-sm font-bold tabular-nums text-sky-800 dark:text-sky-100/90">
                      {formatCurrency(t.amount, t.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!filtered.length && (
            <div className="flex flex-col items-center gap-3 p-12 text-center">
              <CloudUpload className="h-10 w-10 text-content-muted/40" strokeWidth={1.5} />
              <p className="text-sm text-content-muted">
                No uploaded transactions yet — drop a PDF, CSV, or XLSX file above.
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
