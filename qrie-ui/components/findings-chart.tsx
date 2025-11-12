"use client"

import { Card } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Line, LineChart, XAxis, YAxis, CartesianGrid, Legend } from "recharts"

const data = [
  { date: "Week 1", open: 189, closed: 1650, active: 42 },
  { date: "Week 2", open: 203, closed: 1689, active: 43 },
  { date: "Week 3", open: 221, closed: 1734, active: 44 },
  { date: "Week 4", open: 247, closed: 1834, active: 45 },
]

const chartConfig = {
  open: {
    label: "Open Findings",
    color: "hsl(var(--qrie-orange))",
  },
  closed: {
    label: "Closed Findings",
    color: "hsl(var(--chart-2))",
  },
  active: {
    label: "Active Policies",
    color: "hsl(var(--qrie-purple))",
  },
}

export function FindingsChart() {
  return (
    <Card className="p-6 bg-card border-border">
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-semibold">Trends (Last Month)</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Open findings, closed findings, and active policies over time
          </p>
        </div>
        <ChartContainer config={chartConfig} className="h-[300px] w-full">
          <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} />
            <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Legend
              wrapperStyle={{
                paddingTop: "20px",
                fontSize: "12px",
              }}
            />
            <Line
              type="monotone"
              dataKey="open"
              stroke="hsl(var(--qrie-orange))"
              strokeWidth={2}
              dot={false}
              name="Open Findings"
            />
            <Line
              type="monotone"
              dataKey="closed"
              stroke="hsl(var(--chart-2))"
              strokeWidth={2}
              dot={false}
              name="Closed Findings"
            />
            <Line
              type="monotone"
              dataKey="active"
              stroke="hsl(var(--qrie-purple))"
              strokeWidth={2}
              dot={false}
              name="Active Policies"
            />
          </LineChart>
        </ChartContainer>
      </div>
    </Card>
  )
}
