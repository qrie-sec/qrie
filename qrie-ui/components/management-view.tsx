"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Play, Settings, Loader2 } from "lucide-react"
import { getPolicies, getAccounts, launchPolicy, updatePolicy, deletePolicy } from "@/lib/api"
import type { Policy, Account, ScopeConfig } from "@/lib/types"
import { isLaunchedPolicy } from "@/lib/types"

function getSeverityBadgeClass(severity: number) {
  if (severity >= 80) {
    return "border-red-500/50 bg-red-500/10 text-red-400"
  } else if (severity >= 60) {
    return "border-orange-500/50 bg-orange-500/10 text-orange-400"
  } else if (severity >= 40) {
    return "border-yellow-500/50 bg-yellow-500/10 text-yellow-400"
  } else {
    return "border-blue-500/50 bg-blue-500/10 text-blue-400"
  }
}

function getSeverityLabel(severity: number): string {
  if (severity >= 80) return "Critical"
  if (severity >= 60) return "High"
  if (severity >= 40) return "Medium"
  return "Info"
}

export function snakeToTitleCase(str: string): string {
  if (str.length > 0) {
    return str
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(" ")
  }
  return str
}

function formatScope(scope: ScopeConfig): string {
  const includeAccounts = scope.include_accounts || []
  const excludeAccounts = scope.exclude_accounts || []
  const includeTags = scope.include_tags || {}
  const excludeTags = scope.exclude_tags || {}
  const includeOuPaths = scope.include_ou_paths || []
  const excludeOuPaths = scope.exclude_ou_paths || []

  if (
    includeAccounts.length === 0 &&
    excludeAccounts.length === 0 &&
    Object.keys(includeTags).length === 0 &&
    Object.keys(excludeTags).length === 0 &&
    includeOuPaths.length === 0 &&
    excludeOuPaths.length === 0
  ) {
    return "All accounts"
  }

  const parts: string[] = []
  if (includeAccounts.length > 0) {
    parts.push(`${includeAccounts.length} account(s)`)
  }
  if (excludeAccounts.length > 0) {
    parts.push(`excluding ${excludeAccounts.length}`)
  }
  if (Object.keys(includeTags).length > 0) {
    parts.push(`with tags`)
  }
  if (includeOuPaths.length > 0) {
    parts.push(`${includeOuPaths.length} OU(s)`)
  }

  return parts.join(", ") || "Custom scope"
}

