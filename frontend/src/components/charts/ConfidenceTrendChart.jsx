import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCurrency } from '../../lib/format'
import ChartContainer, { CHART_DIMS } from './ChartContainer'

export default function ConfidenceTrendChart({ data }) {
  return (
    <ChartContainer dims={CHART_DIMS.confidence}>
      <ResponsiveContainer
        width="100%"
        height="100%"
        minWidth={48}
        minHeight={CHART_DIMS.confidence.height}
        initialDimension={CHART_DIMS.confidence}
      >
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="confidenceFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.5} />
              <stop offset="100%" stopColor="#22d3ee" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--border))" opacity={0.35} />
          <XAxis dataKey="day" tick={{ fill: 'rgb(var(--content-muted))', fontSize: 11 }} />
          <YAxis
            yAxisId="confidence"
            domain={[0, 1]}
            tick={{ fill: 'rgb(var(--content-muted))', fontSize: 11 }}
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
          />
          <YAxis
            yAxisId="spend"
            orientation="right"
            hide
            tick={{ fill: 'rgb(var(--content-muted))', fontSize: 11 }}
          />
          <Tooltip
            formatter={(value, _name, item) => {
              if (item?.dataKey === 'confidence') return [`${Math.round((Number(value) || 0) * 100)}%`, 'Avg confidence']
              if (item?.dataKey === 'spend') return [formatCurrency(Number(value) || 0), 'Spend']
              return [value, item?.name]
            }}
            contentStyle={{
              borderRadius: 12,
              border: '1px solid rgb(51 65 85)',
              background: 'rgb(28 31 48)',
              color: '#f1f5f9',
            }}
          />
          <ReferenceLine
            y={0.8}
            yAxisId="confidence"
            stroke="#f59e0b"
            strokeDasharray="4 4"
            label={{ value: '80%', position: 'insideTopLeft', fill: '#f59e0b', fontSize: 11 }}
          />
          <Area
            yAxisId="confidence"
            type="monotone"
            dataKey="confidence"
            stroke="#22d3ee"
            fill="url(#confidenceFill)"
            strokeWidth={2}
            isAnimationActive
            animationDuration={450}
          />
          <Area
            yAxisId="spend"
            type="monotone"
            dataKey="spend"
            stroke="#a78bfa"
            fill="#a78bfa22"
            strokeWidth={1.2}
            isAnimationActive
            animationDuration={450}
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartContainer>
  )
}
