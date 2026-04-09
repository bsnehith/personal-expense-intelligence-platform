import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatCurrency } from '../../lib/format'
import ChartContainer, { CHART_DIMS } from './ChartContainer'

export default function WeekdaySpendChart({ data, activeWeekday, onSelectWeekday }) {
  return (
    <ChartContainer dims={CHART_DIMS.weekday}>
      <ResponsiveContainer
        width="100%"
        height="100%"
        minWidth={48}
        minHeight={CHART_DIMS.weekday.height}
        initialDimension={CHART_DIMS.weekday}
      >
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--border))" opacity={0.35} />
          <XAxis dataKey="weekday" tick={{ fill: 'rgb(var(--content-muted))', fontSize: 11 }} />
          <YAxis tick={{ fill: 'rgb(var(--content-muted))', fontSize: 11 }} />
          <Tooltip
            formatter={(value, _name, item) => {
              if (item?.dataKey === 'spend') return [formatCurrency(Number(value) || 0), 'Total spend']
              return [value, 'Transactions']
            }}
            labelFormatter={(label) => `${label}`}
            contentStyle={{
              borderRadius: 12,
              border: '1px solid rgb(51 65 85)',
              background: 'rgb(28 31 48)',
              color: '#f1f5f9',
            }}
          />
          <Bar
            dataKey="spend"
            radius={[8, 8, 0, 0]}
            onClick={(row) => onSelectWeekday?.(row?.weekdayIndex)}
            className="cursor-pointer"
          >
            {data.map((row) => {
              const selected = activeWeekday == null || activeWeekday === row.weekdayIndex
              return (
                <Cell
                  key={row.weekday}
                  fill={selected ? '#38bdf8' : '#94a3b8'}
                  opacity={selected ? 1 : 0.45}
                />
              )
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartContainer>
  )
}
