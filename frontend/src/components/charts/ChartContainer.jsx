/**
 * Wrapper + defaults so Recharts ResponsiveContainer never starts at -1×-1
 * (avoids console warnings before ResizeObserver fires).
 */
export const CHART_DIMS = {
  donut: { width: 480, height: 320 },
  monthly: { width: 640, height: 340 },
  daily: { width: 640, height: 300 },
  weekday: { width: 560, height: 290 },
  confidence: { width: 560, height: 290 },
}

export default function ChartContainer({ dims, children }) {
  return (
    <div
      className="w-full min-w-0"
      style={{
        height: dims.height,
        minHeight: dims.height,
      }}
    >
      {children}
    </div>
  )
}
