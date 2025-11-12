# Findings Summary Backend Calculation & Caching Proposal

## Problem Statement

The findings view component (`qrie-ui/components/findings-view.tsx`) currently performs calculations on the frontend that should be done on the backend:

1. **High findings calculation** (line 126): `highFindings = total - critical` ❌ **INCORRECT** - should be severity 50-89 only
2. **Resolved findings per policy** (lines 345, 395): `resolved = total - open`
3. **Policy sorting by severity** (lines 129-135): Client-side sorting using severity map

Additionally, the findings summary API performs a full table scan on every request without caching, similar to the dashboard summary issue that was already solved.

## Current State

### Backend (`findings_manager.py::get_findings_summary`)
- Performs table scan on every request
- Returns: `total_findings`, `open_findings`, `critical_findings`, `policies[]`
- Missing: high findings count, resolved counts per policy, severity per policy
- No caching mechanism

### Frontend (`findings-view.tsx`)
- Calculates `highFindings` from summary data
- Calculates `resolved` per policy from `total - open`
- Sorts policies by severity using client-side map
- Makes separate API calls for all-accounts vs per-account summaries

## Proposed Solution

### 1. Enhanced Backend Response Schema

Extend `get_findings_summary()` to return:

```python
{
    # Aggregate counts (ACTIVE findings only for severity breakdowns)
    "total_findings": 150,          # All findings (ACTIVE + RESOLVED)
    "open_findings": 45,            # ACTIVE findings
    "resolved_findings": 105,       # NEW: RESOLVED findings
    "critical_findings": 12,        # NEW: ACTIVE findings with severity >= 90
    "high_findings": 33,            # NEW: ACTIVE findings with severity 50-89
    "medium_findings": 15,          # NEW: ACTIVE findings with severity 25-49
    "low_findings": 5,              # NEW: ACTIVE findings with severity 0-24
    
    # Per-policy breakdown (pre-sorted by severity DESC)
    "policies": [
        {
            "policy": "IAMAccessKeyNotRotated",
            "severity": 90,         # NEW: include severity
            "total_findings": 25,
            "open_findings": 8,
            "resolved_findings": 17 # NEW: pre-calculated
        },
        # ... sorted by severity descending
    ]
}
```

**Note**: Summary figures update every 15 minutes via lazy refresh caching.

### 2. Lazy-Init Caching Strategy (Similar to Dashboard)

Use the existing `qrie_summary` DynamoDB table with the same lazy-refresh pattern:

#### Cache Keys:
- **All accounts**: `Type = "findings_summary_all"`
- **Per account**: `Type = "findings_summary_{account_id}"`

#### Cache Strategy:
```python
class FindingsManager:
    def get_findings_summary(self, account_id: Optional[str] = None) -> Dict:
        """Get findings summary with lazy refresh caching"""
        
        # Determine cache key
        cache_key = f"findings_summary_{account_id}" if account_id else "findings_summary_all"
        
        # Try cached data
        cached = self._get_cached_findings_summary(cache_key)
        if cached and self._is_fresh(cached, max_age_minutes=15):
            return cached['summary']
        
        # Cache miss/stale - acquire lock and refresh
        lock_acquired = self._try_acquire_lock(f"{cache_key}_lock", ttl_seconds=30)
        
        if not lock_acquired:
            # Serve stale data while refresh in progress
            if cached:
                return cached['summary']
            time.sleep(1)
            cached = self._get_cached_findings_summary(cache_key)
            if cached:
                return cached['summary']
        
        # Compute fresh summary
        summary = self._compute_findings_summary(account_id)
        
        # Cache it
        self._save_findings_summary(cache_key, summary)
        
        if lock_acquired:
            self._release_lock(f"{cache_key}_lock")
        
        return summary
```

