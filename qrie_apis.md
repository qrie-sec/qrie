# qrie UI APIs

This document describes the API endpoints used by the qrie UI. All endpoints are served by a single Lambda URL handler (`api_handler.py`) that routes requests to appropriate modules.

## Dashboard 
**Handler**: `dashboard_api.py` + `dashboard_manager.py`

`GET /summary/dashboard?date=<YYYY-MM-DD>`

__Request__
- **Query params**: `date` (required, ISO date `YYYY-MM-DD`).

__Response__
- **Body**: `DashboardSummary` JSON with current counts, weekly trends (8 weeks), and top policies.
- **Caching**: Uses 1-hour cache with lazy refresh strategy. First request after cache expiry computes fresh data.
- **Performance**: Uses table scans (no GSI required). Cost-effective for MVP scale (<100K findings).

__Example Response__
```json
{
  "total_findings": 350,
  "total_open_findings": 247,
  "critical_open_findings": 38,
  "active_policies": 42,
  "resources": 1847,
  "accounts": 5,
  "findings_weekly": [
    {
      "week_start": "2024-10-13",
      "total_findings": 320,
      "open_findings": 230,
      "new_findings": 15,
      "closed_findings": 8,
      "critical_new": 3,
      "is_current": false
    },
    {
      "week_start": "2024-10-20",
      "total_findings": 350,
      "open_findings": 247,
      "new_findings": 30,
      "closed_findings": 13,
      "critical_new": 5,
      "is_current": true
    }
  ],
  "top_policies": [
    {
      "policy_id": "S3BucketPublic",
      "open_findings": 45,
      "severity": 90
    },
    {
      "policy_id": "EC2UnencryptedEBS",
      "open_findings": 34,
      "severity": 70
    }
  ],
  "policies_launched_this_month": 2
}
```

__Response Fields__
- **Current Counts**:
  - `total_findings`: All findings (ACTIVE + RESOLVED)
  - `total_open_findings`: Currently active findings
  - `critical_open_findings`: Active findings with severity >= 90
  - `active_policies`: Number of active policies
  - `resources`: Total resources monitored
  - `accounts`: Number of customer accounts
- **Weekly Trends** (`findings_weekly`): Array of 8 weeks (oldest to newest)
  - `week_start`: ISO date of week start (Monday)
  - `total_findings`: Cumulative findings created up to this week
  - `open_findings`: Snapshot of open findings at week end
  - `new_findings`: Findings created during this week
  - `closed_findings`: Findings resolved during this week
  - `critical_new`: New critical findings (severity >= 90) this week
  - `is_current`: Boolean indicating current incomplete week
- **Top Policies** (`top_policies`): Top 10 policies by open findings count
  - `policy_id`: Policy identifier
  - `open_findings`: Count of active findings
  - `severity`: Policy severity (0-100)
- **Month Metrics**:
  - `policies_launched_this_month`: Policies launched in current calendar month

__Logging__
- Request: `Dashboard summary request: date=2024-01-15`
- Cache hit: `Serving cached dashboard summary from 2024-01-15T10:30:00Z`
- Cache miss: `Cache miss or stale, computing fresh dashboard summary`
- Lock acquired: `Acquired refresh lock`
- Lock failed: `Serving stale data while refresh in progress`
- Success: `Dashboard summary retrieved: 247 open findings, 42 active policies, 1847 resources`
- Error: `Error getting dashboard summary for date 2024-01-15: <error message>`

__Implementation Notes__
- **Lazy Refresh**: Cache refreshes on first read after 1-hour expiry (no scheduled Lambda)
- **Distributed Lock**: DynamoDB conditional write prevents thundering herd
- **Race Condition Handling**: Concurrent requests serve stale data while one refreshes
- **Table Scans**: All metrics computed via table scans (no GSI overhead)
- **Cost**: ~$0.00005/month for 3 scans/day at 10K findings scale
- **Cache Storage**: Uses `qrie_summary` table (Type='dashboard') for generic summary caching

## Inventory

**Handler**: `resources_api.py` + `inventory_manager.py`

### Selectors
- `GET /accounts` - Returns list of customer accounts for dropdowns
- `GET /services?supported=true` - Returns supported AWS services

### Main table 
- `GET /resources` - Paginated resource listing
  - **Query params** (all optional):
    - `account=<12-digit-account-id>`
    - `type=<resource_type>`
    - `page_size=<int>` (max 100, default 50)
    - `next_token=<string>`
  - **Response**: `{ "resources": Resource[], "next_token"?: string }`
  - **Examples**:
    - `/resources?account=123123123123`
    - `/resources?type=ec2_instance`
    - `/resources?type=ec2_instance&account=123123123123`

