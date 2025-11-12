import { Card } from "@/components/ui/card"
import type { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"

interface MetricCardProps {
  title: string
  value: string
  subtitle?: string
  change?: string
  trend?: "up" | "down" | "neutral"
  icon: LucideIcon
  accentColor?: "qrie-orange" | "qrie-purple"
}

export function MetricCard({ title, value, subtitle, change, trend, icon: Icon, accentColor }: MetricCardProps) {
  return (
    <Card className="p-6 bg-card border-border">
      <div className="flex items-start justify-between">
        <div className="space-y-3 flex-1">
          <p className="text-sm text-muted-foreground">{title}</p>
          <div className="space-y-1">
            <p className="text-3xl font-semibold text-balance">{value}</p>
            {subtitle ? (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            ) : change ? (
              <p
                className={cn(
                  "text-xs",
                  trend === "up" && "text-qrie-orange",
                  trend === "down" && "text-chart-2",
                  trend === "neutral" && "text-muted-foreground",
                  !trend && "text-muted-foreground",
                )}
              >
                {change}
              </p>
            ) : null}
            {/* </CHANGE> */}
          </div>
        </div>
        <div
          className={cn(
            "p-2.5 rounded-lg",
            accentColor === "qrie-orange" && "bg-qrie-orange/10",
            accentColor === "qrie-purple" && "bg-qrie-purple/10",
            !accentColor && "bg-secondary",
          )}
        >
          <Icon
            className={cn(
              "h-5 w-5",
              accentColor === "qrie-orange" && "text-qrie-orange",
              accentColor === "qrie-purple" && "text-qrie-purple",
              !accentColor && "text-muted-foreground",
            )}
          />
        </div>
      </div>
    </Card>
  )
}
