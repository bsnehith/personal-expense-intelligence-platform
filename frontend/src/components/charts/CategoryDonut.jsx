import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import ChartContainer, { CHART_DIMS } from './ChartContainer'

export default function CategoryDonut({ data, activeId, onSliceClick }) {
  const chartData = data.length ? data : [{ id: 'empty', name: 'No data', value: 1, fill: '#334155' }]

  return (
    <ChartContainer dims={CHART_DIMS.donut}>
      <ResponsiveContainer
        width="100%"
        height="100%"
        minWidth={48}
        minHeight={CHART_DIMS.donut.height}
        initialDimension={CHART_DIMS.donut}
      >
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={72}
            outerRadius={112}
            paddingAngle={2}
            onClick={(_, index) => {
              const row = chartData[index]
              if (row?.id && row.id !== 'empty') onSliceClick?.(row.id)
            }}
            className="cursor-pointer outline-none"
          >
            {chartData.map((entry, index) => (
              <Cell
                key={entry.id ?? index}
                fill={entry.fill}
                stroke={activeId && entry.id === activeId ? '#fff' : 'transparent'}
                strokeWidth={activeId && entry.id === activeId ? 2 : 0}
                opacity={!activeId || entry.id === activeId || entry.id === 'empty' ? 1 : 0.45}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, name, item) => [
              typeof value === 'number' ? value.toLocaleString() : value,
              item?.payload?.name ?? name,
            ]}
            contentStyle={{
              borderRadius: 12,
              border: '1px solid rgb(51 65 85)',
              background: 'rgb(28 31 48)',
              color: '#f1f5f9',
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </ChartContainer>
  )
}