### Summary endpoints
- `GET /summary/resources` - Returns resource counts by type and total accounts
- `GET /summary/resources?account=123123123123` - Returns resource summary for specific account


## Findings

**Handler**: `findings_api.py` + `findings_manager.py`

### Selectors
- `GET /accounts` - Returns list of customer accounts (shared with inventory)
- `GET /policies?status=<active|suspended>` - Returns launched policies for filtering
  - **Query params**: `status` (optional) - filter by policy status

### Main table
- `GET /findings` - Paginated findings listing
  - **Query params** (all optional):
    - `account=<12-digit-account-id>`
    - `policy=<policy_id>`
    - `state=<ACTIVE|RESOLVED>`
    - `severity=<severity>`
    - `page_size=<int>` (max 100, default 50)
    - `next_token=<string>`
  - **Response**: `{ "findings": Finding[], "next_token"?: string }`
  - **Examples**:
    - `/findings?severity=critical&state=ACTIVE`
    - `/findings?account=123123123123&severity=critical`
    - `/findings?policy=S3BucketVersioningDisabled&state=ACTIVE`

### Summary endpoints
- `GET /summary/findings` - Returns findings totals and breakdown by policy
- `GET /summary/findings?account=123123123123` - Returns findings summary for specific account


## Policy Management

**Handler**: `policies_api.py` + `policy_manager.py`

### Unified policy endpoint
- `GET /policies?status=<active|available|all>&policy_id=<id>&services=<service1,service2>` - Unified policy query endpoint
  - **Query params** (all optional):
    - `status`: `active` | `available` | `all` (default: `all`)
    - `policy_id`: Specific policy ID (returns array with 1 item)
    - `services`: Comma-separated list to filter by services
  - **Response**: Array of active policy objects
    ```json
    [
      {
        "policy_id": "S3BucketPublic",
        "description": "Detects S3 buckets with public read access",
        "service": "s3",
        "category": "access_control",
        "scope": {
          "include_accounts": ["123456789012", "987654321098"],
          "exclude_accounts": [],
          "include_tags": {"Environment": ["prod"], "Team": ["security"]},
          "exclude_tags": {"SkipCompliance": ["true"]},
          "include_ou_paths": ["ou-root-123456789/ou-prod-abcdef"],
          "exclude_ou_paths": ["ou-root-123456789/ou-sandbox-xyz123"]
        },
        "severity": 90,
        "remediation": "Remove public access from bucket policy",
        "open_findings": 45,
        "created_at": "2024-01-15",
        "updated_at": "2024-01-15",
        "status": "active"
      },
      {
        "policy_id": "EC2UnencryptedEBS",
        "description": "Detects EC2 instances with unencrypted EBS volumes",
        "service": "ec2",
        "category": "encryption",
        "scope": {
          "include_accounts": [],
          "exclude_accounts": ["111111111111"],
          "include_tags": {},
          "exclude_tags": {},
          "include_ou_paths": [],
          "exclude_ou_paths": []
        },
        "severity": 70,
        "remediation": "Enable encryption on EBS volumes",
        "open_findings": 12,
        "created_at": "2024-02-01",
        "updated_at": "2024-02-01",
        "status": "active"
      },
      {
        "policy_id": "IAMPasswordPolicyWeak",
        "description": "Detects weak IAM password policies",
        "service": "iam",
        "category": "access_control",
        "scope": {
          "include_accounts": [],
          "exclude_accounts": [],
          "include_tags": {},
          "exclude_tags": {},
          "include_ou_paths": [],
          "exclude_ou_paths": []
        },
        "severity": 60,
        "remediation": "Configure strong password policy in IAM",
        "open_findings": 3,
        "created_at": "2024-01-01",
        "updated_at": "2024-01-01",
        "status": "active"
      }
    ]
    ```
  - **Scope Field Definitions**:
    - `include_accounts`: Array of 12-digit AWS account IDs to include (empty = all accounts)
    - `exclude_accounts`: Array of 12-digit AWS account IDs to exclude 
    - `include_tags`: Object mapping tag keys to arrays of values: `{"Environment": ["prod", "staging"]}`
    - `exclude_tags`: Object mapping tag keys to arrays of values that resources must NOT have
    - `include_ou_paths`: Array of AWS Organizations OU paths to include
    - `exclude_ou_paths`: Array of AWS Organizations OU paths to exclude
  - **Scope Logic**: Policy applies to resources that match ALL include criteria AND match NONE of the exclude criteria

  - **Response**: Array of policy objects (consistent schema for all statuses)
    ```json
    [
      {
        "policy_id": "S3BucketPublic",
        "description": "Detects S3 buckets with public read access",
        "service": "s3",
        "category": "access_control",
        "severity": 90,
        "remediation": "Remove public access from bucket policy",
        "scope": {
          "include_accounts": ["123456789012"],
          "exclude_accounts": [],
          "include_tags": {"Environment": ["prod"]},
          "exclude_tags": {},
          "include_ou_paths": [],
          "exclude_ou_paths": []
        },
        "status": "active",
        "open_findings": 45,
        "created_at": "2024-01-15",
        "updated_at": "2024-01-20"
      },
      {
        "policy_id": "EBSUnencrypted",
        "description": "Detects EBS volumes without encryption at rest",
        "service": "ebs",
        "category": "encryption",
        "severity": 70,
        "remediation": "Enable encryption on EBS volumes",
        "scope": null,
        "status": "available",
        "open_findings": 0,
        "created_at": null,
        "updated_at": null
      }
    ]
    ```
  - **Status values**:
    - `active`: Policy is launched and evaluating resources
    - `available`: Policy definition exists but not launched
  - **For available policies**: `scope`, `created_at`, `updated_at` are `null`, `open_findings` is `0`

