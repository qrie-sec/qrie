import type {
  DashboardSummary,
  Account,
  Policy,
  Service,
  Finding,
  Resource,
  FindingsSummary,
  ResourcesSummary,
} from "./types"

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "/api").replace(/\/$/, "")

function logApiCall(endpoint: string, params?: Record<string, unknown>, response?: unknown, error?: unknown) {
  if (error) {
    console.log(`[v0 API] ❌ ${endpoint}`, { params, error })
  } else {
    console.log(`[v0 API] ✅ ${endpoint}`, { params, response })
  }
}

export interface ApiError {
  message: string
  requestId?: string
}

async function handleApiError(response: Response, endpoint: string): Promise<ApiError> {
  const requestId = response.headers.get("x-request-id") || response.headers.get("x-amzn-requestid") || "unknown"
  let errorMessage = `Failed to fetch ${endpoint}`

  try {
    const errorData = await response.json()
    errorMessage = errorData.message || errorData.error || errorMessage
  } catch {
    // If response is not JSON, use status text
    errorMessage = response.statusText || errorMessage
  }

  return {
    message: errorMessage,
    requestId,
  }
}

// Dashboard API
export async function getDashboardSummary(date?: string): Promise<DashboardSummary> {
  try {
    const dateParam = date || new Date().toISOString().split("T")[0]
    const url = `${API_BASE_URL}/summary/dashboard?date=${dateParam}`
    logApiCall("GET /summary/dashboard", { date: dateParam })
    const response = await fetch(url)
    if (!response.ok) {
      const error = await handleApiError(response, "dashboard summary")
      throw error
    }
    const data = await response.json()
    logApiCall("GET /summary/dashboard", { date: dateParam }, data)
    return data
  } catch (error) {
    logApiCall("GET /summary/dashboard", { date }, undefined, error)
    throw error
  }
}

// Accounts API
export async function getAccounts(): Promise<Account[]> {
  try {
    const url = `${API_BASE_URL}/accounts`
    logApiCall("GET /accounts")
    const response = await fetch(url)
    if (!response.ok) {
      const error = await handleApiError(response, "accounts")
      throw error
    }
    const data = await response.json()
    logApiCall("GET /accounts", {}, data)
    return data
  } catch (error) {
    logApiCall("GET /accounts", {}, undefined, error)
    throw error
  }
}

// Policies API - Unified endpoint
export async function getPolicies(params?: {
  status?: "active" | "available" | "all"
  policy_id?: string
  services?: string[]
}): Promise<Policy[]> {
  try {
    const queryParams = new URLSearchParams()
    if (params?.status) queryParams.append("status", params.status)
    if (params?.policy_id) queryParams.append("policy_id", params.policy_id)
    if (params?.services?.length) queryParams.append("services", params.services.join(","))
    
    const url = `${API_BASE_URL}/policies?${queryParams.toString()}`
    logApiCall("GET /policies", params)
    const response = await fetch(url)
    if (!response.ok) {
      const error = await handleApiError(response, "policies")
      throw error
    }
    const data = await response.json()
    logApiCall("GET /policies", params, data)
    return data
  } catch (error) {
    logApiCall("GET /policies", params, undefined, error)
    throw error
  }
}

// Services API
export async function getServices(supported?: boolean): Promise<Service[]> {
  try {
    const url = supported ? `${API_BASE_URL}/services?supported=true` : `${API_BASE_URL}/services`
    logApiCall("GET /services", { supported })
    const response = await fetch(url)
    if (!response.ok) {
      const error = await handleApiError(response, "services")
      throw error
    }
    const data = await response.json()
    logApiCall("GET /services", { supported }, data)
    return data
  } catch (error) {
    logApiCall("GET /services", { supported }, undefined, error)
    throw error
  }
}

// Findings API
export async function getFindings(params: {
  account?: string
  policy?: string
  state?: "ACTIVE" | "RESOLVED"
  severity?: string
  page_size?: number
  next_token?: string
}): Promise<{ findings: Finding[]; next_token?: string }> {
  try {
    const queryParams = new URLSearchParams()
    if (params.account) queryParams.append("account", params.account)
    if (params.policy) queryParams.append("policy", params.policy)
    if (params.state) queryParams.append("state", params.state)
    if (params.severity) queryParams.append("severity", params.severity)
    if (params.page_size) queryParams.append("page_size", params.page_size.toString())
    if (params.next_token) queryParams.append("next_token", params.next_token)

    const url = `${API_BASE_URL}/findings?${queryParams.toString()}`
    logApiCall("GET /findings", params)
    const response = await fetch(url)
    if (!response.ok) {
      const error = await handleApiError(response, "findings")
      throw error
    }
    const data = await response.json()
    logApiCall("GET /findings", params, data)
    return data
  } catch (error) {
    logApiCall("GET /findings", params, undefined, error)
    throw error
  }
}

