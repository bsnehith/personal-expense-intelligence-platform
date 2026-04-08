import { useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Bot, SendHorizontal, Sparkles, User } from 'lucide-react'
import { useAppState } from '../context/AppStateContext'
import { API_BASE, streamCoachChat, streamMonthlyReport } from '../lib/api'
import { formatCurrency } from '../lib/format'
import PageHeader from '../components/ui/PageHeader'

const sumDebits = (txns) =>
  txns.reduce((s, t) => s + (t.debit_credit === 'credit' ? 0 : t.amount), 0)

const MONTH_REMINDER_KEY = 'expense_coach_month_boundary'

export default function CoachPage() {
  const { transactions } = useAppState()
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      text: API_BASE
        ? 'Hi — I am your GenAI financial coach powered by your backend. Ask where money went, where to cut back, or tap **Monthly report** for the five mandated sections.'
        : 'Set **VITE_API_BASE_URL** in `frontend/.env` (e.g. `http://localhost:8000`) and restart Vite to use the coach against your API gateway.',
    },
  ])
  const [input, setInput] = useState('')
  const [streamingId, setStreamingId] = useState(null)
  const [streamBuffer, setStreamBuffer] = useState('')
  const abortRef = useRef(false)

  /** Spec §3.2.5 — prompt for monthly review at the start of a new calendar month (client hint). */
  useEffect(() => {
    const now = new Date()
    const period = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    try {
      const seen = localStorage.getItem(MONTH_REMINDER_KEY)
      if (seen === period) return
      localStorage.setItem(MONTH_REMINDER_KEY, period)
      setMessages((prev) => [
        ...prev,
        {
          id: `month_boundary_${period}`,
          role: 'assistant',
          text:
            '**New month** — tap **Monthly report** for a full review (summary, budget vs history, anomalies, 3 quantified actions, month-over-month), or ask a question below.',
        },
      ])
    } catch {
      // storage blocked
    }
  }, [])

  const streamText = useCallback(async (fullText, messageId) => {
    abortRef.current = false
    setStreamingId(messageId)
    setStreamBuffer('')
    const chunk = 4
    for (let i = 0; i < fullText.length && !abortRef.current; i += chunk) {
      setStreamBuffer((b) => b + fullText.slice(i, i + chunk))
      await new Promise((r) => setTimeout(r, 16))
    }
    setStreamingId(null)
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, text: fullText } : m)),
    )
    setStreamBuffer('')
  }, [])

  const send = useCallback(
    async (text) => {
      const trimmed = text.trim()
      if (!trimmed) return
      const userMsg = { id: `u_${Date.now()}`, role: 'user', text: trimmed }
      setMessages((m) => [...m, userMsg])
      setInput('')

      const id = `a_${Date.now()}`
      setMessages((m) => [...m, { id, role: 'assistant', text: '' }])

      if (!API_BASE) {
        const msg =
          'Configure **VITE_API_BASE_URL** in `frontend/.env` and restart the dev server to reach the coach API.'
        await streamText(msg, id)
        return
      }

      setStreamingId(id)
      setStreamBuffer('')
      abortRef.current = false
      let accumulated = ''
      try {
        await streamCoachChat(trimmed, transactions, (token) => {
          if (!abortRef.current) {
            accumulated += token
            setStreamBuffer(accumulated)
          }
        })
        setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, text: accumulated } : m)))
      } catch (e) {
        const msg = e instanceof Error && e.message ? e.message : '[Coach unavailable — check backend]'
        setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, text: msg } : m)))
      } finally {
        setStreamingId(null)
        setStreamBuffer('')
      }
    },
    [streamText, transactions, API_BASE],
  )

  const monthlyReport = useCallback(async () => {
    const id = `a_${Date.now()}`
    setMessages((m) => [...m, { id, role: 'assistant', text: '' }])

    if (!API_BASE) {
      await streamText(
        'Set **VITE_API_BASE_URL** in `frontend/.env` and restart Vite to load the monthly report from your backend.',
        id,
      )
      return
    }

    setStreamingId(id)
    setStreamBuffer('')
    abortRef.current = false
    let accumulated = ''
    try {
      await streamMonthlyReport(transactions, (token) => {
        if (!abortRef.current) {
          accumulated += token
          setStreamBuffer(accumulated)
        }
      })
      setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, text: accumulated } : m)))
    } catch (e) {
      const msg = e instanceof Error && e.message ? e.message : '[Backend unavailable]'
      setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, text: msg } : m)))
    } finally {
      setStreamingId(null)
      setStreamBuffer('')
    }
  }, [streamText, transactions, API_BASE])

  // Auto-trigger monthly review once per month when data is available.
  useEffect(() => {
    const now = new Date()
    const period = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    const autoKey = `${MONTH_REMINDER_KEY}:auto`
    try {
      const seen = localStorage.getItem(autoKey)
      if (seen === period) return
      if (!API_BASE) return
      if (!transactions.length) return
      localStorage.setItem(autoKey, period)
      monthlyReport()
    } catch {
      // storage blocked
    }
  }, [monthlyReport, transactions])

  return (
    <div className="flex min-h-[min(70vh,36rem)] flex-col gap-6 sm:min-h-[calc(100svh-10rem)] sm:gap-8">
      <PageHeader
        eyebrow="GenAI layer"
        title="Financial coach"
        description={
          <>
            {API_BASE ? (
              <>
                Streaming live from <code className="code-inline text-xs">genai-service</code> via SSE — powered by your configured LLM.
              </>
            ) : (
              <>
                Set <code className="code-inline text-xs">VITE_API_BASE_URL</code> in <code className="code-inline text-xs">frontend/.env</code> to reach the coach API.
              </>
            )}
          </>
        }
      >
        <button
          type="button"
          onClick={monthlyReport}
          disabled={!!streamingId}
          className="btn-primary w-full justify-center sm:w-auto sm:whitespace-nowrap disabled:opacity-50"
        >
          <Sparkles className="h-4 w-4" strokeWidth={2.2} />
          Monthly report
        </button>
      </PageHeader>

      <div className="flex flex-1 flex-col overflow-hidden rounded-3xl border border-theme bg-gradient-to-b from-white/90 to-slate-100/80 shadow-card backdrop-blur-xl dark:from-surface-elevated/60 dark:to-surface-muted/30">
        <div className="flex items-center gap-2 border-b border-theme-subtle px-5 py-3">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/25 text-violet-900 dark:bg-violet-500/20 dark:text-violet-200">
            <Bot className="h-4 w-4" strokeWidth={2.2} />
          </span>
          <span className="text-sm font-bold text-content">Coach session</span>
          <span className="ml-auto text-xs font-medium text-content-muted">
            {API_BASE ? 'Live backend' : 'Not configured'}
          </span>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto scrollbar-thin p-4 sm:p-6">
          {messages.map((m) => (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
            >
              <div
                className={
                  m.role === 'user'
                    ? 'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-sky-500/25 text-sky-900 ring-1 ring-sky-400/40 dark:text-sky-100 dark:ring-sky-400/30'
                    : 'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-500/25 text-violet-900 ring-1 ring-violet-400/35 dark:bg-violet-500/20 dark:text-violet-100 dark:ring-violet-400/25'
                }
              >
                {m.role === 'user' ? (
                  <User className="h-4 w-4" strokeWidth={2.2} />
                ) : (
                  <Sparkles className="h-4 w-4" strokeWidth={2.2} />
                )}
              </div>
              <div
                className={
                  m.role === 'user'
                    ? 'min-w-0 max-w-[min(100%,28rem)] rounded-2xl rounded-tr-md border border-sky-400/35 bg-gradient-to-br from-sky-100/90 to-cyan-100/50 px-4 py-3 text-sm leading-relaxed text-content shadow-inner-glow dark:border-sky-400/25 dark:from-sky-500/20 dark:to-cyan-600/10'
                    : 'min-w-0 max-w-[min(100%,36rem)] rounded-2xl rounded-tl-md border border-theme-subtle bg-surface-muted/60 px-4 py-3 text-sm leading-relaxed text-content dark:border-white/[0.08] dark:bg-surface-muted/50'
                }
              >
                {m.id === streamingId ? (
                  <pre className="whitespace-pre-wrap break-words font-sans text-sm">
                    {streamBuffer}
                    <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-sky-400" />
                  </pre>
                ) : (
                  <pre className="whitespace-pre-wrap break-words font-sans text-sm">{m.text}</pre>
                )}
              </div>
            </motion.div>
          ))}
        </div>

        <form
          className="border-t border-theme-subtle bg-surface-muted/50 p-4 sm:p-5 dark:bg-surface-muted/40"
          onSubmit={(e) => {
            e.preventDefault()
            send(input)
          }}
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. Where did I overspend this month?"
              disabled={!!streamingId}
              className="input-premium min-h-[48px] flex-1 rounded-2xl px-4 py-3"
            />
            <button
              type="submit"
              disabled={!!streamingId || !input.trim()}
              className="btn-primary min-h-[48px] shrink-0 px-6 disabled:pointer-events-none disabled:opacity-40"
            >
              <SendHorizontal className="h-4 w-4" />
              Ask
            </button>
          </div>
          <p className="mt-3 flex flex-wrap items-center gap-2 text-xs text-content-muted">
            <span className="h-1 w-1 rounded-full bg-emerald-400" />
            Grounded on live buffer:{' '}
            <span className="font-semibold text-sky-800 dark:text-sky-200/90">{formatCurrency(sumDebits(transactions))}</span>{' '}
            in observed debits
          </p>
        </form>
      </div>
    </div>
  )
}
