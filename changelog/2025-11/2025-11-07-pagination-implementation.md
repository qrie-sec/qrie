# Pagination Implementation - UI Changes

**Date:** 2025-11-07  
**Status:** Complete  
**Related:** `2025-11-07-pagination-and-query-analysis.md`, `roadmap/2025-11-00-dynamodb-schema-redesign.md`

## Summary

Implemented proper `next_token` pagination in both `findings-view.tsx` and `inventory-view.tsx` to support fetching all available data from the backend, not just the first 100 items.

---

## Changes Made

### **1. inventory-view.tsx**

**Added State Management:**
```typescript
const [loadingMore, setLoadingMore] = useState(false)
const [nextToken, setNextToken] = useState<string | undefined>()
const [hasMore, setHasMore] = useState(false)
```

**Track next_token in All Fetch Operations:**
```typescript
// Initial load
const resourcesData = await getResources({ page_size: 100 })
setResources(resourcesData.resources)
setNextToken(resourcesData.next_token)
setHasMore(!!resourcesData.next_token)

// Filtered load
const resourcesData = await getResources(params)
setResources(resourcesData.resources)
setNextToken(resourcesData.next_token)
setHasMore(!!resourcesData.next_token)
```

**Load More Function:**
```typescript
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
```

**UI Changes:**
- Added "(more available)" indicator when `hasMore` is true
- Added "Load More" button that appears when more data is available
- Button shows "Loading..." state while fetching

### **2. findings-view.tsx**

**Same pattern as inventory-view.tsx:**
- Added `loadingMore`, `nextToken`, `hasMore` state
- Track `next_token` in initial and filtered fetches
- Implemented `loadMoreFindings()` function
- Added "Load More" button with loading state

**Key Difference:**
Findings view has more complex filter logic (accounts, policies, status) but the pagination pattern is identical.

---

## Behavior

### **Before:**
- ❌ Only showed first 100 items from backend
- ❌ Client-side pagination on limited dataset
- ❌ No way to access items beyond first page
- ❌ User saw "Showing 1-25 of 100" even when 10,000+ items existed

### **After:**
- ✅ Shows first 100 items initially
- ✅ Client-side pagination on fetched items (25 per page)
- ✅ "Load More" button appears when more data available
- ✅ Clicking "Load More" fetches next 100 items and appends to list
- ✅ User can progressively load all data
- ✅ Indicator shows "(more available)" when applicable

---

## Query Efficiency Analysis

### **Current State - Where Efficient GSI Method Can Be Used**

The `get_findings_for_account_service()` method exists in `findings_manager.py` (line 216-238) and uses the efficient GSI:

```python
def get_findings_for_account_service(self, account_id: str, service: str, 
                                   state_filter: Optional[Literal['ACTIVE', 'RESOLVED']] = None,
                                   limit: Optional[int] = None) -> List[Finding]:
    """Get findings for an account/service combination using GSI"""
    account_service = f"{account_id}_{service}"
    
    query_params = {
        'IndexName': 'AccountService-State-index',
        'KeyConditionExpression': 'AccountService = :account_service',
        'ExpressionAttributeValues': {':account_service': account_service}
    }
    
    response = self.table.query(**query_params)  # ✅ Efficient Query!
    return [self._item_to_finding(item) for item in response.get('Items', [])]
```

**❌ Problem: This method is NEVER called!**

The API handler calls `get_findings_paginated()` which uses table scans:

```python
# findings_api.py line 53
result = get_findings_manager().get_findings_paginated(
    account_id=account,
    policy_id=policy,
    state_filter=state_filter,
    ...
)
# This internally does: self.table.scan(**scan_params)  ❌ Inefficient!
```

### **Where We COULD Use the Efficient Method**

**Scenario:** User selects single account + single service in UI

Currently this is not possible in the UI because:
- Findings view only allows selecting accounts and policies
- Inventory view allows account OR service (mutually exclusive)

**Potential Future Enhancement:**
If we add service filtering to findings view, we could optimize:

```python
# findings_api.py - Enhanced version
def handle_list_findings_paginated(query_params, headers):
    account = query_params.get('account')
    service = query_params.get('service')  # NEW parameter
    policy = query_params.get('policy')
    state = query_params.get('state')
    
    # Use efficient GSI when possible
    if account and service and not policy:
        # ✅ Use efficient GSI method
        result = get_findings_manager().get_findings_for_account_service(
            account_id=account,
            service=service,
            state_filter=state,
            limit=page_size
        )
    else:
        # Fall back to flexible scan-based method
        result = get_findings_manager().get_findings_paginated(...)
```

**Current Query Patterns:**

