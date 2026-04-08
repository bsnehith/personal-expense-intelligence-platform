import { TrendingUp } from 'lucide-react'
import { formatPercent } from '../lib/format'

export default function ConfidenceBadge({ value, className = '' }) {
  const high = value >= 0.8
  const mid = value >= 0.65
  const cls = high
    ? 'border-emerald-400/35 bg-emerald-500/12 text-emerald-200 ring-emerald-400/20'
    : mid
      ? 'border-amber-400/35 bg-amber-500/12 text-amber-100 ring-amber-400/15'
      : 'border-rose-400/35 bg-rose-500/12 text-rose-100 ring-rose-400/15'
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-bold tabular-nums ${cls} ${className}`}
      title="Model confidence"
    >
      <TrendingUp className="h-3 w-3 opacity-80" strokeWidth={2.5} aria-hidden />
      {formatPercent(value)}
    </span>
  )
}
