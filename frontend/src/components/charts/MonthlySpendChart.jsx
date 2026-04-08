import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { CATEGORIES } from '../../lib/categories'
import ChartContainer, { CHART_DIMS } from './ChartContainer'

export default function MonthlySpendChart({ data }) {
  return (
    <ChartContainer dims={CHART_DIMS.monthly}>
      <ResponsiveContainer
        width="100%"
        height="100%"
        minWidth={48}
        minHeight={CHART_DIMS.monthly.height}
        initialDimension={CHART_DIMS.monthly}
      >
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--border))" opacity={0.35} />
          <XAxis dataKey="month" tick={{ fill: 'rgb(var(--content-muted))', fontSize: 11 }} />
          <YAxis tick={{ fill: 'rgb(var(--content-muted))', fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              borderRadius: 12,
              border: '1px solid rgb(51 65 85)',
              background: 'rgb(28 31 48)',
              color: '#f1f5f9',
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {CATEGORIES.map((c) => (
            <Bar
              key={c.id}
              dataKey={c.id}
              stackId="spend"
              fill={c.chartColor}
              name={c.label}
              isAnimationActive
              animationDuration={450}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartContainer>
  )
}
