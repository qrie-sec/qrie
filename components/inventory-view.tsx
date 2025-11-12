"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { getAccounts, getServices, getResources, getResourcesSummary } from "@/lib/api"
import type { Account, Service, Resource, ResourcesSummary } from "@/lib/types"

export function InventoryView() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [services, setServices] = useState<Service[]>([])
  const [resources, setResources] = useState<Resource[]>([])
  const [summary, setSummary] = useState<ResourcesSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)

  const [selectedAccount, setSelectedAccount] = useState<string | null>(null)
  const [selectedResourceType, setSelectedResourceType] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [nextToken, setNextToken] = useState<string | undefined>()
  const [hasMore, setHasMore] = useState(false)

  useEffect(() => {
    async function fetchInitialData() {
      setLoading(true)
      const resourcesData = await getResources({ page_size: 100 })
      const [accountsData, servicesData, summaryData] = await Promise.all([
        getAccounts(),
        getServices(true),
        getResourcesSummary(),
      ])
      setAccounts(accountsData)
      setServices(servicesData)
      setResources(resourcesData.resources)
      setNextToken(resourcesData.next_token)
      setHasMore(!!resourcesData.next_token)
      setSummary(summaryData)
      setLoading(false)
    }
    fetchInitialData()
  }, [])

  useEffect(() => {
    async function fetchFilteredResources() {
      const params: any = { page_size: 100 }
      if (selectedAccount) params.account = selectedAccount
      if (selectedResourceType) params.type = selectedResourceType

      const resourcesData = await getResources(params)
      setResources(resourcesData.resources)
      setNextToken(resourcesData.next_token)
      setHasMore(!!resourcesData.next_token)
      setCurrentPage(1) // Reset to first page when filters change
    }

    if (!loading) {
      fetchFilteredResources()
    }
  }, [selectedAccount, selectedResourceType, loading])

  useEffect(() => {
    async function fetchSummary() {
      const summaryData = await getResourcesSummary(selectedAccount || undefined)
      setSummary(summaryData)
    }

    if (!loading) {
      fetchSummary()
    }
  }, [selectedAccount, loading])

  const loadMoreResources = async () => {
    if (!nextToken || loadingMore) return

    setLoadingMore(true)
    try {
      const params: any = { page_size: 100, next_token: nextToken }
      if (selectedAccount) params.account = selectedAccount
      if (selectedResourceType) params.type = selectedResourceType

      const resourcesData = await getResources(params)
      setResources((prev) => [...prev, ...resourcesData.resources])
      setNextToken(resourcesData.next_token)
      setHasMore(!!resourcesData.next_token)
    } finally {
      setLoadingMore(false)
    }
  }

  const itemsPerPage = 25
  const totalPages = Math.ceil(resources.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const currentInventory = resources.slice(startIndex, endIndex)

  const handleAccountSelect = (account: string) => {
    if (selectedAccount === account) {
      setSelectedAccount(null)
    } else {
      setSelectedAccount(account)
      setSelectedResourceType(null)
    }
  }

  const handleResourceTypeSelect = (resourceType: string) => {
    if (selectedResourceType === resourceType) {
      setSelectedResourceType(null)
    } else {
      setSelectedResourceType(resourceType)
      setSelectedAccount(null)
    }
  }

  const showAllAccountsSummary = !selectedAccount

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-semibold text-balance">Inventory</h1>
          <p className="mt-2 text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-balance">Inventory</h1>
      </div>

      <div className="grid grid-cols-[280px_minmax(0,1fr)] gap-6">
        <div className="space-y-4">
          <Card className="p-4 bg-card border-border">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Account</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => setSelectedAccount(null)}
                  disabled={!selectedAccount}
                >
                  All
                </Button>
              </div>
              <ScrollArea className="h-[200px]">
                <div className="space-y-1">
                  {accounts.map((account) => (
                    <button
                      key={account.account_id}
                      onClick={() => handleAccountSelect(account.account_id)}
                      disabled={!!selectedResourceType}
                      className={cn(
                        "w-full text-left px-2 py-1.5 text-sm rounded transition-colors font-mono",
                        selectedAccount === account.account_id
                          ? "bg-secondary text-foreground"
                          : "text-muted-foreground hover:bg-secondary/50",
                        selectedResourceType && "opacity-50 cursor-not-allowed",
                      )}
                    >
                      {account.account_id}
                    </button>
                  ))}
                </div>
              </ScrollArea>
              {selectedResourceType && (
                <p className="text-xs text-muted-foreground italic">Can't select both filters</p>
              )}
            </div>
          </Card>

          <Card className="p-4 bg-card border-border">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Resource Type</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => setSelectedResourceType(null)}
                  disabled={!selectedResourceType}
                >
                  All
                </Button>
              </div>
              <ScrollArea className="h-[200px]">
                <div className="space-y-1">
                  {services.map((service) => (
                    <button
                      key={service.service_name}
                      onClick={() => handleResourceTypeSelect(service.service_name)}
                      disabled={!!selectedAccount}
                      className={cn(
                        "w-full text-left px-2 py-1.5 text-xs rounded transition-colors",
                        selectedResourceType === service.service_name
                          ? "bg-secondary text-foreground"
                          : "text-muted-foreground hover:bg-secondary/50",
                        selectedAccount && "opacity-50 cursor-not-allowed",
                      )}
                    >
                      {service.display_name}
                    </button>
                  ))}
                </div>
              </ScrollArea>
              {selectedAccount && <p className="text-xs text-muted-foreground italic">Can't select both filters</p>}
            </div>
          </Card>
        </div>

        <div className="space-y-6 min-w-0">
          <Card className="p-4 bg-card border-border">
            <div className="space-y-4">
              {showAllAccountsSummary ? (
                <>
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">All Accounts Summary</p>
                    <span className="text-xs text-muted-foreground">Updates every 15 min</span>
                  </div>
                  <div className="text-xs">
                    <div className="flex items-center justify-end gap-4 mb-3">
                      <span className="text-muted-foreground">Total Findings: {summary?.total_findings || 0}</span>
                    </div>
                    <div className="flex items-center justify-end gap-4 mb-3 font-medium">
                      <span className="text-qrie-orange">Critical: {summary?.critical_findings || 0}</span>
                      <span className="text-muted-foreground">High: {summary?.high_findings || 0}</span>
                    </div>
                    <Table>
                      <TableHeader>
                        <TableRow className="border-border hover:bg-transparent">
                          <TableHead className="text-xs text-muted-foreground h-8">Resource Type</TableHead>
                          <TableHead className="text-xs text-muted-foreground text-center h-8">All Resources</TableHead>
                          <TableHead className="text-xs text-qrie-orange text-center h-8">Non-Compliant</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {summary?.resource_types.map((rt) => (
                          <TableRow key={rt.resource_type} className="border-border hover:bg-secondary/50">
                            <TableCell className="text-xs py-2">{rt.resource_type.toUpperCase()}</TableCell>
                            <TableCell className="text-xs text-center py-2">{rt.all_resources}</TableCell>
                            <TableCell className="text-xs text-center py-2">{rt.non_compliant}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-muted-foreground">Account: {selectedAccount}</p>
                      <p className="text-xs text-muted-foreground">
                        OU: {accounts.find((a) => a.account_id === selectedAccount)?.ou || "N/A"}
                      </p>
                    </div>
                    <span className="text-xs text-muted-foreground">Updates every 15 min</span>
                  </div>
                  <div className="text-xs">
                    <div className="flex items-center justify-end gap-4 mb-3">
                      <span className="text-muted-foreground">Total Findings: {summary?.total_findings || 0}</span>
                    </div>
                    <div className="flex items-center justify-end gap-4 mb-3 font-medium">
                      <span className="text-qrie-orange">Critical: {summary?.critical_findings || 0}</span>
                      <span className="text-muted-foreground">High: {summary?.high_findings || 0}</span>
                    </div>
                    <Table>
                      <TableHeader>
                        <TableRow className="border-border hover:bg-transparent">
                          <TableHead className="text-xs text-muted-foreground h-8">Resource Type</TableHead>
                          <TableHead className="text-xs text-muted-foreground text-center h-8">All Resources</TableHead>
                          <TableHead className="text-xs text-qrie-orange text-center h-8">Non-Compliant</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {summary?.resource_types.map((rt) => (
                          <TableRow key={rt.resource_type} className="border-border hover:bg-secondary/50">
                            <TableCell className="text-xs py-2">{rt.resource_type.toUpperCase()}</TableCell>
                            <TableCell className="text-xs text-center py-2">{rt.all_resources}</TableCell>
                            <TableCell className="text-xs text-center py-2">{rt.non_compliant}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </>
              )}
            </div>
          </Card>

          <Card className="bg-card border-border overflow-hidden">
            <div className="p-4 border-b border-border">
              <h2 className="text-lg font-semibold">Inventory</h2>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead className="text-muted-foreground pl-4">Account</TableHead>
                    <TableHead className="text-muted-foreground pl-4">Service</TableHead>
                    <TableHead className="text-muted-foreground pl-4">ARN</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentInventory.map((item, idx) => (
                    <TableRow key={`${item.arn}-${idx}`} className="border-border hover:bg-secondary/50">
                      <TableCell className="font-mono text-xs pl-4">{item.account_service.split("_")[0]}</TableCell>
                      <TableCell className="text-sm pl-4">
                        {item.account_service.split("_")[1]?.toUpperCase()}
                      </TableCell>
                      <TableCell className="font-mono text-xs pl-4">{item.arn}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <div className="flex items-center justify-between border-t border-border px-6 py-4">
              <div className="text-sm text-muted-foreground">
                Showing {startIndex + 1}-{Math.min(endIndex, resources.length)} of {resources.length} resources
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
                    onClick={loadMoreResources}
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