#### Cache Characteristics:
- **TTL**: 15 minutes (shorter than dashboard's 1 hour since findings change more frequently)
- **Distributed locking**: Prevent thundering herd on cache miss
- **Stale-while-revalidate**: Serve stale data if refresh in progress
- **Separate caches**: All-accounts vs per-account summaries cached independently

### 3. Enhanced Computation Logic

```python
def _compute_findings_summary(self, account_id: Optional[str] = None) -> Dict:
    """Compute findings summary with all calculations"""
    
    # Build scan parameters
    scan_params = {
        'ProjectionExpression': '#policy, Severity, #state',
        'ExpressionAttributeNames': {
            '#policy': 'Policy',
            '#state': 'State'
        }
    }
    
    if account_id:
        scan_params['FilterExpression'] = 'begins_with(AccountService, :account_prefix)'
        scan_params['ExpressionAttributeValues'] = {':account_prefix': f"{account_id}_"}
    
    response = self.table.scan(**scan_params)
    
    # Aggregate counts
    total_findings = 0
    open_findings = 0
    resolved_findings = 0
    critical_findings = 0  # ACTIVE with severity >= 90
    high_findings = 0      # ACTIVE with severity 50-89
    medium_findings = 0    # ACTIVE with severity 25-49
    low_findings = 0       # ACTIVE with severity 0-24
    policy_counts = {}
    
    for item in response.get('Items', []):
        policy = item.get('Policy', '')
        severity = int(item.get('Severity', 0)) if item.get('Severity') is not None else 0
        state = item.get('State', '')
        
        total_findings += 1
        
        if state == 'ACTIVE':
            open_findings += 1
            # Severity breakdowns (ACTIVE only)
            if severity >= 90:
                critical_findings += 1
            elif severity >= 50:
                high_findings += 1
            elif severity >= 25:
                medium_findings += 1
            else:
                low_findings += 1
        else:
            resolved_findings += 1
        
        # Per-policy counts
        if policy not in policy_counts:
            policy_counts[policy] = {
                'total': 0,
                'open': 0,
                'resolved': 0,
                'severity': severity  # Store severity from first occurrence
            }
        policy_counts[policy]['total'] += 1
        if state == 'ACTIVE':
            policy_counts[policy]['open'] += 1
        else:
            policy_counts[policy]['resolved'] += 1
    
    # Get policy definitions for accurate severity (override from definition if available)
    from data_access.policy_manager import PolicyManager
    policy_manager = PolicyManager()
    
    for policy_id in policy_counts.keys():
        policy_def = policy_manager.get_policy_definition(policy_id)
        if policy_def:
            policy_counts[policy_id]['severity'] = policy_def.severity
    
    # Build sorted policies array
    policies = [
        {
            'policy': policy,
            'severity': counts['severity'],
            'total_findings': counts['total'],
            'open_findings': counts['open'],
            'resolved_findings': counts['resolved']
        }
        for policy, counts in policy_counts.items()
    ]
    
    # Sort by severity descending, then by open findings descending
    policies.sort(key=lambda x: (-x['severity'], -x['open_findings']))
    
    return {
        'total_findings': total_findings,
        'open_findings': open_findings,
        'resolved_findings': resolved_findings,
        'critical_findings': critical_findings,
        'high_findings': high_findings,
        'medium_findings': medium_findings,
        'low_findings': low_findings,
        'policies': policies
    }
```

### 4. Frontend Simplification

Remove all calculations from `findings-view.tsx`:

```typescript
// BEFORE (lines 126, 345, 395):
const highFindings = (summary?.total_findings || 0) - (summary?.critical_findings || 0)  // ❌ WRONG!
const resolved = policy.total_findings - policy.open_findings
const sortedSummaryPolicies = summary?.policies ? [...summary.policies].sort(...) : []

// AFTER:
const highFindings = summary?.high_findings || 0  // ✅ Correct: severity 50-89 only
const resolved = policy.resolved_findings
const sortedSummaryPolicies = summary?.policies || []  // Already sorted by backend
```

**UI Display Note**: Add footnote "Summary figures update every 15 minutes" near summary displays.

Remove policy severity map construction (lines 58-62) - no longer needed since backend includes severity in response.

## Implementation Plan

### Phase 1: Backend Enhancement (No Breaking Changes)
1. ✅ Add caching infrastructure to `FindingsManager`
2. ✅ Enhance `_compute_findings_summary()` to include new fields
3. ✅ Add cache helper methods (`_get_cached_findings_summary`, `_save_findings_summary`, etc.)
4. ✅ Update `get_findings_summary()` to use caching with lazy refresh
5. ✅ Backward compatible: New fields are additive, existing fields unchanged

### Phase 2: Frontend Simplification
1. ✅ Update `FindingsSummary` type in `lib/types.ts` to include new fields
2. ✅ Remove frontend calculations in `findings-view.tsx`
3. ✅ Remove policy severity map construction
4. ✅ Use backend-provided sorted policies directly

### Phase 3: Testing & Validation
1. ✅ Test cache hit/miss scenarios
2. ✅ Test all-accounts vs per-account summaries
3. ✅ Verify cache invalidation timing
4. ✅ Load test with concurrent requests (verify locking works)
5. ✅ Verify UI displays correct data

## Benefits

1. **Performance**: 15-minute cache reduces DynamoDB scans by ~95%
2. **Correctness**: Single source of truth for calculations
3. **Consistency**: All clients see same calculated values
4. **Simplicity**: Frontend code becomes simpler and more maintainable
5. **Scalability**: Distributed locking prevents thundering herd
6. **Cost**: Fewer DynamoDB scans = lower AWS costs

## Considerations

### Cache Invalidation
- **15-minute TTL**: Balances freshness vs performance
- **Lazy refresh**: Cache updates on next request after expiry
- **Stale-while-revalidate**: Users never wait for refresh

### Per-Account Cache Strategy
- **Cheap queries**: Per-account scans with `begins_with(AccountService, :account_prefix)` are fast
- **Cache anyway**: Provides consistency and reduces load even if query is fast
- **Independent caches**: All-accounts and per-account summaries cached separately

### Memory Considerations
- **Summary table**: Lightweight - only stores summary objects (~1-2KB each)
- **Cache keys**: `findings_summary_all` + one per account (~10-100 accounts typical)
- **Total storage**: < 1MB for typical deployment

## Migration Path

1. **Deploy backend changes** - New fields added, existing fields unchanged
2. **Verify API responses** - Check that new fields appear in responses
3. **Deploy frontend changes** - Remove calculations, use new fields
4. **Monitor cache hit rates** - Verify caching is working as expected
5. **Adjust TTL if needed** - Based on user feedback and data freshness requirements

## Alternative Considered: Real-time Calculation

**Rejected** because:
- Table scans are expensive at scale
- Findings change frequently but not constantly
- 15-minute staleness is acceptable for summary views
- Caching provides better UX (faster response times)
- Dashboard already uses this pattern successfully

## Open Questions

1. **Cache invalidation on policy launch/suspend?**
   - Current proposal: No, rely on TTL
   - Alternative: Explicitly invalidate cache on policy changes
   - Recommendation: Start with TTL-only, add explicit invalidation if needed

2. **Should we cache per-policy summaries too?**
   - Current proposal: No, only all-accounts and per-account
   - Use case: Policy detail view might benefit
   - Recommendation: Add if needed based on usage patterns

3. **Should we add cache warming on scan completion?**
   - Current proposal: No, lazy refresh only
   - Alternative: Warm cache after inventory/policy scans
   - Recommendation: Add if cache misses are too frequent
