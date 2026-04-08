/** 12-category taxonomy + Uncategorised (project spec §3.3) */
export const CATEGORIES = [
  {
    id: 'food_dining',
    label: 'Food & Dining',
    chartColor: '#f97316',
    tw: 'bg-orange-500/15 text-orange-300 border-orange-500/30',
  },
  {
    id: 'transport',
    label: 'Transport',
    chartColor: '#3b82f6',
    tw: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  },
  {
    id: 'shopping',
    label: 'Shopping',
    chartColor: '#a855f7',
    tw: 'bg-violet-500/15 text-violet-300 border-violet-500/30',
  },
  {
    id: 'housing',
    label: 'Housing',
    chartColor: '#eab308',
    tw: 'bg-yellow-500/15 text-yellow-200 border-yellow-500/30',
  },
  {
    id: 'health_medical',
    label: 'Health & Medical',
    chartColor: '#22c55e',
    tw: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  },
  {
    id: 'entertainment',
    label: 'Entertainment',
    chartColor: '#ec4899',
    tw: 'bg-pink-500/15 text-pink-300 border-pink-500/30',
  },
  {
    id: 'travel',
    label: 'Travel',
    chartColor: '#06b6d4',
    tw: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
  },
  {
    id: 'education',
    label: 'Education',
    chartColor: '#6366f1',
    tw: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
  },
  {
    id: 'finance',
    label: 'Finance',
    chartColor: '#64748b',
    tw: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  },
  {
    id: 'subscriptions',
    label: 'Subscriptions',
    chartColor: '#14b8a6',
    tw: 'bg-teal-500/15 text-teal-300 border-teal-500/30',
  },
  {
    id: 'family_personal',
    label: 'Family & Personal',
    chartColor: '#f43f5e',
    tw: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  },
  {
    id: 'uncategorised',
    label: 'Uncategorised',
    chartColor: '#94a3b8',
    tw: 'bg-slate-600/30 text-slate-400 border-slate-500/25',
  },
]

export const CATEGORY_BY_ID = Object.fromEntries(
  CATEGORIES.map((c) => [c.id, c]),
)

export const CATEGORY_BY_LABEL = Object.fromEntries(
  CATEGORIES.map((c) => [c.label, c]),
)

export function categoryStyle(categoryId) {
  return CATEGORY_BY_ID[categoryId]?.tw ?? CATEGORY_BY_ID.uncategorised.tw
}

export function categoryColor(categoryId) {
  return CATEGORY_BY_ID[categoryId]?.chartColor ?? '#94a3b8'
}
