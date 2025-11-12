"use client"

import { Card } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Bar, BarChart, XAxis, YAxis, CartesianGrid, Legend } from "recharts"

const data = [
  { policy: "S3BucketPublic", open: 45, closed: 234 },
  { policy: "UnencryptedEBS", open: 38, closed: 189 },
  { policy: "OpenSecurityGroup", open: 32, closed: 156 },
  { policy: "IAMPasswordPolicy", open: 28, closed: 98 },
  { policy: "UnusedAccessKeys", open: 24, closed: 145 },
  { policy: "MFANotEnabled", open: 21, closed: 87 },
  { policy: "PublicRDSSnapshot", open: 18, closed: 76 },
  { policy: "UnencryptedS3", open: 15, closed: 123 },
  { policy: "CloudTrailDisabled", open: 12, closed: 54 },
  { policy: "RootAccountUsage", open: 8, closed: 32 },
]

const chartConfig = {
  open: {
    label: "Open",
    color: "hsl(var(--qrie-orange))",
  },
  closed: {
    label: "Closed",
    color: "hsl(var(--chart-2))",
  },
}

export function FindingsByPolicyChart() {
  return (
    <Card className="p-6 bg-card border-border">
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-semibold">Findings by Policy</h3>
          <p className="text-sm text-muted-foreground mt-1">Distribution of open and closed findings across policies</p>
        </div>
        <ChartContainer config={chartConfig} className="h-[400px] w-full">
          <BarChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 80 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              dataKey="policy"
              stroke="hsl(var(--muted-foreground))"
              fontSize={11}
              tickLine={false}
              angle={-45}
              textAnchor="end"
              height={100}
            />
            <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Legend
              wrapperStyle={{
                paddingTop: "10px",
                fontSize: "12px",
              }}
            />
            <Bar dataKey="open" fill="hsl(var(--qrie-orange))" radius={[4, 4, 0, 0]} name="Open" />
            <Bar dataKey="closed" fill="hsl(var(--chart-2))" radius={[4, 4, 0, 0]} name="Closed" />
          </BarChart>
        </ChartContainer>
      </div>
    </Card>
  )
}
