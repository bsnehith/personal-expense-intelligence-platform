import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import {
  API_BASE,
  postCorrectCategory,
  subscribeToFeed,
  fetchModelInfo,
  checkGatewayHealth,
} from '../lib/api'

const MAX_FEED = 180

const EMPTY_MODEL_INFO = {
  version: '—',
  training_rows: 0,
  eval_accuracy: 0,
  last_retrained: null,
  confusionMatrix: [],
  correctionCounts: {},
}

const AppStateContext = createContext(null)

export function AppStateProvider({ children }) {
  const [transactions, setTransactions] = useState([])
  // SSE live feed when VITE_API_BASE_URL + gateway /health are available.
  const [streamOn, setStreamOn] = useState(true)
  const [parseJob, setParseJob] = useState(null)
  const [toasts, setToasts] = useState([])
  const [modelInfo, setModelInfo] = useState(EMPTY_MODEL_INFO)
  const [correctionsTotal, setCorrectionsTotal] = useState(0)
  /** null = checking / unknown; true = /health ok; false = unreachable or no API URL */
  const [gatewayReachable, setGatewayReachable] = useState(() => (API_BASE ? null : false))
  /** Live SSE /feed/stream status (Kafka wait, errors). Cleared when a transaction arrives. */
  const [liveFeedMeta, setLiveFeedMeta] = useState(null)
  /** True after gateway SSE sends feed_event ready (Kafka consumer subscribed). */
  const [liveFeedReady, setLiveFeedReady] = useState(false)
  const backendDownNotified = useRef(false)
  const toastId = useRef(0)

  const pushToast = useCallback((payload) => {
    const id = `toast_${toastId.current++}`
    setToasts((prev) => [...prev.slice(-5), { id, ...payload }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 6000)
  }, [])

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addTransaction = useCallback(
    (txn) => {
      setTransactions((prev) => {
        const next = [txn, ...prev]
        return next.slice(0, MAX_FEED)
      })
      if (txn.anomaly) {
        pushToast({
          variant: 'anomaly',
          title: 'Anomaly detected',
          body: `${txn.merchant_clean} — ${txn.anomaly.reason}`,
          txn_id: txn.txn_id,
        })
      }
    },
    [pushToast],
  )

  const correctCategory = useCallback(async (txnId, newCategoryId) => {
    let didChange = false
    setTransactions((prev) =>
      prev.map((t) => {
        if (t.txn_id !== txnId) return t
        if (t.category === newCategoryId) return t
        didChange = true
        return {
          ...t,
          category: newCategoryId,
          confidence: 0.99,
          review_required: false,
        }
      }),
    )
    if (!didChange) return
    setCorrectionsTotal((c) => c + 1)
    const txnSnapshot = transactions.find((t) => t.txn_id === txnId)
    try {
      await postCorrectCategory(txnId, newCategoryId, txnSnapshot)
    } catch {
      pushToast({
        variant: 'error',
        title: 'Correction not synced',
        body: 'Saved locally; backend unreachable.',
      })
    }
  }, [pushToast, transactions])

  const markAnomalyAction = useCallback((txnId, action) => {
    setTransactions((prev) =>
      prev.map((t) =>
        t.txn_id === txnId ? { ...t, user_anomaly_action: action } : t,
      ),
    )
  }, [])

  // Poll GET /health when VITE_API_BASE_URL is set (retries when Docker starts later)
  useEffect(() => {
    if (!API_BASE) {
      setGatewayReachable(false)
      return undefined
    }
    let cancelled = false
    const tick = () => {
      checkGatewayHealth().then((ok) => {
        if (!cancelled) setGatewayReachable(ok)
      })
    }
    tick()
    const id = window.setInterval(tick, 15000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  useEffect(() => {
    if (!API_BASE || gatewayReachable !== false || backendDownNotified.current) return
    backendDownNotified.current = true
    pushToast({
      variant: 'error',
      title: 'API not reachable',
      body: 'Start the backend (docker compose up) so the gateway can stream live transactions.',
    })
  }, [gatewayReachable, pushToast])

  // SSE only after /health succeeds; no synthetic feed when offline
  useEffect(() => {
    if (!streamOn) {
      setLiveFeedMeta(null)
      setLiveFeedReady(false)
      return undefined
    }

    if (API_BASE && gatewayReachable === null) return undefined

    const useLiveSSE = Boolean(API_BASE && gatewayReachable === true)
    if (!useLiveSSE) {
      setLiveFeedMeta(null)
      setLiveFeedReady(false)
      return undefined
    }

    const unsubscribe = subscribeToFeed(
      (txn) => {
        setLiveFeedMeta(null)
        addTransaction(txn)
      },
      (meta) => {
        if (meta.type === 'connecting') {
          setLiveFeedMeta({ kind: 'connecting' })
        } else if (meta.type === 'waiting_kafka') {
          setLiveFeedMeta({
            kind: 'waiting_kafka',
            bootstrap: meta.bootstrap,
            error: meta.error,
          })
        } else if (meta.type === 'kafka_unavailable') {
          setLiveFeedMeta({
            kind: 'kafka_unavailable',
            bootstrap: meta.bootstrap,
            hint: meta.hint,
          })
        } else if (meta.type === 'feed_ready') {
          setLiveFeedMeta(null)
          setLiveFeedReady(true)
        } else if (meta.type === 'sse_error') {
          setLiveFeedMeta((prev) => prev ?? { kind: 'sse_error' })
        }
      },
    )
    return () => {
      setLiveFeedMeta(null)
      setLiveFeedReady(false)
      unsubscribe()
    }
  }, [streamOn, addTransaction, gatewayReachable])

  // Sync model info when gateway becomes available
  useEffect(() => {
    if (!API_BASE || !gatewayReachable) return
    fetchModelInfo()
      .then((info) => {
        if (info) setModelInfo(info)
      })
      .catch(() => {})
  }, [gatewayReachable])

  const startParseJob = useCallback((total) => {
    setParseJob({
      running: true,
      step: 'upload',
      label: 'Uploading…',
      done: 0,
      total,
      indeterminate: false,
    })
  }, [])

  const updateParseJob = useCallback((data) => {
    setParseJob((p) => (p ? { ...p, ...data } : p))
  }, [])

  /** outcome: 'success' → Done; 'error' → keep last label (e.g. parse error message) */
  const finishParseJob = useCallback((outcome = 'success') => {
    setParseJob((p) => {
      if (!p) return p
      if (outcome === 'success') {
        return { ...p, running: false, step: 'done', label: 'Done' }
      }
      return { ...p, running: false, step: 'error' }
    })
  }, [])

  const updateModelAfterRetrain = useCallback(() => {
    if (!API_BASE) return
    // Re-fetch real model info from backend after retrain
    setTimeout(() => {
      fetchModelInfo().then((info) => {
        if (info) setModelInfo(info)
      }).catch(() => {})
    }, 2000)
  }, [])

  const value = useMemo(
    () => ({
      transactions,
      streamOn,
      setStreamOn,
      parseJob,
      startParseJob,
      updateParseJob,
      finishParseJob,
      toasts,
      dismissToast,
      addTransaction,
      correctCategory,
      markAnomalyAction,
      modelInfo,
      setModelInfo,
      correctionsTotal,
      updateModelAfterRetrain,
      pushToast,
      gatewayReachable,
      liveFeedMeta,
      liveFeedReady,
    }),
    [
      transactions,
      streamOn,
      parseJob,
      startParseJob,
      updateParseJob,
      finishParseJob,
      toasts,
      dismissToast,
      addTransaction,
      correctCategory,
      markAnomalyAction,
      modelInfo,
      correctionsTotal,
      updateModelAfterRetrain,
      pushToast,
      gatewayReachable,
      liveFeedMeta,
      liveFeedReady,
    ],
  )

  return (
    <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>
  )
}

export function useAppState() {
  const ctx = useContext(AppStateContext)
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider')
  return ctx
}
