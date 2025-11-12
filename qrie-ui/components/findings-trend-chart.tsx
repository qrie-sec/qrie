"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Bar, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Legend, ComposedChart, LabelList } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { getDashboardSummary } from "@/lib/api"

interface TrendData {
  date: string
  openFindings: number
  closedFindings: number
  activePolicies: number
}

export function FindingsTrendChart() {
  const [data, setData] = useState<TrendData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        
        // Get dashboard summary with weekly trends
        const today = new Date()
        const dateStr = today.toISOString().split('T')[0]
        const summary = await getDashboardSummary(dateStr)
        
        // Transform weekly findings data for chart
        const trendData: TrendData[] = summary.findings_weekly.map(week => {
          const weekDate = new Date(week.week_start)
          return {
            date: weekDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
            openFindings: week.open_findings,
            closedFindings: week.closed_findings,
            activePolicies: summary.active_policies
          }
        })
        
        setData(trendData)
      } catch (error) {
        console.error("Failed to load trend data:", error)
        setData([])
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) {
    return (
      <Card className="p-6 bg-card border-border">
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold">Findings Trend</h3>
            <p className="text-sm text-muted-foreground mt-1">Loading...</p>
          </div>
        </div>
      </Card>
    )
  }

  if (data.length === 0) {
    return (
      <Card className="p-6 bg-card border-border">
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold">Findings Trend</h3>
            <p className="text-sm text-muted-foreground mt-1">No data available</p>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-6 bg-card border-border">
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold">Findings Trend</h3>
          <p className="text-sm text-muted-foreground mt-1">Last 8 weeks</p>
        </div>

        <div className="flex justify-center">
          <ChartContainer
            config={{
              activePolicies: {
                label: "Active Policies",
                color: "#735177",
              },
              openFindings: {
                label: "Open Findings",
                color: "#e67e50",
              },
              closedFindings: {
                label: "Closed Findings",
                color: "#94a3b8", // Changed from #64748b to lighter slate for better visibility in dark mode
              },
            }}
            className="h-[350px] w-full max-w-5xl"
          >
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  yAxisId="left"
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  label={{
                    value: "Findings",
                    angle: -90,
                    position: "insideLeft",
                    style: { fontSize: 12, fill: "hsl(var(--muted-foreground))" },
                  }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  label={{
                    value: "Policies",
                    angle: 90,
                    position: "insideRight",
                    style: { fontSize: 12, fill: "hsl(var(--muted-foreground))" },
                  }}
                />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Legend
                  wrapperStyle={{ fontSize: "12px", paddingTop: "20px" }}
                  iconType="line"
                  iconSize={16}
                  formatter={(value) => {
                    if (value === "activePolicies") return "Active Policies"
                    if (value === "openFindings") return "Open Findings"
                    if (value === "closedFindings") return "Closed Findings"
                    return value
                  }}
                />
                <Bar yAxisId="right" dataKey="activePolicies" fill="#735177" radius={[4, 4, 0, 0]}>
                  <LabelList
                    dataKey="activePolicies"
                    position="top"
                    style={{ fontSize: 11, fill: "hsl(var(--foreground))" }}
                  />
                </Bar>
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="openFindings"
                  stroke="#e67e50"
                  strokeWidth={2}
                  dot={{ fill: "#e67e50", r: 4 }}
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="closedFindings"
                  stroke="#94a3b8"
                  strokeWidth={2}
                  dot={{ fill: "#94a3b8", r: 4 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </ChartContainer>
        </div>
      </div>
    </Card>
  )
}