### Launch a new policy
- `POST /policies` - Launch a policy with scope and configuration
  - **Request body**:
    ```json
    {
      "policy_id": "S3BucketPublic",
      "scope": {
        "include_accounts": ["123456789012", "987654321098"],
        "exclude_accounts": [],
        "include_tags": {"Environment": ["prod"], "Team": ["security"]},
        "exclude_tags": {"SkipCompliance": ["true"]},
        "include_ou_paths": ["ou-root-123456789/ou-prod-abcdef"],
        "exclude_ou_paths": ["ou-root-123456789/ou-sandbox-xyz123"]
      },
      "severity": 90,
      "remediation": "Remove public access from bucket policy"
    }
    ```
  - **Required fields**: `policy_id`, `scope`
  - **Optional fields**: `severity` (overrides default), `remediation` (overrides default)
  - **Response** (201 Created):
    ```json
    {
      "message": "Policy S3BucketPublic launched successfully"
    }
    ```
  - **Error responses**:
    - 400: Missing required fields or validation error
    - 500: Internal server error
  - **Note**: After launching, a full scan is triggered automatically

### Update policy metadata
- `PUT /policies/{policy_id}` - Update a launched policy's metadata (scope, severity, remediation)
  - **Path params**: `policy_id` (required) - policy identifier
  - **Request body**:
    ```json
    {
      "scope": {
        "include_accounts": ["123456789012"],
        "exclude_accounts": [],
        "include_tags": {"Environment": ["prod"]},
        "exclude_tags": {},
        "include_ou_paths": [],
        "exclude_ou_paths": []
      },
      "severity": 95,
      "remediation": "Updated remediation instructions"
    }
    ```
  - **Optional fields**: `scope`, `severity`, `remediation` (update any combination, at least one required)
  - **Response** (200 OK):
    ```json
    {
      "message": "Policy S3BucketPublic updated successfully"
    }
    ```
  - **Error responses**:
    - 400: Missing policy_id or validation error
    - 404: Policy not found or not launched
    - 500: Internal server error
  - **Note**: Updating scope or severity triggers a re-scan of affected resources

### Delete a policy
- `DELETE /policies/{policy_id}` - Delete a policy and purge all findings
  - **Path params**: `policy_id` (required) - policy identifier
  - **Response** (200 OK):
    ```json
    {
      "message": "Policy S3BucketPublic deleted successfully",
      "findings_deleted": 45
    }
    ```
  - **Error responses**:
    - 404: Policy not found or not launched
    - 500: Internal server error
  - **Note**: Deleting a policy purges all associated findings and makes the policy available again for re-launch


# Data Entities

## TypeScript Interfaces (for UI generation)

