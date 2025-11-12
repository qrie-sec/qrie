# Anti-Entropy Strategy Implementation

**Date**: 2025-11-04  
**Status**: Implemented

## Overview
Implemented anti-entropy strategy with scheduled inventory and policy scans to detect and correct drift between actual AWS state and qrie's inventory/findings. Removed backward compatibility code for cleaner pre-MVP implementation.

## Changes

### 1. ✅ Scheduled Scans (EventBridge Rules)

**Weekly Inventory Scan**:
- **Schedule**: Saturday 00:00 UTC (midnight)
- **Purpose**: Full inventory refresh across all services and accounts
- **Rationale**: Weekly cadence balances freshness with AWS API costs
- **EventBridge Rule**: `WeeklyInventorySchedule`

**Daily Policy Scan**:
- **Schedule**: Daily 04:00 UTC (4 AM)
- **Purpose**: Re-evaluate all resources against active policies
- **Rationale**: Daily scans catch policy violations quickly while allowing time for inventory updates
- **EventBridge Rule**: `DailyPolicyScanSchedule`

**Anti-Entropy Benefits**:
- Detects resources created/deleted outside of CloudTrail events
- Corrects any missed or failed event processing
- Ensures findings are eventually consistent with actual AWS state
- Provides regular health checks of the system

### 2. ✅ Scan Metrics Tracking

**Inventory Scan Metrics** (saved to `qrie_summary` table):
```python
{
    'Type': 'last_inventory_scan',
    'timestamp_ms': <scan_end_time>,
    'duration_ms': <scan_duration>,
    'service': 'all' | 's3' | 'ec2' | 'iam',
    'account_id': <account_id> | 'all',
    'resources_found': <total_count>
}
```

**Policy Scan Metrics** (saved to `qrie_summary` table):
```python
{
    'Type': 'last_policy_scan',
    'timestamp_ms': <scan_end_time>,
    'duration_ms': <scan_duration>,
    'processed_resources': <count>,
    'skipped_resources': <count>,
    'findings_created': <count>,
    'findings_closed': <count>,
    'policies_evaluated': <count>,
    'accounts_processed': <count>
}
```

### 3. ✅ Drift Detection in Dashboard

**Anti-Entropy Metrics** (added to dashboard summary):
```json
{
  "anti_entropy": {
    "last_inventory_scan": {
      "timestamp_ms": 1699056000000,
      "age_hours": 2.5,
      "duration_ms": 45000,
      "resources_found": 1234
    },
    "last_policy_scan": {
      "timestamp_ms": 1699142400000,
      "age_hours": 0.5,
      "duration_ms": 12000,
      "processed_resources": 1234,
      "findings_created": 15,
      "findings_closed": 8
    },
    "drift_detected": false
  }
}
```

**Drift Detection Logic**:
- **Inventory Drift**: Last scan > 8 days old (weekly + 1 day buffer)
- **Policy Drift**: Last scan > 26 hours old (daily + 2 hour buffer)
- **Alert**: `drift_detected: true` when either threshold exceeded

### 4. ✅ Removed Backward Compatibility

**Before** (`common.py`):
```python
# Time-based cache for customer accounts (15 minute TTL)
_accounts_cache: Optional[Dict] = None
_accounts_cache_time: float = 0
ACCOUNTS_CACHE_TTL_SECONDS = 15 * 60

def get_customer_accounts() -> List[Dict]:
    """Get list with time-based caching"""
    global _accounts_cache, _accounts_cache_time
    # ... caching logic ...
```

**After** (simplified, auto-paginating):
```python
def get_customer_accounts() -> List[Dict]:
    """Get all customer accounts with auto-pagination"""
    table = get_accounts_table()
    accounts = []
    last_key = None
    
    while True:
        if last_key:
            response = table.scan(ExclusiveStartKey=last_key)
        else:
            response = table.scan()
        
        accounts.extend(response.get('Items', []))
        
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
    
    return accounts
```

**Rationale**: Pre-MVP doesn't need backward compatibility. Simpler code, auto-pagination built-in.

## Files Modified

1. **`stacks/core_stack.py`**:
   - Updated EventBridge schedules to weekly inventory (Saturday midnight) and daily policy scans (4AM)

2. **`lambda/common.py`**:
   - Removed time-based caching and backward compatibility code
   - Simplified `get_customer_accounts()` with auto-pagination

3. **`lambda/inventory_generator/inventory_handler.py`**:
   - Added scan start/end time tracking
   - Save inventory scan metrics to summary table
   - Return scan duration and resource count

4. **`lambda/scan_processor/scan_handler.py`**:
   - Added scan start/end time tracking
   - Save policy scan metrics to summary table
   - Pass `describe_time_ms` to evaluators
   - Return scan duration and metrics

5. **`lambda/data_access/dashboard_manager.py`**:
   - Added `_get_anti_entropy_metrics()` method
   - Include anti-entropy metrics in dashboard summary
   - Drift detection logic with configurable thresholds

## Testing

**Manual Testing**:
1. Trigger inventory scan: `aws lambda invoke --function-name qrie_inventory_generator --payload '{"service":"all"}' response.json`
2. Trigger policy scan: `aws lambda invoke --function-name qrie_policy_scanner response.json`
3. Check dashboard: `GET /summary/dashboard` - verify `anti_entropy` section
4. Verify scan metrics in DynamoDB: `qrie_summary` table, items with `Type='last_inventory_scan'` and `Type='last_policy_scan'`

**Drift Testing**:
1. Wait > 26 hours without policy scan
2. Check dashboard - `drift_detected` should be `true`
3. Run policy scan
4. Check dashboard - `drift_detected` should be `false`

## Impact

**Operational Benefits**:
- **Reliability**: Catches missed events and ensures eventual consistency
- **Visibility**: Dashboard shows last scan times and drift status
- **Debugging**: Scan metrics help diagnose performance issues
- **Confidence**: Regular scans provide health checks

**Cost Considerations**:
- Weekly inventory scans: ~1 scan/week across all services
- Daily policy scans: ~7 scans/week (no AWS API calls, just DynamoDB reads)
- Minimal AWS API costs due to infrequent inventory scans

## Next Steps

1. Add alerting when `drift_detected: true` (SNS/email)
2. Add scan history/trends to dashboard (last 4 weeks)
3. Make scan schedules configurable per customer
4. Add manual scan trigger buttons in UI