export function ManagementView() {
  const [activePolicies, setActivePolicies] = useState<Policy[]>([])
  const [availablePolicies, setAvailablePolicies] = useState<Policy[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<{ message: string; requestId?: string } | null>(null)

  const [launchDialogOpen, setLaunchDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null)

  const [scopeMode, setScopeMode] = useState<"all" | "custom">("all")
  const [includeAccounts, setIncludeAccounts] = useState<string[]>([])
  const [excludeAccounts, setExcludeAccounts] = useState<string[]>([])
  const [includeTags, setIncludeTags] = useState<Record<string, string[]>>({})
  const [excludeTags, setExcludeTags] = useState<Record<string, string[]>>({})
  const [includeOuPaths, setIncludeOuPaths] = useState<string[]>([])
  const [excludeOuPaths, setExcludeOuPaths] = useState<string[]>([])
  const [severity, setSeverity] = useState<number>(70)
  const [remediation, setRemediation] = useState<string>("")

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [errorRequestId, setErrorRequestId] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      setLoadError(null)
      try {
        const [activePoliciesData, availablePoliciesData, accountsData] = await Promise.all([
          getPolicies({ status: "active" }),
          getPolicies({ status: "available" }),
          getAccounts(),
        ])
        setActivePolicies(activePoliciesData)
        setAvailablePolicies(availablePoliciesData)
        setAccounts(accountsData)
      } catch (err: any) {
        setLoadError({
          message: err.message || "Failed to load policy data",
          requestId: err.requestId,
        })
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const handleLaunchPolicy = (policy: Policy) => {
    console.log("[v0] Launch policy data:", policy)
    console.log("[v0] Launch remediation:", policy.remediation)
    setSelectedPolicy(policy)
    setSeverity(policy.severity)
    setRemediation(policy.remediation)
    setScopeMode("all")
    setIncludeAccounts([])
    setExcludeAccounts([])
    setIncludeTags({})
    setExcludeTags({})
    setIncludeOuPaths([])
    setExcludeOuPaths([])
    setError(null)
    setLaunchDialogOpen(true)
  }

  const handleLaunchSubmit = async () => {
    if (!selectedPolicy) return

    setSubmitting(true)
    setError(null)
    setErrorRequestId(null)

    const scope = {
      include_accounts: scopeMode === "all" ? [] : includeAccounts,
      exclude_accounts: scopeMode === "all" ? [] : excludeAccounts,
      include_tags: scopeMode === "all" ? {} : includeTags,
      exclude_tags: scopeMode === "all" ? {} : excludeTags,
      include_ou_paths: scopeMode === "all" ? [] : includeOuPaths,
      exclude_ou_paths: scopeMode === "all" ? [] : excludeOuPaths,
    }

    const result = await launchPolicy(selectedPolicy.policy_id, scope, severity, remediation)

    setSubmitting(false)

    if (result.success) {
      setLaunchDialogOpen(false)
      // Refresh the data
      const [activePoliciesData, availablePoliciesData] = await Promise.all([
        getPolicies({ status: "active" }),
        getPolicies({ status: "available" }),
      ])
      setActivePolicies(activePoliciesData)
      setAvailablePolicies(availablePoliciesData)
    } else {
      setError(result.error || "Failed to launch policy")
      setErrorRequestId(result.requestId || null)
    }
  }

  const handleEditPolicy = (policy: Policy) => {
    // Type guard ensures we have scope for launched policies
    if (!isLaunchedPolicy(policy)) return

    console.log("[v0] Edit policy data:", policy)
    console.log("[v0] Edit remediation:", policy.remediation)
    console.log("[v0] Edit description:", policy.description)
    setSelectedPolicy(policy)
    setSeverity(policy.severity)
    setRemediation(policy.remediation || "")
    // Check if scope is "all accounts"
    const isAllAccounts =
      policy.scope.include_accounts.length === 0 &&
      policy.scope.exclude_accounts.length === 0 &&
      Object.keys(policy.scope.include_tags).length === 0 &&
      Object.keys(policy.scope.exclude_tags).length === 0 &&
      policy.scope.include_ou_paths.length === 0 &&
      policy.scope.exclude_ou_paths.length === 0

    setScopeMode(isAllAccounts ? "all" : "custom")
    setIncludeAccounts(policy.scope.include_accounts || [])
    setExcludeAccounts(policy.scope.exclude_accounts || [])
    setIncludeTags(policy.scope.include_tags || {})
    setExcludeTags(policy.scope.exclude_tags || {})
    setIncludeOuPaths(policy.scope.include_ou_paths || [])
    setExcludeOuPaths(policy.scope.exclude_ou_paths || [])
    setError(null)
    setEditDialogOpen(true)
  }

  const handleUpdateSubmit = async () => {
    if (!selectedPolicy) return

    setSubmitting(true)
    setError(null)
    setErrorRequestId(null)

    const scope = {
      include_accounts: scopeMode === "all" ? [] : includeAccounts,
      exclude_accounts: scopeMode === "all" ? [] : excludeAccounts,
      include_tags: scopeMode === "all" ? {} : includeTags,
      exclude_tags: scopeMode === "all" ? {} : excludeTags,
      include_ou_paths: scopeMode === "all" ? [] : includeOuPaths,
      exclude_ou_paths: scopeMode === "all" ? [] : excludeOuPaths,
    }

    const result = await updatePolicy(selectedPolicy.policy_id, {
      scope,
      severity,
      remediation,
    })

    setSubmitting(false)

    if (result.success) {
      setEditDialogOpen(false)
      // Refresh the data
      const activePoliciesData = await getPolicies({ status: "active" })
      setActivePolicies(activePoliciesData)
    } else {
      setError(result.error || "Failed to update policy")
      setErrorRequestId(result.requestId || null)
    }
  }

  const handleDisablePolicy = async () => {
    if (!selectedPolicy) return

    setSubmitting(true)
    setError(null)
    setErrorRequestId(null)

    const result = await deletePolicy(selectedPolicy.policy_id)

    setSubmitting(false)

    if (result.success) {
      setEditDialogOpen(false)
      // Refresh the data
      const [activePoliciesData, availablePoliciesData] = await Promise.all([
        getPolicies({ status: "active" }),
        getPolicies({ status: "available" }),
      ])
      setActivePolicies(activePoliciesData)
      setAvailablePolicies(availablePoliciesData)
    } else {
      setError(result.error || "Failed to disable policy")
      setErrorRequestId(result.requestId || null)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-semibold text-balance">Policy Management</h1>
          <p className="mt-2 text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-semibold text-balance">Policy Management</h1>
        </div>
        <div className="rounded-md bg-red-500/10 border border-red-500/50 p-4">
          <p className="text-sm text-red-400">
            {loadError.message}
            {loadError.requestId && (
              <>
                <br />
                <span className="text-xs italic">Request Id: {loadError.requestId}</span>
              </>
            )}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="text-3xl font-semibold text-balance">Policy Management</h1>
        <p className="mt-2 text-muted-foreground">Configure and manage security policies across your infrastructure</p>
      </div>

      {/* Active Policies */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold">Active Policies</h2>
          <p className="text-sm text-muted-foreground mt-1">Currently enforced policies and their findings</p>
        </div>
        <Card className="bg-card border-border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="text-muted-foreground">Policy Name</TableHead>
                <TableHead className="text-muted-foreground">Scope</TableHead>
                <TableHead className="text-muted-foreground">Severity</TableHead>
                <TableHead className="text-muted-foreground">Open Findings</TableHead>
                <TableHead className="text-muted-foreground">Enforced Since</TableHead>
                <TableHead className="text-muted-foreground">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {activePolicies.map((policy) => (
                <TableRow key={policy.policy_id} className="border-border hover:bg-secondary/50">
                  <TableCell className="font-semibold">{policy.policy_id}</TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {policy.scope ? formatScope(policy.scope) : "N/A"}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={getSeverityBadgeClass(policy.severity)}>
                      {getSeverityLabel(policy.severity)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="font-semibold text-qrie-orange">{policy.open_findings ?? 0}</span>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">{policy.created_at ?? "N/A"}</TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2 bg-transparent"
                      onClick={() => handleEditPolicy(policy)}
                    >
                      <Settings className="h-4 w-4" />
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>

      {/* Available Policies */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Available Policies</h2>
            <p className="text-sm text-muted-foreground mt-1">Browse and launch security policies</p>
          </div>
        </div>
        <Card className="bg-card border-border">
          {availablePolicies.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-muted-foreground">All policies are launched</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {availablePolicies.map((policy) => (
                <div key={policy.policy_id} className="p-6 flex items-start justify-between gap-4">
                  <div className="flex-1 space-y-1">
                    <div className="font-medium">{policy.policy_id}</div>
                    <p className="text-sm text-muted-foreground">{policy.description}</p>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2">
                      <span>Service: {policy.service.toUpperCase()}</span>
                      <span>Category: {snakeToTitleCase(policy.category)}</span>
                      <Badge variant="outline" className={getSeverityBadgeClass(policy.severity)}>
                        {getSeverityLabel(policy.severity)}
                      </Badge>
                    </div>
                  </div>
                  <Button size="sm" className="gap-2" onClick={() => handleLaunchPolicy(policy)}>
                    <Play className="h-4 w-4" />
                    Launch
                  </Button>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Launch Policy Dialog */}
      <Dialog open={launchDialogOpen} onOpenChange={setLaunchDialogOpen}>
        <DialogContent className="bg-card border-border max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Launch Policy: {selectedPolicy?.policy_id}</DialogTitle>
            {selectedPolicy?.description && (
              <p className="text-sm text-muted-foreground pt-1">{selectedPolicy.description}</p>
            )}
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Severity */}
            <div className="space-y-2">
              <Label htmlFor="launch-severity">Severity</Label>
              <Select value={severity.toString()} onValueChange={(v) => setSeverity(Number.parseInt(v))}>
                <SelectTrigger id="launch-severity" className="bg-background border-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">Info (30)</SelectItem>
                  <SelectItem value="50">Medium (50)</SelectItem>
                  <SelectItem value="70">High (70)</SelectItem>
                  <SelectItem value="90">Critical (90)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Scope Mode */}
            <div className="space-y-2">
              <Label>Scope</Label>
              <Select value={scopeMode} onValueChange={(v) => setScopeMode(v as "all" | "custom")}>
                <SelectTrigger className="bg-background border-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All accounts</SelectItem>
                  <SelectItem value="custom">Custom selection</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Custom Scope Configuration */}
            {scopeMode === "custom" && (
              <div className="space-y-4 border border-border rounded-lg p-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Include Accounts</Label>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setIncludeAccounts(accounts.map((a) => a.account_id))}
                      >
                        Select All
                      </Button>
                      <Button type="button" variant="ghost" size="sm" onClick={() => setIncludeAccounts([])}>
                        Deselect All
                      </Button>
                    </div>
                  </div>
                  <Textarea
                    value={(includeAccounts || []).join("\n")}
                    onChange={(e) => setIncludeAccounts(e.target.value.split("\n").filter(Boolean))}
                    placeholder="Enter account IDs, one per line"
                    className="bg-background border-border font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Exclude Accounts</Label>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setExcludeAccounts(accounts.map((a) => a.account_id))}
                      >
                        Select All
                      </Button>
                      <Button type="button" variant="ghost" size="sm" onClick={() => setExcludeAccounts([])}>
                        Deselect All
                      </Button>
                    </div>
                  </div>
                  <Textarea
                    value={(excludeAccounts || []).join("\n")}
                    onChange={(e) => setExcludeAccounts(e.target.value.split("\n").filter(Boolean))}
                    placeholder="Enter account IDs to exclude, one per line"
                    className="bg-background border-border font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Include Tags (key=value, one per line)</Label>
                  <Textarea
                    value={Object.entries(includeTags || {})
                      .map(([k, v]) => `${k}=${v}`)
                      .join("\n")}
                    onChange={(e) => {
                      const tags: Record<string, string[]> = {}
                      e.target.value
                        .split("\n")
                        .filter(Boolean)
                        .forEach((line) => {
                          const [key, value] = line.split("=")
                          if (key && value) tags[key.trim()] = [value.trim()]
                        })
                      setIncludeTags(tags)
                    }}
                    placeholder="Environment=prod"
                    className="bg-background border-border font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Exclude Tags (key=value, one per line)</Label>
                  <Textarea
                    value={Object.entries(excludeTags || {})
                      .map(([k, v]) => `${k}=${v}`)
                      .join("\n")}
                    onChange={(e) => {
                      const tags: Record<string, string[]> = {}
                      e.target.value
                        .split("\n")
                        .filter(Boolean)
                        .forEach((line) => {
                          const [key, value] = line.split("=")
                          if (key && value) tags[key.trim()] = [value.trim()]
                        })
                      setExcludeTags(tags)
                    }}
                    placeholder="SkipCompliance=true"
                    className="bg-background border-border font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Include OU Paths</Label>
                  <Textarea
                    value={(includeOuPaths || []).join("\n")}
                    onChange={(e) => setIncludeOuPaths(e.target.value.split("\n").filter(Boolean))}
                    placeholder="ou-root-123456789/ou-prod-abcdef"
                    className="bg-background border-border font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Exclude OU Paths</Label>
                  <Textarea
                    value={(excludeOuPaths || []).join("\n")}
                    onChange={(e) => setExcludeOuPaths(e.target.value.split("\n").filter(Boolean))}
                    placeholder="ou-root-123456789/ou-sandbox-xyz123"
                    className="bg-background border-border font-mono text-sm"
                  />
                </div>
              </div>
            )}

            {/* Remediation */}
            <div className="space-y-2">
              <Label htmlFor="launch-remediation">Remediation</Label>
              <Textarea
                id="launch-remediation"
                value={remediation}
                onChange={(e) => setRemediation(e.target.value)}
                placeholder="Enter remediation instructions"
                className="bg-background border-border font-mono text-sm resize-none max-h-[360px]"
                rows={15}
              />
            </div>
          </div>
          {error && (
            <div className="rounded-md bg-red-500/10 border border-red-500/50 p-3 text-sm text-red-400">
              {error}
              {errorRequestId && (
                <>
                  <br />
                  <span className="text-xs italic">Request Id: {errorRequestId}</span>
                </>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setLaunchDialogOpen(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button onClick={handleLaunchSubmit} disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Launching...
                </>
              ) : (
                "Launch & Scan"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Policy Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="bg-card border-border max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Policy: {selectedPolicy?.policy_id}</DialogTitle>
            {selectedPolicy?.description && (
              <p className="text-sm text-muted-foreground pt-1">{selectedPolicy.description}</p>
            )}
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Severity */}
            <div className="space-y-2">
              <Label htmlFor="edit-severity">Severity</Label>
              <Select value={severity.toString()} onValueChange={(v) => setSeverity(Number.parseInt(v))}>
                <SelectTrigger id="edit-severity" className="bg-background border-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">Info (30)</SelectItem>
                  <SelectItem value="50">Medium (50)</SelectItem>
                  <SelectItem value="70">High (70)</SelectItem>
                  <SelectItem value="90">Critical (90)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Scope Mode */}
            <div className="space-y-2">
              <Label>Scope</Label>
              <Select value={scopeMode} onValueChange={(v) => setScopeMode(v as "all" | "custom")}>
                <SelectTrigger className="bg-background border-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All accounts</SelectItem>
                  <SelectItem value="custom">Custom selection</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Custom Scope Configuration */}
            {scopeMode === "custom" && (
              <div className="space-y-4 border border-border rounded-lg p-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Include Accounts</Label>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setIncludeAccounts(accounts.map((a) => a.account_id))}
                      >
                        Select All
                      </Button>
                      <Button type="button" variant="ghost" size="sm" onClick={() => setIncludeAccounts([])}>
                        Deselect All
                      </Button>
                    </div>
                  </div>
                  <Textarea
                    value={(includeAccounts || []).join("\n")}
                    onChange={(e) => setIncludeAccounts(e.target.value.split("\n").filter(Boolean))}
                    placeholder="Enter account IDs, one per line"
                    className="bg-background border-border font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Exclude Accounts</Label>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setExcludeAccounts(accounts.map((a) => a.account_id))}
                      >
                        Select All
                      </Button>
                      <Button type="button" variant="ghost" size="sm" onClick={() => setExcludeAccounts([])}>
                        Deselect All
                      </Button>
                    </div>
                  </div>
                  <Textarea
                    value={(excludeAccounts || []).join("\n")}
                    onChange={(e) => setExcludeAccounts(e.target.value.split("\n").filter(Boolean))}
                    placeholder="Enter account IDs to exclude, one per line"
                    className="bg-background border-border font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Include Tags (key=value, one per line)</Label>
                  <Textarea
                    value={Object.entries(includeTags || {})
                      .map(([k, v]) => `${k}=${v}`)
                      .join("\n")}
                    onChange={(e) => {
                      const tags: Record<string, string[]> = {}
                      e.target.value
                        .split("\n")
                        .filter(Boolean)
                        .forEach((line) => {
                          const [key, value] = line.split("=")
                          if (key && value) tags[key.trim()] = [value.trim()]
                        })
                      setIncludeTags(tags)
                    }}
                    placeholder="Environment=prod"
                    className="bg-background border-border font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Exclude Tags (key=value, one per line)</Label>
                  <Textarea
                    value={Object.entries(excludeTags || {})
                      .map(([k, v]) => `${k}=${v}`)
                      .join("\n")}
                    onChange={(e) => {
                      const tags: Record<string, string[]> = {}
                      e.target.value
                        .split("\n")
                        .filter(Boolean)
                        .forEach((line) => {
                          const [key, value] = line.split("=")
                          if (key && value) tags[key.trim()] = [value.trim()]
                        })
                      setExcludeTags(tags)
                    }}
                    placeholder="SkipCompliance=true"
                    className="bg-background border-border font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Include OU Paths</Label>
                  <Textarea
                    value={(includeOuPaths || []).join("\n")}
                    onChange={(e) => setIncludeOuPaths(e.target.value.split("\n").filter(Boolean))}
                    placeholder="ou-root-123456789/ou-prod-abcdef"
                    className="bg-background border-border font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Exclude OU Paths</Label>
                  <Textarea
                    value={(excludeOuPaths || []).join("\n")}
                    onChange={(e) => setExcludeOuPaths(e.target.value.split("\n").filter(Boolean))}
                    placeholder="ou-root-123456789/ou-sandbox-xyz123"
                    className="bg-background border-border font-mono text-sm"
                  />
                </div>
              </div>
            )}

            {/* Remediation */}
            <div className="space-y-2">
              <Label htmlFor="edit-remediation">Remediation</Label>
              <Textarea
                id="edit-remediation"
                value={remediation}
                onChange={(e) => setRemediation(e.target.value)}
                placeholder="Enter remediation instructions"
                className="bg-background border-border font-mono text-sm resize-none max-h-[360px]"
                rows={15}
              />
            </div>
          </div>
          {error && (
            <div className="rounded-md bg-red-500/10 border border-red-500/50 p-3 text-sm text-red-400">
              {error}
              {errorRequestId && (
                <>
                  <br />
                  <span className="text-xs italic">Request Id: {errorRequestId}</span>
                </>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="destructive" onClick={handleDisablePolicy} disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Disabling...
                </>
              ) : (
                "Disable Policy"
              )}
            </Button>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button onClick={handleUpdateSubmit} disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Changes"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
