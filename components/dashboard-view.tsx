"use client"

import { useEffect, useState } from "react"
import { MetricCard } from "@/components/metric-card"
import { FindingsTrendChart } from "@/components/findings-trend-chart"
import { TopPoliciesChart } from "@/components/top-policies-chart"
import { AlertTriangle, CheckCircle2 } from "lucide-react"
import { getDashboardSummary } from "@/lib/api"
import type { DashboardSummary } from "@/lib/types"

export function DashboardView() {
  const [dashboardData, setDashboardData] = useState<DashboardSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchDashboard() {
      setLoading(true)
      const data = await getDashboardSummary()
      setDashboardData(data)
      setLoading(false)
    }
    fetchDashboard()
  }, [])

  if (loading || !dashboardData) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-semibold text-balance">Dashboard</h1>
          <p className="mt-2 text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  const latestWeeklyFindings = dashboardData.findings_weekly?.[dashboardData.findings_weekly.length - 1]
  const newFindingsThisWeek = latestWeeklyFindings?.new_findings ?? 0
  const criticalNewThisWeek = latestWeeklyFindings?.critical_new ?? 0

  return (
    <div className="space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="text-3xl font-semibold text-balance">Dashboard</h1>
        <p className="mt-2 text-muted-foreground">Security posture overview and compliance metrics</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Open Findings"
          value={String(dashboardData.total_open_findings ?? 0)}
          change={`+${newFindingsThisWeek} new this week`}
          trend="up"
          icon={AlertTriangle}
          accentColor="qrie-orange"
        />
        <MetricCard
          title="Critical Open"
          value={String(dashboardData.critical_open_findings ?? 0)}
          change={`+${criticalNewThisWeek} new this week`}
          trend="up"
          icon={AlertTriangle}
          accentColor="qrie-orange"
        />
        <MetricCard
          title="High Open"
          value={String(dashboardData.high_open_findings ?? 0)}
          change={`Severity 50-89`}
          trend="neutral"
          icon={AlertTriangle}
          accentColor="qrie-orange"
        />
        <MetricCard
          title="Resolved This Month"
          value={String(dashboardData.resolved_this_month ?? 0)}
          subtitle={`${dashboardData.accounts ?? 0} Accounts`}
          icon={CheckCircle2}
          accentColor="qrie-purple"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-1">
        <FindingsTrendChart />
      </div>

      <div className="grid gap-6 lg:grid-cols-1">
        <TopPoliciesChart />
      </div>
    </div>
  )
}
