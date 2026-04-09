/**
 * Centralised API base for the api-gateway (set VITE_API_BASE_URL in frontend/.env).
 */
export const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? ''

// ── Helpers ──────────────────────────────────────────────────────────────────

async function post(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

async function get(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ── Category correction ───────────────────────────────────────────────────────

export async function postCorrectCategory(txnId, correctCategory, txnSnapshot = null) {
  if (!API_BASE) throw new Error('VITE_API_BASE_URL is not set')
  const body = { txn_id: txnId, correct_category: correctCategory }
  if (txnSnapshot && txnSnapshot.merchant_raw != null) {
    body.merchant_raw = txnSnapshot.merchant_raw
    body.description = txnSnapshot.description ?? ''
    body.amount = txnSnapshot.amount
  }
  return post('/correct', body)
}

export async function postAnomalyAction(txnId, action, note = '') {
  if (!API_BASE) throw new Error('VITE_API_BASE_URL is not set')
  return post('/anomaly-action', { txn_id: txnId, action, note })
}

// ── Retrain ───────────────────────────────────────────────────────────────────

export async function postTriggerRetrain(mode = 'fast') {
  if (!API_BASE) throw new Error('VITE_API_BASE_URL is not set')
  const m = mode === 'best_fit' ? 'best_fit' : 'fast'
  const res = await fetch(`${API_BASE}/retrain?mode=${encodeURIComponent(m)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ── Model info ────────────────────────────────────────────────────────────────

export async function fetchModelInfo() {
  if (!API_BASE) return null
  return get('/model-info')
}

/** True if the api-gateway responds at GET /health (e.g. Docker stack running). */
export async function checkGatewayHealth() {
  if (!API_BASE) return false
  const ctrl = new AbortController()
  const t = window.setTimeout(() => ctrl.abort(), 5000)
  try {
    const r = await fetch(`${API_BASE}/health`, {
      method: 'GET',
      cache: 'no-store',
      signal: ctrl.signal,
    })
    return r.ok
  } catch {
    return false
  } finally {
    window.clearTimeout(t)
  }
}

// ── Live feed SSE ─────────────────────────────────────────────────────────────

/**
 * Opens an SSE connection to GET /feed/stream.
 * Calls onTransaction(txn) for each categorised transaction event.
 * onMeta (optional): gateway connection phases — waiting for Kafka, or Kafka unavailable.
 * Returns a cleanup function.
 */
export function subscribeToFeed(onTransaction, onMeta) {
  if (!API_BASE) return () => {}

  onMeta?.({ type: 'connecting' })

  const es = new EventSource(`${API_BASE}/feed/stream`)

  es.onmessage = (e) => {
    try {
      const payload = JSON.parse(e.data)
      // Gateway meta when Kafka is down or still starting (see api-gateway main.py feed_stream)
      if (payload.feed_event === 'waiting') {
        onMeta?.({ type: 'waiting_kafka', bootstrap: payload.bootstrap, error: payload.error })
        return
      }
      if (payload.feed_event === 'unavailable') {
        onMeta?.({ type: 'kafka_unavailable', bootstrap: payload.bootstrap, hint: payload.hint })
        return
      }
      if (payload.feed_event === 'ready') {
        onMeta?.({ type: 'feed_ready', topic: payload.topic })
        return
      }
      onTransaction(payload)
    } catch {
      // ignore malformed events
    }
  }

  es.onerror = () => {
    onMeta?.({ type: 'sse_error' })
    // EventSource auto-reconnects; avoid console noise in dev
  }

  return () => es.close()
}

// ── Statement upload with SSE progress ────────────────────────────────────────

/**
 * Uploads a file to POST /upload and streams SSE progress events.
 * Uses XMLHttpRequest so we can report upload byte progress (fetch has no upload progress).
 * onProgress({ step, label, done, total, txn?, indeterminate?, ... }) for each event.
 */
export function uploadStatement(file, onProgress) {
  if (!API_BASE) {
    return Promise.reject(new Error('No API_BASE configured'))
  }

  const formData = new FormData()
  formData.append('file', file)

  const uploadTimeoutMs = 1_800_000

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    let lineBuf = ''
    let responseProcessed = 0
    let sawTerminal = false

    const applySseLine = (rawLine) => {
      const trimmed = rawLine.replace(/^\uFEFF/, '').trim()
      if (!trimmed.startsWith('data: ')) return false
      try {
        const data = JSON.parse(trimmed.slice(6))
        onProgress(data)
        return data.step === 'done' || data.step === 'error'
      } catch {
        return false
      }
    }

    const drainSseFromResponse = () => {
      const full = xhr.responseText
      const chunk = full.slice(responseProcessed)
      responseProcessed = full.length
      lineBuf += chunk
      const lines = lineBuf.split(/\r?\n/)
      lineBuf = lines.pop() ?? ''
      for (const line of lines) {
        if (applySseLine(line)) sawTerminal = true
      }
    }

    const tid = window.setTimeout(() => {
      xhr.abort()
    }, uploadTimeoutMs)

    xhr.upload.addEventListener('progress', (e) => {
      if (!e.lengthComputable) return
      const pct = Math.max(0, Math.min(100, Math.round((e.loaded / e.total) * 100)))
      onProgress({
        step: 'upload',
        label: `Sending file to server… ${pct}%`,
        done: e.loaded,
        total: e.total,
      })
    })

    xhr.onreadystatechange = () => {
      if (xhr.readyState === 3 || xhr.readyState === 4) {
        drainSseFromResponse()
      }
      if (xhr.readyState === 4) {
        window.clearTimeout(tid)
        if (xhr.status === 0) {
          onProgress({
            step: 'error',
            label: 'Upload cancelled or network error.',
            done: 0,
            total: 0,
          })
          reject(new Error('Upload cancelled'))
          return
        }
        if (xhr.status < 200 || xhr.status >= 300) {
          const errText = xhr.responseText || xhr.statusText || 'Upload failed'
          reject(new Error(errText))
          return
        }
        for (const line of lineBuf.split(/\r?\n/)) {
          if (applySseLine(line)) sawTerminal = true
        }
        lineBuf = ''
        if (!sawTerminal) {
          onProgress({
            step: 'error',
            label:
              'Upload stream ended without a completion event. Check gateway + parser-service (docker compose up) and VITE_API_BASE_URL.',
            done: 0,
            total: 0,
          })
        }
        resolve()
      }
    }

    xhr.open('POST', `${API_BASE}/upload`)
    xhr.send(formData)
  })
}

// ── GenAI Coach SSE streaming ─────────────────────────────────────────────────

/**
 * Streams a chat response from the GenAI coach.
 * onToken(string) called for each token.
 * Returns a promise that resolves when streaming ends.
 */
export async function streamCoachChat(question, transactions, onToken) {
  if (!API_BASE) return

  const res = await fetch(`${API_BASE}/coach/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, transactions }),
  })
  if (!res.ok) throw new Error(await res.text())

  await _consumeTokenStream(res, onToken)
}

export async function streamMonthlyReport(transactions, onToken) {
  if (!API_BASE) return

  const res = await fetch(`${API_BASE}/coach/monthly/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transactions }),
  })
  if (!res.ok) throw new Error(await res.text())
  await _consumeTokenStream(res, onToken)
}

/**
 * Streams statement-upload summary (same SSE shape as coach chat).
 * Spec: auto-trigger GenAI summary after a statement is fully categorised.
 */
export async function streamStatementSummary(transactions, sourceFile, onToken) {
  if (!API_BASE) return

  const res = await fetch(`${API_BASE}/coach/statement`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transactions, source_file: sourceFile }),
  })
  if (!res.ok) throw new Error(await res.text())

  await _consumeTokenStream(res, onToken)
}

async function _consumeTokenStream(res, onToken) {
  const reader = res.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split(/\r?\n/)
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data: ')) continue
      try {
        const j = JSON.parse(trimmed.slice(6))
        if (j.done) return
        if (j.token) onToken(j.token)
      } catch {
        /* ignore */
      }
    }
  }
}
