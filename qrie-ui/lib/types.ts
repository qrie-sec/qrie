// API Response Types

export interface WeeklyFindings {
  week_start: string
  total_findings: number
  open_findings: number
  new_findings: number
  closed_findings: number
  critical_new: number
  is_current: boolean
}

export interface TopPolicy {
  policy_id: string
  open_findings: number
  severity: number
}

export interface DashboardSummary {
  // Current counts
  total_open_findings: number
  critical_open_findings: number
  high_open_findings: number
  resolved_this_month: number
  active_policies: number
  resources: number
  accounts: number
  
  // Weekly trends (8 weeks)
  findings_weekly: WeeklyFindings[]
  
  // Top policies
  top_policies: TopPolicy[]
  
  // Month metrics
  policies_launched_this_month: number
}

export interface Account {
  account_id: string
  ou?: string
}

export interface ScopeConfig {
  include_accounts: string[] // 12-digit AWS account IDs
  exclude_accounts: string[] // 12-digit AWS account IDs
  include_tags: Record<string, string[]> // Tag key to array of values
  exclude_tags: Record<string, string[]> // Tag key to array of values
  include_ou_paths: string[] // AWS Organizations OU paths
  exclude_ou_paths: string[] // AWS Organizations OU paths
}

export interface Policy {
  // Core fields (always present)
  policy_id: string // Policy identifier
  description: string // Policy description
  service: string // AWS service (e.g., "s3", "ec2")
  category: string // Policy category (e.g., "encryption", "access_control")
  severity: number // 0-100 numeric severity
  remediation: string // Remediation instructions
  status: "active" | "available" // Policy status
  
  // Optional fields (present for launched policies only)
  scope?: ScopeConfig | null // Targeting configuration (null/undefined if unlaunched)
  open_findings?: number // Count of ACTIVE findings (undefined if unlaunched)
  created_at?: string | null // ISO date (YYYY-MM-DD) or null/undefined if unlaunched
  updated_at?: string | null // ISO date (YYYY-MM-DD) or null/undefined if unlaunched
}

// Type guards for type-safe narrowing
export function isLaunchedPolicy(policy: Policy): policy is Policy & {
  scope: ScopeConfig
  open_findings: number
  created_at: string
  updated_at: string
  status: "active"
} {
  return policy.status === "active"
}

export function isAvailablePolicy(policy: Policy): boolean {
  return policy.status === "available"
}

export function isActivePolicy(policy: Policy): boolean {
  return policy.status === "active"
}

export interface Service {
  service_name: string
  display_name: string
}

export interface Finding {
  arn: string
  policy: string
  account_service: string
  severity: number // Changed from string to number (0-100)
  state: "ACTIVE" | "RESOLVED"
  first_seen: string
  last_evaluated: string
  evidence?: Record<string, any>
}

export interface Resource {
  account_service: string
  arn: string
  last_seen_at: string
  configuration?: Record<string, any>
}

export interface FindingsSummary {
  total_findings: number
  open_findings: number
  resolved_findings: number
  critical_findings: number  // ACTIVE findings with severity >= 90
  high_findings: number       // ACTIVE findings with severity 50-89
  medium_findings: number     // ACTIVE findings with severity 25-49
  low_findings: number        // ACTIVE findings with severity 0-24
  policies: Array<{
    policy: string
    severity: number
    total_findings: number
    open_findings: number
    resolved_findings: number
  }>
}

export interface ResourcesSummary {
  total_resources: number
  total_findings: number
  critical_findings: number
  high_findings: number
  resource_types: Array<{
    resource_type: string
    all_resources: number
    non_compliant: number
  }>
}