// Findings Summary API
export async function getFindingsSummary(account?: string): Promise<FindingsSummary> {
  try {
    const url = account ? `${API_BASE_URL}/summary/findings?account=${account}` : `${API_BASE_URL}/summary/findings`
    logApiCall("GET /summary/findings", { account })
    const response = await fetch(url)
    if (!response.ok) {
      const error = await handleApiError(response, "findings summary")
      throw error
    }
    const data = await response.json()
    logApiCall("GET /summary/findings", { account }, data)
    return data
  } catch (error) {
    logApiCall("GET /summary/findings", { account }, undefined, error)
    throw error
  }
}

// Resources API
export async function getResources(params: {
  account?: string
  type?: string
  page_size?: number
  next_token?: string
}): Promise<{ resources: Resource[]; next_token?: string }> {
  try {
    const queryParams = new URLSearchParams()
    if (params.account) queryParams.append("account", params.account)
    if (params.type) queryParams.append("type", params.type)
    if (params.page_size) queryParams.append("page_size", params.page_size.toString())
    if (params.next_token) queryParams.append("next_token", params.next_token)

    const url = `${API_BASE_URL}/resources?${queryParams.toString()}`
    logApiCall("GET /resources", params)
    const response = await fetch(url)
    if (!response.ok) {
      const error = await handleApiError(response, "resources")
      throw error
    }
    const data = await response.json()
    logApiCall("GET /resources", params, data)
    return data
  } catch (error) {
    logApiCall("GET /resources", params, undefined, error)
    throw error
  }
}

// Resources Summary API
export async function getResourcesSummary(account?: string): Promise<ResourcesSummary> {
  try {
    const url = account ? `${API_BASE_URL}/summary/resources?account=${account}` : `${API_BASE_URL}/summary/resources`
    logApiCall("GET /summary/resources", { account })
    const response = await fetch(url)
    if (!response.ok) {
      const error = await handleApiError(response, "resources summary")
      throw error
    }
    const data = await response.json()
    logApiCall("GET /summary/resources", { account }, data)
    return data
  } catch (error) {
    logApiCall("GET /summary/resources", { account }, undefined, error)
    throw error
  }
}


// Launch a new policy
export async function launchPolicy(
  policyId: string,
  scope: {
    include_accounts: string[]
    exclude_accounts: string[]
    include_tags: Record<string, string[]>
    exclude_tags: Record<string, string[]>
    include_ou_paths: string[]
    exclude_ou_paths: string[]
  },
  severity?: number,
  remediation?: string,
): Promise<{ success: boolean; error?: string; requestId?: string }> {
  try {
    const url = `${API_BASE_URL}/policies`
    const body = {
      policy_id: policyId,
      scope,
      severity,
      remediation,
    }
    logApiCall("POST /policies", body)
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const error = await handleApiError(response, "launch policy")
      logApiCall("POST /policies", body, undefined, error)
      return { success: false, error: error.message, requestId: error.requestId }
    }

    const data = await response.json()
    logApiCall("POST /policies", body, data)
    return { success: true }
  } catch (error) {
    logApiCall("POST /policies", { policyId }, undefined, error)
    return { success: false, error: "Failed to launch policy", requestId: "unknown" }
  }
}

// Update policy metadata (scope, severity, remediation)
export async function updatePolicy(
  policyId: string,
  updates: {
    scope?: {
      include_accounts: string[]
      exclude_accounts: string[]
      include_tags: Record<string, string[]>
      exclude_tags: Record<string, string[]>
      include_ou_paths: string[]
      exclude_ou_paths: string[]
    }
    severity?: number
    remediation?: string
  },
): Promise<{ success: boolean; error?: string; requestId?: string }> {
  try {
    const url = `${API_BASE_URL}/policies/${policyId}`
    logApiCall(`PUT /policies/${policyId}`, updates)
    const response = await fetch(url, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updates),
    })

    if (!response.ok) {
      const error = await handleApiError(response, "update policy")
      logApiCall(`PUT /policies/${policyId}`, updates, undefined, error)
      return { success: false, error: error.message, requestId: error.requestId }
    }

    const data = await response.json()
    logApiCall(`PUT /policies/${policyId}`, updates, data)
    return { success: true }
  } catch (error) {
    logApiCall(`PUT /policies/${policyId}`, updates, undefined, error)
    return { success: false, error: "Failed to update policy", requestId: "unknown" }
  }
}

// Delete/suspend a policy (purges all findings)
export async function deletePolicy(policyId: string): Promise<{ success: boolean; error?: string; requestId?: string; findings_deleted?: number }> {
  try {
    const url = `${API_BASE_URL}/policies/${policyId}`
    logApiCall(`DELETE /policies/${policyId}`)
    const response = await fetch(url, {
      method: "DELETE",
    })

    if (!response.ok) {
      const error = await handleApiError(response, "delete policy")
      logApiCall(`DELETE /policies/${policyId}`, {}, undefined, error)
      return { success: false, error: error.message, requestId: error.requestId }
    }

    const data = await response.json()
    logApiCall(`DELETE /policies/${policyId}`, {}, data)
    return { success: true, findings_deleted: data.findings_deleted }
  } catch (error) {
    logApiCall(`DELETE /policies/${policyId}`, {}, undefined, error)
    return { success: false, error: "Failed to delete policy", requestId: "unknown" }
  }
}
