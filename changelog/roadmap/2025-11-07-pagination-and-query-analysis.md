# Pagination & Query Efficiency Analysis

**Date:** 2025-11-07  
**Status:** Analysis Complete - Implementation Pending

## Executive Summary

Analyzed pagination strategy and query efficiency across inventory and findings flows. **Critical finding:** UI only displays first 100 items from backend, ignoring pagination tokens. Backend supports proper pagination but uses inefficient table scans for most query patterns.

---

## 1. Current Pagination Implementation

### **UI Layer - Consistent Pattern**

Both `findings-view.tsx` and `inventory-view.tsx` (after fix) now use:
- **Backend fetch:** `page_size: 100` (max allowed by API)
- **UI display:** 25 items per page (client-side slicing)
- **Problem:** UI ignores `next_token` - only shows first 100 items total

### **API Layer - Proper Pagination Support**

Both APIs support pagination correctly:

```python
# resources_api.py & findings_api.py
page_size = int(query_params.get('page_size', 50))
next_token = query_params.get('next_token')

# Max 100 items per request
if page_size > 100:
    page_size = 100

# Returns next_token in response if more data available
if 'LastEvaluatedKey' in response:
    result['next_token'] = base64.b64encode(...)
```

### **Data Layer - Pagination Modes**

#### **Inventory (`inventory_manager.py`)**

4 query modes with varying efficiency:

| Mode | Filters | DynamoDB Operation | Efficiency |
|------|---------|-------------------|------------|
| 1 | `account_id` + `service` | **Query** on PK `AccountService` | ✅ **Efficient** |
| 2 | `account_id` only | **Scan** with filter `begins_with(AccountService, "123_")` | ❌ **Inefficient** |
| 3 | `service` only | **Scan** with filter `ends_with(AccountService, "_s3")` | ❌ **Inefficient** |
| 4 | No filters | **Scan** entire table | ❌ **Inefficient** |

#### **Findings (`findings_manager.py`)**

Similar pattern - mostly scans:

```python
def get_findings_paginated(account_id, policy_id, state_filter, ...):
    # Uses SCAN with filters for all combinations
    # Only efficient query: get_findings_for_account_service() uses GSI
```

---

## 2. Current DynamoDB Schema

### **qrie_resources Table**
```
PK: AccountService (e.g., "123456789012_s3")
SK: ARN
GSI: None
```

**Problem:** Only supports efficient queries when both account AND service are specified.

### **qrie_findings Table**
```
PK: ARN
SK: Policy
GSI: AccountService-State-index
  - PK: AccountService
  - SK: State
```

**Better:** Has GSI for account+service queries, but still requires scans for:
- Policy-only filtering
- Account-only filtering (across all services)
- Service-only filtering (across all accounts)

---

## 3. Scaling Analysis

### **Scenario: 20 accounts × 20 services × 1000 resources = 400K total resources**

#### **Current Performance:**

| UI Action | Backend Query | Items Scanned | Items Returned | Efficiency |
|-----------|---------------|---------------|----------------|------------|
| Initial load (no filter) | Full scan | 400,000 | 100 | ❌ **0.025%** |
| Select account | Scan + filter | 400,000 | 100 | ❌ **0.025%** |
| Select service | Scan + filter | 400,000 | 100 | ❌ **0.025%** |
| Select account + service | Query | ~1,000 | 100 | ✅ **10%** |

**Cost Impact:**
- Full table scan: ~400K RCUs per request
- Query (account+service): ~1 RCU per request
- **400x cost difference** between scan and query!

---

## 4. Findings Flow Analysis

### **Current State:**

✅ **Better than inventory** - has GSI for account+service queries

```python
# findings_manager.py line 216
def get_findings_for_account_service(account_id, service, state_filter):
    # Uses GSI: AccountService-State-index
    query_params = {
        'IndexName': 'AccountService-State-index',
        'KeyConditionExpression': 'AccountService = :account_service',
        ...
    }
    response = self.table.query(**query_params)  # ✅ Efficient
```

### **Problems:**

❌ **UI doesn't use the efficient method** - calls `get_findings_paginated()` which uses scans:

```python
# findings_manager.py line 239
def get_findings_paginated(account_id, policy_id, state_filter, ...):
    # Uses SCAN with filters - inefficient!
    scan_params = {
        'FilterExpression': 'begins_with(AccountService, :account_prefix)',
        ...
    }
    response = self.table.scan(**scan_params)  # ❌ Inefficient
```

### **Findings UI Calls:**

