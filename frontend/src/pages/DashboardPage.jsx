import { useMemo, useState } from 'react'
import { useThrottledValue } from '../hooks/useThrottledValue'
import {
  Calendar,
  ChartPie,
  Gauge,
  LineChart as LineChartIcon,
  ListTree,
  Store,
} from 'lucide-react'
import { useAppState } from '../context/AppStateContext'
import {
  currentMonthSpendByCategory,
  dailySpendSeries,
  donutData,
  monthlyStackData,
  suggestedBudgets,
  topMerchants,
} from '../lib/aggregates'
import { CATEGORY_BY_ID } from '../lib/categories'
import { formatCurrency, formatDateTime } from '../lib/format'
import CategoryDonut from '../components/charts/CategoryDonut'
import MonthlySpendChart from '../components/charts/MonthlySpendChart'
import DailyTimelineChart from '../components/charts/DailyTimelineChart'
import TopMerchants from '../components/charts/TopMerchants'
import BudgetBars from '../components/charts/BudgetBars'
import CategoryBadge from '../components/CategoryBadge'
import PageHeader from '../components/ui/PageHeader'

function Panel({ icon: Icon, title, subtitle, children, interactive }) {
  return (
    <div
      className={`glass-panel ${interactive ? 'glass-panel-interactive' : ''}`}
    >
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            {Icon && (
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500/20 text-sky-800 ring-1 ring-sky-400/35 dark:bg-sky-500/15 dark:text-sky-300 dark:ring-sky-400/25">
                <Icon className="h-[18px] w-[18px]" strokeWidth={2} />
              </span>
            )}
            <h2 className="font-display text-lg font-bold text-content">{title}</h2>
          </div>
          {subtitle && <p className="mt-2 text-xs leading-relaxed text-content-muted">{subtitle}</p>}
        </div>
      </div>
      {children}
    </div>
  )
}

export default function DashboardPage() {
  const { transactions } = useAppState()
  const chartTransactions = useThrottledValue(transactions, 280)
  const [activeCategory, setActiveCategory] = useState(null)

  const debitTx = useMemo(
    () => chartTransactions.filter((t) => t.debit_credit !== 'credit'),
    [chartTransactions],
  )

  const donut = useMemo(() => donutData(debitTx), [debitTx])
  const monthly = useMemo(() => monthlyStackData(debitTx, 6), [debitTx])
  const daily = useMemo(() => dailySpendSeries(debitTx), [debitTx])
  const merchants = useMemo(() => topMerchants(debitTx, 10), [debitTx])
  const budgets = useMemo(() => suggestedBudgets(debitTx), [debitTx])
  const monthSpend = useMemo(() => currentMonthSpendByCategory(debitTx), [debitTx])

  const drilldown = useMemo(() => {
    if (!activeCategory) return []
    return debitTx.filter((t) => t.category === activeCategory).slice(0, 40)
  }, [debitTx, activeCategory])

  const activeLabel = activeCategory ? CATEGORY_BY_ID[activeCategory]?.label ?? activeCategory : null

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="Analytics core"
        title="Spending intelligence"
        description="Charts hydrate from the same categorised stream as the live feed. Tap a donut slice to inspect transactions — wired for SSE snapshots in production."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          icon={ChartPie}
          title="Category mix"
          subtitle="Debit volume · click a slice to filter drilldown"
        >
          <CategoryDonut
            data={donut}
            activeId={activeCategory}
            onSliceClick={(id) => setActiveCategory((c) => (c === id ? null : id))}
          />
        </Panel>
        <Panel
          icon={ListTree}
          title={activeLabel ? `Drilldown · ${activeLabel}` : 'Category drilldown'}
          subtitle={activeLabel ? 'Latest rows for the selected slice' : 'Select a category from the donut'}
          interactive
        >
          <ul className="max-h-[320px] space-y-2 overflow-auto scrollbar-thin pr-1">
            {drilldown.map((t) => (
              <li
                key={t.txn_id}
                className="interactive-lift-sm flex items-center justify-between gap-3 rounded-xl border border-theme-subtle bg-surface-muted/40 px-3 py-2.5 text-sm transition hover:border-sky-400/45 hover:bg-sky-500/10 dark:hover:border-sky-400/20 dark:hover:bg-sky-500/5"
              >
                <span className="min-w-0 truncate font-medium text-content">{t.merchant_clean}</span>
                <span className="shrink-0 font-display text-sm font-bold tabular-nums text-sky-800 dark:text-sky-200/90">
                  {formatCurrency(t.amount)}
                </span>
              </li>
            ))}
            {!drilldown.length && (
              <li className="py-14 text-center text-sm text-content-muted">
                Pick a category to see matching transactions
              </li>
            )}
          </ul>
        </Panel>
      </div>

      <Panel
        icon={Calendar}
        title="Monthly momentum"
        subtitle="Stacked history — last 6 months refresh as events arrive"
      >
        <MonthlySpendChart data={monthly} />
      </Panel>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="glass-panel xl:col-span-2">
          <div className="mb-5 flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500/20 text-sky-800 ring-1 ring-sky-400/35 dark:bg-sky-500/15 dark:text-sky-300 dark:ring-sky-400/25">
              <LineChartIcon className="h-[18px] w-[18px]" strokeWidth={2} />
            </span>
            <div>
              <h2 className="font-display text-lg font-bold text-content">Daily rhythm</h2>
              <p className="mt-1 text-xs text-content-muted">
                Current month · <span className="font-semibold text-rose-400">red markers</span> = anomaly
                days
              </p>
            </div>
          </div>
          <DailyTimelineChart data={daily} />
        </div>
        <Panel icon={Store} title="Top merchants" subtitle="Ranked by total debit exposure">
          <TopMerchants items={merchants} />
        </Panel>
      </div>

      <Panel
        icon={Gauge}
        title="Budget pulse"
        subtitle="This period vs suggested caps (3-month trailing × 1.05)"
      >
        <BudgetBars spentByCategory={monthSpend} budgetByCategory={budgets} />
      </Panel>

      <section className="glass-panel-muted">
        <h2 className="flex items-center gap-2 text-sm font-bold text-content">
          <span className="h-2 w-2 rounded-full bg-sky-400 shadow-[0_0_10px_rgb(56_189_248/0.8)]" />
          Recent activity snapshot
        </h2>
        <ul className="mt-5 grid gap-3 sm:grid-cols-2">
          {debitTx.slice(0, 6).map((t) => (
            <li
              key={t.txn_id}
              className="card-shine group flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-theme-subtle bg-surface-elevated/70 p-4 transition hover:border-sky-400/40 hover:shadow-lg dark:bg-surface-elevated/40 dark:hover:border-sky-400/20 dark:hover:shadow-card"
            >
              <div className="min-w-0">
                <p className="truncate font-semibold text-content">{t.merchant_clean}</p>
                <p className="text-xs text-content-muted">{formatDateTime(t.date)}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <CategoryBadge categoryId={t.category} />
                <span className="font-display text-sm font-bold tabular-nums text-sky-800 dark:text-sky-200/90">
                  {formatCurrency(t.amount)}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
