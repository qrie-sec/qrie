"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"
import { getAccounts, getPolicies, getFindings, getFindingsSummary } from "@/lib/api"
import type { Account, Policy, Finding, FindingsSummary } from "@/lib/types"

function getSeverityLabel(severity: number): string {
  if (severity >= 75) return "Critical"
  if (severity >= 50) return "High"
  if (severity >= 25) return "Medium"
  return "Info"
}

function getSeverityBadgeClass(severity: number): string {
  if (severity >= 75) {
    return "border-red-500/50 bg-red-500/10 text-red-400"
  } else if (severity >= 50) {
    return "border-orange-500/50 bg-orange-500/10 text-orange-400"
  } else if (severity >= 25) {
    return "border-yellow-500/50 bg-yellow-500/10 text-yellow-400"
  } else {
    return "border-blue-500/50 bg-blue-500/10 text-blue-400"
  }
}

export function FindingsView() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [policies, setPolicies] = useState<Policy[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [summary, setSummary] = useState<FindingsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)

  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([])
  const [selectedPolicies, setSelectedPolicies] = useState<string[]>([])
  const [selectedStatus, setSelectedStatus] = useState<"ACTIVE" | "RESOLVED">("ACTIVE")
  const [selectedPolicy, setSelectedPolicy] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [nextToken, setNextToken] = useState<string | undefined>()
  const [hasMore, setHasMore] = useState(false)

  useEffect(() => {
    async function fetchInitialData() {
      setLoading(true)
      const [accountsData, policiesData, findingsData, summaryData] = await Promise.all([
        getAccounts(),
        getPolicies({ status: "active" }),
        getFindings({ page_size: 100 }),
        getFindingsSummary(),
      ])
      setAccounts(accountsData)
      setPolicies(policiesData)
      setFindings(findingsData.findings)
      setNextToken(findingsData.next_token)
      setHasMore(!!findingsData.next_token)
      setSummary(summaryData)
      setLoading(false)
    }
    fetchInitialData()
  }, [])

  useEffect(() => {
    async function fetchFilteredFindings() {
      const params: any = { page_size: 100 }

      if (selectedAccounts.length > 0 && selectedAccounts.length < accounts.length) {
        if (selectedAccounts.length === 1) {
          params.account = selectedAccounts[0]
        }
      }

      if (selectedPolicies.length > 0 && selectedPolicies.length < policies.length) {
        if (selectedPolicies.length === 1) {
          params.policy = selectedPolicies[0]
        }
      }

      params.state = selectedStatus

      const findingsData = await getFindings(params)
      setFindings(findingsData.findings)
      setNextToken(findingsData.next_token)
      setHasMore(!!findingsData.next_token)
      setCurrentPage(1)
    }

    if (!loading) {
      fetchFilteredFindings()
    }
  }, [selectedAccounts, selectedPolicies, selectedStatus, loading, accounts.length, policies.length])

  useEffect(() => {
    async function fetchSummary() {
      const summaryData = await getFindingsSummary(selectedAccounts.length === 1 ? selectedAccounts[0] : undefined)
      setSummary(summaryData)
    }

    if (!loading) {
      fetchSummary()
    }
  }, [selectedAccounts, loading])

  const loadMoreFindings = async () => {
    if (!nextToken || loadingMore) return

    setLoadingMore(true)
    try {
      const params: any = { page_size: 100, next_token: nextToken }

      if (selectedAccounts.length > 0 && selectedAccounts.length < accounts.length) {
        if (selectedAccounts.length === 1) {
          params.account = selectedAccounts[0]
        }
      }

      if (selectedPolicies.length > 0 && selectedPolicies.length < policies.length) {
        if (selectedPolicies.length === 1) {
          params.policy = selectedPolicies[0]
        }
      }

      params.state = selectedStatus

      const findingsData = await getFindings(params)
      setFindings((prev) => [...prev, ...findingsData.findings])
      setNextToken(findingsData.next_token)
      setHasMore(!!findingsData.next_token)
    } finally {
      setLoadingMore(false)
    }
  }

  const itemsPerPage = 25
  const totalPages = Math.ceil(findings.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const currentFindings = findings.slice(startIndex, endIndex)

  const toggleAccount = (account: string) => {
    setSelectedAccounts((prev) => (prev.includes(account) ? prev.filter((a) => a !== account) : [...prev, account]))
  }

  const togglePolicy = (policy: string) => {
    setSelectedPolicies((prev) => (prev.includes(policy) ? prev.filter((p) => p !== policy) : [...prev, policy]))
  }

  const showAllAccountsSummary = selectedAccounts.length !== 1
  const selectedAccountForSummary = selectedAccounts.length === 1 ? selectedAccounts[0] : null

  // Use backend-calculated values
  const highFindings = summary?.high_findings || 0

  const sortedPolicies = [...policies].sort((a, b) => b.severity - a.severity)
  // Backend already sorts policies by severity descending
  const sortedSummaryPolicies = summary?.policies || []

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-semibold text-balance">Findings</h1>
          <p className="mt-2 text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-3xl font-semibold text-balance">Findings</h1>
      </div>

      <div className="grid grid-cols-[280px_minmax(0,1fr)] gap-6">
        {/* Left Sidebar - Filters */}
        <div className="space-y-4">
          {/* Account Filter */}
          <Card className="p-4 bg-card border-border">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Account</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() =>
                    setSelectedAccounts(
                      selectedAccounts.length === accounts.length ? [] : accounts.map((a) => a.account_id),
                    )
                  }
                >
                  {selectedAccounts.length === accounts.length ? "Clear" : "All"}
                </Button>
              </div>
              <ScrollArea className="max-h-[200px]">
                <div className="space-y-1">
                  {accounts.map((account) => (
                    <button
                      key={account.account_id}
                      onClick={() => toggleAccount(account.account_id)}
                      className={cn(
                        "w-full text-left px-2 py-1 text-xs rounded transition-colors font-mono",
                        selectedAccounts.includes(account.account_id)
                          ? "bg-secondary text-foreground"
                          : "text-muted-foreground hover:bg-secondary/50",
                      )}
                    >
                      {account.account_id}
                    </button>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </Card>

          {/* Policy Filter */}
          <Card className="p-4 bg-card border-border">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Policy</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() =>
                    setSelectedPolicies(
                      selectedPolicies.length === policies.length ? [] : policies.map((p) => p.policy_id),
                    )
                  }
                >
                  {selectedPolicies.length === policies.length ? "Clear" : "All"}
                </Button>
              </div>
              <ScrollArea className="max-h-[200px]">
                <div className="space-y-1">
                  {sortedPolicies.map((policy) => (
                    <button
                      key={policy.policy_id}
                      onClick={() => togglePolicy(policy.policy_id)}
                      className={cn(
                        "w-full text-left px-2 py-1 text-xs rounded transition-colors flex items-center justify-between gap-2",
                        selectedPolicies.includes(policy.policy_id)
                          ? "bg-secondary text-foreground"
                          : "text-muted-foreground hover:bg-secondary/50",
                      )}
                    >
                      <span className="truncate">{policy.policy_id}</span>
                      <Badge
                        variant="outline"
                        className={cn("text-[10px] px-1 py-0 h-4 shrink-0", getSeverityBadgeClass(policy.severity))}
                      >
                        {getSeverityLabel(policy.severity)}
                      </Badge>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </Card>

          {/* Status Filter */}
          <Card className="p-4 bg-card border-border">
            <div className="space-y-3">
              <h3 className="text-sm font-medium">Finding Status</h3>
              <div className="space-y-1">
                <button
                  onClick={() => setSelectedStatus("ACTIVE")}
                  className={cn(
                    "w-full text-left px-2 py-1 text-xs rounded transition-colors",
                    selectedStatus === "ACTIVE"
                      ? "bg-secondary text-foreground"
                      : "text-muted-foreground hover:bg-secondary/50",
                  )}
                >
                  Open
                </button>
                <button
                  onClick={() => setSelectedStatus("RESOLVED")}
                  className={cn(
                    "w-full text-left px-2 py-1 text-xs rounded transition-colors",
                    selectedStatus === "RESOLVED"
                      ? "bg-secondary text-foreground"
                      : "text-muted-foreground hover:bg-secondary/50",
                  )}
                >
                  Resolved
                </button>
              </div>
            </div>
          </Card>
        </div>

        {/* Right - Policy Detail Card, Risk Summary, and Findings Table */}
        <div className="space-y-6 min-w-0">
          {selectedPolicy && (
            <Card className="p-6 bg-card border-border">
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">Policy: {selectedPolicy}</h3>
                    <p className="text-sm text-muted-foreground mt-1">Description of the policy</p>
                    <Button variant="link" className="h-auto p-0 text-xs text-qrie-orange mt-2">
                      link <ExternalLink className="ml-1 h-3 w-3" />
                    </Button>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => setSelectedPolicy(null)}>
                    ✕
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Launched:</p>
                    <p className="font-medium">2025.10.23</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Severity:</p>
                    <p className="font-medium text-qrie-orange">Critical</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Open Findings:</p>
                    <p className="font-medium">13</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Resolved Findings:</p>
                    <p className="font-medium">98</p>
                  </div>
                </div>
              </div>
            </Card>
          )}

          <Card className="p-4 bg-card border-border">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">Risk Summary</h3>
                <span className="text-xs text-muted-foreground">Updates every 15 min</span>
              </div>
              {showAllAccountsSummary ? (
                <div className="space-y-3">
                  <div className="space-y-1 text-sm">
                    <div>
                      <span className="text-muted-foreground">Scope: </span>
                      <span className="font-medium">All Accounts</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span>
                        <span className="text-muted-foreground">High: </span>
                        <span className="font-medium">{highFindings}</span>
                      </span>
                      <span>
                        <span className="text-muted-foreground">Critical: </span>
                        <span className="font-medium text-qrie-orange">{summary?.critical_findings || 0}</span>
                      </span>
                      <span>
                        <span className="text-muted-foreground">Open: </span>
                        <span className="font-medium">{summary?.open_findings || 0}</span>
                      </span>
                      <span>
                        <span className="text-muted-foreground">Resolved: </span>
                        <span className="font-medium">{summary?.resolved_findings || 0}</span>
                      </span>
                    </div>
                  </div>
                  <div className="pt-2">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-border hover:bg-transparent">
                          <TableHead className="text-xs text-muted-foreground h-8">Policy</TableHead>
                          <TableHead className="text-xs text-muted-foreground text-center h-8">Severity</TableHead>
                          <TableHead className="text-xs text-qrie-orange text-center h-8">Open</TableHead>
                          <TableHead className="text-xs text-muted-foreground text-center h-8">Resolved</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {sortedSummaryPolicies.map((policy) => (
                          <TableRow key={policy.policy} className="border-border hover:bg-secondary/50">
                            <TableCell className="text-xs py-2">{policy.policy}</TableCell>
                            <TableCell className="text-center py-2">
                              <Badge
                                variant="outline"
                                className={cn("text-[10px] px-1 py-0 h-4", getSeverityBadgeClass(policy.severity))}
                              >
                                {getSeverityLabel(policy.severity)}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-xs text-center py-2">{policy.open_findings}</TableCell>
                            <TableCell className="text-xs text-center py-2">{policy.resolved_findings}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="space-y-1 text-sm">
                    <div>
                      <span className="text-muted-foreground">Account: </span>
                      <span className="font-medium font-mono">{selectedAccountForSummary}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span>
                        <span className="text-muted-foreground">High: </span>
                        <span className="font-medium">{highFindings}</span>
                      </span>
                      <span>
                        <span className="text-muted-foreground">Critical: </span>
                        <span className="font-medium text-qrie-orange">{summary?.critical_findings || 0}</span>
                      </span>
                      <span>
                        <span className="text-muted-foreground">Open: </span>
                        <span className="font-medium">{summary?.open_findings || 0}</span>
                      </span>
                      <span>
                        <span className="text-muted-foreground">Resolved: </span>
                        <span className="font-medium">{summary?.resolved_findings || 0}</span>
                      </span>
                    </div>
                  </div>
                  <div className="pt-2">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-border hover:bg-transparent">
                          <TableHead className="text-xs text-muted-foreground h-8">Policy</TableHead>
                          <TableHead className="text-xs text-muted-foreground text-center h-8">Severity</TableHead>
                          <TableHead className="text-xs text-qrie-orange text-center h-8">Open</TableHead>
                          <TableHead className="text-xs text-muted-foreground text-center h-8">Resolved</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {sortedSummaryPolicies.map((policy) => (
                          <TableRow key={policy.policy} className="border-border hover:bg-secondary/50">
                            <TableCell className="text-xs py-2">{policy.policy}</TableCell>
                            <TableCell className="text-center py-2">
                              <Badge
                                variant="outline"
                                className={cn("text-[10px] px-1 py-0 h-4", getSeverityBadgeClass(policy.severity))}
                              >
                                {getSeverityLabel(policy.severity)}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-xs text-center py-2">{policy.open_findings}</TableCell>
                            <TableCell className="text-xs text-center py-2">{policy.resolved_findings}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
            </div>
          </Card>

          <Card className="bg-card border-border overflow-hidden">
            <div className="p-4 border-b border-border">
              <h2 className="text-lg font-semibold">Findings Explorer</h2>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead className="text-muted-foreground pl-4">Account</TableHead>
                    <TableHead className="text-muted-foreground pl-4">Service</TableHead>
                    <TableHead className="text-muted-foreground pl-4">ARN</TableHead>
                    <TableHead className="text-muted-foreground pl-4">Risk</TableHead>
                    <TableHead className="text-muted-foreground pl-4">Severity</TableHead>
                    <TableHead className="text-muted-foreground pl-4">Detected</TableHead>
                    <TableHead className="text-muted-foreground pl-4">Resolved</TableHead>
                    <TableHead className="text-muted-foreground pl-4">Finding</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentFindings.map((finding, idx) => (
                    <TableRow key={`${finding.arn}-${idx}`} className="border-border hover:bg-secondary/50">
                      <TableCell className="font-mono text-xs pl-4">{finding.account_service.split("_")[0]}</TableCell>
                      <TableCell className="text-sm pl-4">
                        {finding.account_service.split("_")[1]?.toUpperCase()}
                      </TableCell>
                      <TableCell className="font-mono text-xs max-w-[200px] truncate pl-4">{finding.arn}</TableCell>
                      <TableCell className="text-sm pl-4">{finding.policy}</TableCell>
                      <TableCell className="pl-4">
                        <Badge variant="outline" className={getSeverityBadgeClass(finding.severity)}>
                          {getSeverityLabel(finding.severity)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground pl-4">
                        {new Date(finding.first_seen).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground pl-4">
                        {finding.state === "RESOLVED" ? new Date(finding.last_evaluated).toLocaleString() : "-"}
                      </TableCell>
                      <TableCell className="pl-4">
                        <Button variant="link" className="h-auto p-0 text-xs text-qrie-orange">
                          {finding.arn.split("/").pop()?.substring(0, 12)}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between border-t border-border px-6 py-4">
              <div className="text-sm text-muted-foreground">
                Showing {startIndex + 1}-{Math.min(endIndex, findings.length)} of {findings.length} findings
                {hasMore && <span className="ml-2">(more available)</span>}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="border-border"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="border-border"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
                {hasMore && (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={loadMoreFindings}
                    disabled={loadingMore}
                    className="ml-2"
                  >
                    {loadingMore ? "Loading..." : "Load More"}
                  </Button>
                )}
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
