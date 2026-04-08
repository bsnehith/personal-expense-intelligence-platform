import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import ChartContainer, { CHART_DIMS } from './ChartContainer'

function Dot(props) {
  const { cx, cy, payload } = props
  if (cx == null || cy == null) return null
  const r = payload?.anomaly ? 5 : 3
  const fill = payload?.anomaly ? '#f43f5e' : '#38bdf8'
  return <circle cx={cx} cy={cy} r={r} fill={fill} stroke="rgb(15 17 28)" strokeWidth={1} />
}

export default function DailyTimelineChart({ data }) {
  return (
    <ChartContainer dims={CHART_DIMS.daily}>
      <ResponsiveContainer
        width="100%"
        height="100%"
        minWidth={48}
        minHeight={CHART_DIMS.daily.height}
        initialDimension={CHART_DIMS.daily}
      >
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--border))" opacity={0.35} />
          <XAxis
            dataKey="day"
            tick={{ fill: 'rgb(var(--content-muted))', fontSize: 11 }}
            label={{ value: 'Day of month', position: 'insideBottom', offset: -4, fill: '#64748b' }}
          />
          <YAxis tick={{ fill: 'rgb(var(--content-muted))', fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              borderRadius: 12,
              border: '1px solid rgb(51 65 85)',
              background: 'rgb(28 31 48)',
              color: '#f1f5f9',
            }}
            labelFormatter={(d) => `Day ${d}`}
            formatter={(value, _n, item) => [
              typeof value === 'number' ? value.toLocaleString() : value,
              item?.payload?.anomaly ? 'Spend (anomaly day)' : 'Spend',
            ]}
          />
          <Line
            type="monotone"
            dataKey="spend"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={<Dot />}
            activeDot={{ r: 6 }}
            isAnimationActive
            animationDuration={450}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartContainer>
  )
}