| UI Filter | Backend Method | DynamoDB Operation | Efficiency |
|-----------|----------------|-------------------|------------|
| Account only | `get_findings_paginated()` | Scan + filter | ❌ Inefficient |
| Policy only | `get_findings_paginated()` | Scan + filter | ❌ Inefficient |
| Account + Policy | `get_findings_paginated()` | Scan + filter | ❌ Inefficient |
| Status only | `get_findings_paginated()` | Scan + filter | ❌ Inefficient |
| **Account + Service** | **Not supported in UI** | **Could use GSI Query** | ✅ **Would be efficient** |

---

## Recommendations

### **Immediate (This Sprint):**
1. ✅ **DONE:** Implement `next_token` pagination in UI
2. 🔄 **TODO:** Add service filter to findings view UI
3. 🔄 **TODO:** Update `findings_api.py` to use efficient GSI when account+service provided

### **Short-term (Next Sprint):**
4. Implement schema redesign (see `roadmap/2025-11-00-dynamodb-schema-redesign.md`)
5. Add GSIs for policy-only and account-only queries
6. Update all data access methods to prefer GSI queries over scans

### **Code Example - Using Efficient Method:**

```python
# findings_api.py - Optimized version
def handle_list_findings_paginated(query_params, headers):
    account = query_params.get('account')
    service = query_params.get('service')
    policy = query_params.get('policy')
    state = query_params.get('state')
    page_size = int(query_params.get('page_size', 50))
    
    try:
        # Route to most efficient method
        if account and service and not policy:
            # ✅ Use GSI - most efficient
            findings = get_findings_manager().get_findings_for_account_service(
                account_id=account,
                service=service,
                state_filter=state,
                limit=page_size
            )
            result = {
                'findings': findings,
                'count': len(findings)
            }
            # Note: This method doesn't support pagination yet
            # Would need to add next_token support
        else:
            # Use flexible scan-based method
            result = get_findings_manager().get_findings_paginated(
                account_id=account,
                policy_id=policy,
                state_filter=state,
                page_size=page_size,
                next_token=next_token
            )
        
        # Format response...
```

---

## Testing

### **Manual Testing Checklist:**

**Inventory View:**
- [ ] Initial load shows first 100 resources
- [ ] "Load More" button appears when more data available
- [ ] Clicking "Load More" appends next 100 resources
- [ ] Button shows "Loading..." while fetching
- [ ] Button disappears when no more data
- [ ] Filtering resets pagination correctly
- [ ] Client-side pagination (25 per page) works correctly

**Findings View:**
- [ ] Initial load shows first 100 findings
- [ ] "Load More" button appears when more data available
- [ ] Clicking "Load More" appends next 100 findings
- [ ] Button shows "Loading..." while fetching
- [ ] Button disappears when no more data
- [ ] Account/policy/status filters reset pagination correctly
- [ ] Client-side pagination (25 per page) works correctly

### **Edge Cases:**
- [ ] Exactly 100 items (no "Load More" button)
- [ ] 101 items (button appears, then disappears after one click)
- [ ] Empty results (no button, no errors)
- [ ] Network error during "Load More" (error handling)

---

## Performance Impact

### **UI Performance:**
- ✅ Progressive loading prevents UI freeze with large datasets
- ✅ User can start interacting with first 100 items immediately
- ✅ Smooth experience even with 10,000+ items

### **Backend Performance:**
- ⚠️ Still uses table scans for most queries (no change)
- ✅ Pagination prevents timeout issues
- 🔄 Will improve significantly after schema redesign

---

## Files Modified

1. `/Users/shubham/dev/qrie/qrie-ui/components/inventory-view.tsx`
   - Added `loadingMore`, `nextToken`, `hasMore` state
   - Implemented `loadMoreResources()` function
   - Added "Load More" button to UI

2. `/Users/shubham/dev/qrie/qrie-ui/components/findings-view.tsx`
   - Added `loadingMore`, `nextToken`, `hasMore` state
   - Implemented `loadMoreFindings()` function
   - Added "Load More" button to UI

3. `/Users/shubham/dev/qrie/changelog/roadmap/2025-11-00-dynamodb-schema-redesign.md`
   - Created comprehensive schema redesign proposal
   - Documented migration strategy
   - Explained why GSI-2 (AccountService) is not needed

4. `/Users/shubham/dev/qrie/changelog/2025-11/2025-11-07-pagination-and-query-analysis.md`
   - Created detailed analysis of current pagination issues
   - Documented scaling problems
   - Proposed solutions

---

## Next Steps

1. Test pagination in dev environment
2. Add service filter to findings view UI
3. Update `findings_api.py` to use efficient GSI when possible
4. Begin Phase 1 of schema redesign (add new attributes)
5. Monitor query patterns in CloudWatch to identify scan operations
