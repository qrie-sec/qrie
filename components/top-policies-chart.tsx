"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Bar, BarChart, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { getDashboardSummary } from "@/lib/api"
import type { TopPolicy } from "@/lib/types"

interface PolicyData {
  policy: string
  openFindings: number
}

export function TopPoliciesChart() {
  const [data, setData] = useState<PolicyData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        
        // Get dashboard summary with top policies
        const today = new Date()
        const dateStr = today.toISOString().split('T')[0]
        const summary = await getDashboardSummary(dateStr)
        
        // Transform top policies data for chart
        const topPolicies = summary.top_policies.map((p: TopPolicy) => ({
          policy: p.policy_id,
          openFindings: p.open_findings
        }))
        
        setData(topPolicies)
      } catch (error) {
        console.error("Failed to load top policies data:", error)
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
            <h3 className="text-lg font-semibold">Top 10 Policies by Open Findings</h3>
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
            <h3 className="text-lg font-semibold">Top 10 Policies by Open Findings</h3>
            <p className="text-sm text-muted-foreground mt-1">No open findings found</p>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-6 bg-card border-border">
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold">Top 10 Policies by Open Findings</h3>
          <p className="text-sm text-muted-foreground mt-1">Sorted by open findings count</p>
        </div>

        <div className="flex justify-center">
          <ChartContainer
            config={{
              openFindings: {
                label: "Open Findings",
                color: "#735177",
              },
            }}
            className="h-[400px] w-full max-w-3xl"
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} layout="vertical" margin={{ left: 120, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                <XAxis
                  type="number"
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="policy"
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  width={110}
                />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="openFindings" fill="#735177" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartContainer>
        </div>
      </div>
    </Card>
  )
}
