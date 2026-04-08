import { CATEGORY_BY_ID, categoryStyle } from '../lib/categories'

export default function CategoryBadge({ categoryId, className = '' }) {
  const label = CATEGORY_BY_ID[categoryId]?.label ?? categoryId
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide shadow-sm backdrop-blur-sm ${categoryStyle(categoryId)} ${className}`}
    >
      {label}
    </span>
  )
}
