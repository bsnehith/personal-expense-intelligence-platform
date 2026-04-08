import { CATEGORIES } from './categories'

export function totalsByCategory(transactions) {
  const m = Object.fromEntries(CATEGORIES.map((c) => [c.id, 0]))
  for (const t of transactions) {
    if (t.debit_credit === 'credit') continue
    m[t.category] = (m[t.category] ?? 0) + t.amount
  }
  return m
}

export function currentMonthSpendByCategory(transactions) {
  const now = new Date()
  const y = now.getFullYear()
  const mo = now.getMonth()
  return totalsByCategory(
    transactions.filter((t) => {
      const d = new Date(t.date)
      return d.getFullYear() === y && d.getMonth() === mo
    }),
  )
}

export function donutData(transactions) {
  const totals = totalsByCategory(transactions)
  return CATEGORIES.map((c) => ({
    id: c.id,
    name: c.label,
    value: totals[c.id] || 0,
    fill: c.chartColor,
  })).filter((d) => d.value > 0)
}

/** Last N calendar months, stacked by category */
export function monthlyStackData(transactions, monthsBack = 6) {
  const now = new Date()
  const keys = []
  for (let i = monthsBack - 1; i >= 0; i -= 1) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    keys.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
  }
  const byMonthCat = Object.fromEntries(
    keys.map((k) => [k, Object.fromEntries(CATEGORIES.map((c) => [c.id, 0]))]),
  )
  for (const t of transactions) {
    if (t.debit_credit === 'credit') continue
    const d = new Date(t.date)
    const k = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    if (!byMonthCat[k]) continue
    const row = byMonthCat[k]
    row[t.category] = (row[t.category] ?? 0) + t.amount
  }
  return keys.map((k) => {
    const row = { month: k, ...byMonthCat[k] }
    return row
  })
}

export function dailySpendSeries(transactions) {
  const now = new Date()
  const y = now.getFullYear()
  const m = now.getMonth()
  const daysInMonth = new Date(y, m + 1, 0).getDate()
  const byDay = Object.fromEntries(
    Array.from({ length: daysInMonth }, (_, i) => [String(i + 1), 0]),
  )
  const anomalyDays = new Set()
  for (const t of transactions) {
    if (t.debit_credit === 'credit') continue
    const d = new Date(t.date)
    if (d.getFullYear() !== y || d.getMonth() !== m) continue
    const day = String(d.getDate())
    byDay[day] = (byDay[day] ?? 0) + t.amount
    if (t.anomaly) anomalyDays.add(day)
  }
  return Array.from({ length: daysInMonth }, (_, i) => {
    const day = String(i + 1)
    return {
      day: i + 1,
      label: day,
      spend: byDay[day] ?? 0,
      anomaly: anomalyDays.has(day),
    }
  })
}

export function topMerchants(transactions, n = 10) {
  const m = new Map()
  for (const t of transactions) {
    if (t.debit_credit === 'credit') continue
    const key = t.merchant_clean
    const prev = m.get(key) ?? { name: key, total:      0, category: t.category }
    prev.total += t.amount
    m.set(key, prev)
  }
  return [...m.values()]
    .sort((a, b) => b.total - a.total)
    .slice(0, n)
}

/** Suggested budget ≈ 3-month rolling average monthly spend × 1.05 */
export function suggestedBudgets(transactions) {
  const cutoff = Date.now() - 90 * 86400000
  const recent = transactions.filter((t) => new Date(t.date).getTime() >= cutoff)
  const totals = totalsByCategory(recent)
  return Object.fromEntries(
    CATEGORIES.map((c) => {
      const monthlyAvg = totals[c.id] / 3
      return [c.id, Math.max(monthlyAvg * 1.05, 1)]
    }),
  )
}