```typescript
// findings-view.tsx line 52
getFindings({ page_size: 100 })  // Initial: full scan

// Line 82 - with filters
getFindings({ 
  account: selectedAccount,    // Still uses scan!
  policy: selectedPolicy,
  state: selectedStatus,
  page_size: 100 
})
```

---

## 5. Proposed Solutions

### **Option A: Add GSIs (Recommended)**

#### **For qrie_resources:**

```python
# Add GSI for service-only queries
resources.add_global_secondary_index(
    index_name="Service-ARN-index",
    partition_key=ddb.Attribute(name="Service", type=ddb.AttributeType.STRING),
    sort_key=ddb.Attribute(name="ARN", type=ddb.AttributeType.STRING),
    projection_type=ddb.ProjectionType.ALL
)
```

**Requires:** Adding `Service` attribute to all items (extract from AccountService)

#### **For qrie_findings:**

```python
# Add GSI for policy-only queries
findings.add_global_secondary_index(
    index_name="Policy-State-index",
    partition_key=ddb.Attribute(name="Policy", type=ddb.AttributeType.STRING),
    sort_key=ddb.Attribute(name="State", type=ddb.AttributeType.STRING),
    projection_type=ddb.ProjectionType.ALL
)
```

### **Option B: Redesign Schema (Better Long-term)**

#### **qrie_resources:**
```
Current: PK=AccountService, SK=ARN
Proposed: PK=AccountId, SK=ARN

GSI-1: PK=Service, SK=ARN (or Service_ARN)
GSI-2: PK=AccountService, SK=ARN (for account+service queries)
```

**Benefits:**
- Account-only queries: Use main table Query ✅
- Service-only queries: Use GSI-1 Query ✅
- Account+Service queries: Use GSI-2 Query ✅
- No scans needed for any common query pattern!

**Migration:** Requires data migration and redeployment

---

## 6. UI Pagination Fixes Needed

### **Current Problem:**

```typescript
// Both findings-view.tsx and inventory-view.tsx
const [resources, setResources] = useState<Resource[]>([])

// Only fetches first page
const resourcesData = await getResources(params)
setResources(resourcesData.resources)  // ❌ Ignores next_token!

// Client-side pagination on first 100 items
const currentInventory = resources.slice(startIndex, endIndex)
```

### **Proposed Fix:**

```typescript
const [resources, setResources] = useState<Resource[]>([])
const [nextToken, setNextToken] = useState<string | undefined>()
const [hasMore, setHasMore] = useState(true)

// Fetch with continuation
async function loadMoreResources() {
  const result = await getResources({ 
    ...params, 
    next_token: nextToken 
  })
  setResources(prev => [...prev, ...result.resources])
  setNextToken(result.next_token)
  setHasMore(!!result.next_token)
}

// Show "Load More" button or implement infinite scroll
{hasMore && (
  <Button onClick={loadMoreResources}>Load More</Button>
)}
```

---

## 7. Recommendations

### **Immediate (This Sprint):**

1. ✅ **Fix UI pagination** - Make inventory-view.tsx consistent with findings-view.tsx (DONE)
2. 🔄 **Implement "Load More" functionality** in both views
3. 📊 **Add loading indicators** for pagination

### **Short-term (Next Sprint):**

4. 🔧 **Add GSIs** to support efficient queries:
   - `qrie_resources`: Service-ARN-index
   - `qrie_findings`: Policy-State-index
5. 🔄 **Update data access layer** to use GSIs instead of scans
6. 📝 **Add Service attribute** to qrie_resources items

### **Long-term (Future):**

7. 🏗️ **Schema redesign** - Change PK to AccountId for both tables
8. 🔄 **Data migration** - Migrate existing data to new schema
9. 📊 **Performance monitoring** - Add CloudWatch metrics for query patterns

---

## 8. Current State Summary

### **What Works:**
- ✅ Backend pagination is properly implemented
- ✅ API respects `next_token` and returns it in responses
- ✅ Findings has GSI for account+service queries
- ✅ Both UIs now use consistent page_size (100) and display (25)

### **What's Broken:**
- ❌ UI ignores `next_token` - only shows first 100 items
- ❌ Most queries use inefficient table scans
- ❌ No GSI for service-only or policy-only queries
- ❌ Inventory has no GSIs at all

### **Impact at Scale (400K resources):**
- **Current:** 400K RCUs per request (scan entire table)
- **With GSIs:** ~1-10 RCUs per request (query specific partition)
- **Cost savings:** 40-400x reduction in read costs

---

## Next Steps

1. Implement "Load More" functionality in UI components
2. Create CDK changes to add GSIs
3. Write migration script to add Service attribute to existing resources
4. Update data access layer to prefer GSI queries over scans
5. Add CloudWatch alarms for scan operations (should be rare)