```typescript
interface ScopeConfig {
  include_accounts: string[]        // 12-digit AWS account IDs
  exclude_accounts: string[]        // 12-digit AWS account IDs  
  include_tags: Record<string, string[]>  // Tag key to array of values
  exclude_tags: Record<string, string[]>  // Tag key to array of values
  include_ou_paths: string[]        // AWS Organizations OU paths
  exclude_ou_paths: string[]        // AWS Organizations OU paths
}

interface ActivePolicy {
  policy_id: string                 // Policy identifier
  description: string               // Policy description
  service: string                   // AWS service (e.g., "s3", "ec2")
  category: string                  // Policy category
  scope: ScopeConfig               // Targeting configuration
  severity: number                  // 0-100 numeric severity
  remediation: string              // Remediation instructions
  open_findings: number            // Count of ACTIVE findings
  created_at: string               // ISO date (YYYY-MM-DD)
  updated_at: string               // ISO date (YYYY-MM-DD)
  status: "active" | "suspended"   // Policy status
}

interface AvailablePolicy {
  policy_id: string                // Policy identifier
  description: string              // Policy description
  service: string                  // AWS service (e.g., "s3", "ec2")
  category: string                 // Policy category (e.g., "encryption", "access_control")
  severity: number                 // Default severity (0-100)
  remediation: string              // Remediation instructions
  status: "unlaunched"             // Always "unlaunched" for available policies
}

interface PolicyDetail {
  policy_id: string                // Policy identifier
  description: string              // Policy description
  service: string                  // AWS service (e.g., "s3", "ec2")
  category: string                 // Policy category (e.g., "encryption", "access_control")
  severity: number                 // 0-100 numeric severity
  remediation: string              // Remediation instructions
  scope: ScopeConfig | null        // Targeting configuration (null if unlaunched)
  status: "active" | "suspended" | "unlaunched"  // Policy status
  open_findings: number            // Count of ACTIVE findings (0 if unlaunched)
  created_at: string | null        // ISO date (YYYY-MM-DD) or null if unlaunched
  updated_at: string | null        // ISO date (YYYY-MM-DD) or null if unlaunched
}

interface Finding {
  arn: string                      // AWS resource ARN
  policy: string                   // Policy ID that triggered finding
  account_service: string          // Format: "{account_id}_{service}"
  severity: number                 // 0-100 numeric severity
  state: "ACTIVE" | "RESOLVED"    // Finding state
  first_seen: string              // ISO timestamp
  last_evaluated: string          // ISO timestamp
  evidence: Record<string, any>   // JSON evidence of violation
}

interface Resource {
  account_service: string          // Format: "{account_id}_{service}" 
  arn: string                     // AWS resource ARN
  last_seen_at: string           // ISO timestamp
  configuration: Record<string, any>  // Full resource configuration
}
```

# DynamoDB Schema

## Launched Policy (DynamoDB)
```python
{
    'PolicyId': 'S3BucketPublic',           # Primary Key
    'Status': 'active',                     # active | suspended
    'Scope': {                              # Targeting configuration
        'IncludeAccounts': ['123456789012'],
        'ExcludeAccounts': [],
        'IncludeTags': {'Environment': ['prod']},  # Tag values are arrays
        'ExcludeTags': {},
        'IncludeOuPaths': [],
        'ExcludeOuPaths': []
    },
    'Severity': 90,                         # Optional override (0-100)
    'Remediation': 'Custom remediation',    # Optional override
    'CreatedAt': '2024-01-15T10:30:00Z',
    'UpdatedAt': '2024-01-15T10:30:00Z'
}
```

## Finding (DynamoDB)
```python
{
    'ARN': 'arn:aws:s3:::my-bucket',        # Primary Key
    'Policy': 'S3BucketPublic',             # Sort Key
    'AccountService': '123456789012_s3',    # GSI Key
    'Severity': 90,                         # 0-100 (numeric severity)
    'State': 'ACTIVE',                      # ACTIVE | RESOLVED
    'FirstSeen': '2024-01-15T10:30:00Z',
    'LastEvaluated': '2024-01-15T10:30:00Z',
    'Evidence': {                           # JSON evidence of violation
        'bucket_policy': {...},
        'public_access_block': {...}
    }
}
```

## Resource (DynamoDB)
```python
{
    'AccountService': '123456789012_s3',    # Primary Key
    'ARN': 'arn:aws:s3:::my-bucket',        # Sort Key
    'LastSeenAt': '2024-01-15T10:30:00Z',
    'Configuration': {                      # Full resource configuration
        'bucket_policy': {...},
        'versioning': {...},
        'encryption': {...}
    }
}
```

## Policy Definition (Code)
```python
PolicyDefinition(
    policy_id='S3BucketPublic',
    description='Detects publicly accessible S3 buckets',
    service='s3',
    category='access_control',
    severity=90,
    remediation='Remove public access from bucket policy',
    evaluation_module='s3_bucket_public'
)
```