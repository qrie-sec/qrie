# Race Condition Fixes and Code Review Improvements

**Date**: 2025-11-03  
**Status**: Implemented

## Overview
Addressed race conditions in findings and inventory updates by implementing one-shot conditional DynamoDB writes with millisecond timestamps. Simplified event handler logic and moved policy filtering to PolicyManager. Removed defaults and implemented fail-fast for critical path operations.

## Changes

### 1. ✅ Universal Timestamp: DescribeTime

**Key Decision**: Use **describe call timestamp** as the universal timestamp across both inventory and findings tables.

**Schema Changes**:
- **Resources table**: Added `DescribeTime` field (milliseconds) when config was captured via describe call
- **Findings table**: Added `DescribeTime` field (milliseconds) when config was evaluated, same as resource's DescribeTime
- **Kept**: `LastSeenAt` in resources (for backward compatibility and display)
- **Kept**: `LastEvaluated` in findings (for audit trail)
- **Format**: Millisecond timestamps for better precision and ordering

**Rationale**: The describe call timestamp is the source of truth for:
- When the configuration snapshot was captured
- Ordering of updates (newer describe time = fresher data)
- Staleness detection (compare describe times, not event times)

**Fail-Fast**: `describe_time_ms` is now REQUIRED (no defaults) - critical path operations must be explicit

### 2. ✅ Conditional DynamoDB Updates to Prevent Race Conditions

**Problem**: Check-then-write pattern had race conditions where two competing writes could be written out of order.

**Solution**: Implemented atomic conditional updates using DynamoDB's `ConditionExpression`.

#### Findings Manager (`findings_manager.py`)
- **Before**: Try-except dance with separate update and create paths
- **After**: One-shot `update_item` with unified condition that handles both create and update atomically
- **Behavior**: 
  - Single `update_item` call with `if_not_exists()` for FirstSeen
  - Condition allows: new items, items missing DescribeTime, or items with older DescribeTime
  - If condition fails, skip update (existing describe time is more recent)

```python
# One-shot atomic update - handles both create and update
self.table.update_item(
    Key=key,
    UpdateExpression=(
        "SET #state = :state, "
        "#severity = :sev, "
        "#describeTime = :now, "
        "#lastEvaluated = :now, "
        "#evidence = :evidence, "
        "#accountService = :acct, "
        "#firstSeen = if_not_exists(#firstSeen, :firstSeen)"  # Only set if new
    ),
    ConditionExpression=(
        "attribute_not_exists(#arn) OR "           # Allow new items
        "attribute_not_exists(#describeTime) OR "  # Allow items missing timestamp
        "#describeTime < :now"                      # Allow older items
    ),
    ...
)
```

**Benefits**:
- Single DynamoDB call (more efficient)
- Simpler code (no try-except dance)
- Handles both create and update atomically
- No redundant `attribute_exists(ARN)` check

#### Inventory Manager (`inventory_manager.py`)
- Same one-shot approach as findings_manager
- Added `describe_time_ms` parameter (REQUIRED, no default)
- Added `get_resource_by_arn()` method for direct ARN-based lookups

**Key Principle**: The describe call timestamp is when the config snapshot was captured - this is the source of truth for ordering and staleness detection.

### 3. ✅ Simplified Event Handler

**Changes**:
1. **Direct ARN lookup**: Use `inventory_manager.get_resource_by_arn(arn)` instead of scanning all resources
2. **Staleness check**: Check if event time is stale compared to existing inventory before processing
3. **Capture describe time**: Capture timestamp when calling `_describe_resource()` - this is the snapshot time
4. **Event timestamp extraction**: Added `_extract_event_time()` stub to extract timestamp from CloudTrail events

**Before**:
```python
# Scan all resources for account/service
existing_resources = inventory_manager.get_resources_by_account_service(account_service)
existing_config = None
for res in existing_resources:
    if res.get('ARN') == resource_arn:
        existing_config = res.get('Configuration', {})
        break
```

**After**:
```python
# Direct lookup by ARN
existing_resource = inventory_manager.get_resource_by_arn(resource_arn)

# Check staleness
if existing_resource:
    existing_snapshot_time = existing_resource.get('LastSeenAt', '')
    if event_time <= existing_snapshot_time:
        print(f"Skipping stale event...")
        continue

# Capture describe time when fetching config
describe_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
new_config = _describe_resource(resource_arn, account_id, service)

# Update with describe time
inventory_manager.upsert_resource(..., describe_time=describe_time)
```

**Benefits**:
- More efficient (no full scan)
- Prevents processing stale events
- Clearer intent

### 4. ✅ Moved Policy Filtering to PolicyManager

**Problem**: Event handler had complex policy filtering logic that belonged in PolicyManager.

**Solution**: Added `get_active_policies_for_service(service)` method to PolicyManager.

**Before** (in event_handler.py):
```python
launched_policies = policy_manager.list_launched_policies()
active_policies = [p for p in launched_policies if p.status == 'active']

service_policies = []
for policy in active_policies:
    policy_def = policy_manager.get_policy_definition(policy.policy_id)
    if policy_def and policy_def.service == service:
        service_policies.append(policy)
```

**After**:
```python
service_policies = policy_manager.get_active_policies_for_service(service)
```

**Benefits**:
- Single responsibility - PolicyManager owns policy filtering logic
- Reusable across event handler and scan handler
- Cleaner, more maintainable code

## Files Modified

1. `/Users/shubham/dev/qrie/qrie-infra/lambda/data_access/findings_manager.py`
   - Implemented conditional updates in `put_finding()`
   - Added `evaluation_time` parameter

2. `/Users/shubham/dev/qrie/qrie-infra/lambda/data_access/inventory_manager.py`
   - Implemented conditional updates in `upsert_resource()`
   - Added `snapshot_time` parameter
   - Added `get_resource_by_arn()` method

3. `/Users/shubham/dev/qrie/qrie-infra/lambda/data_access/policy_manager.py`
   - Added `get_active_policies_for_service(service)` method

4. `/Users/shubham/dev/qrie/qrie-infra/lambda/event_processor/event_handler.py`
   - Use `get_resource_by_arn()` for direct lookups
   - Added staleness check based on event time
   - Use `get_active_policies_for_service()` for policy filtering
   - Added `_extract_event_time()` stub
   - Pass `snapshot_time` to `upsert_resource()`

## Testing Recommendations

1. **Race Condition Testing**:
   - Simulate concurrent updates to same finding/resource with different timestamps
   - Verify that only the most recent update is persisted
   - Test both update and create paths

2. **Staleness Testing**:
   - Send events with old timestamps
   - Verify they are skipped if inventory has newer snapshot
   - Test with missing inventory (should process)

3. **Policy Filtering**:
   - Verify `get_active_policies_for_service()` returns correct policies
   - Test with multiple services and statuses
   - Verify caching behavior

## Exception Handling

**Fail-Fast Pattern**: All helper functions raise exceptions instead of returning None/empty values.

**Event Processing Loop**:
- Single try-except block catches all exceptions per record
- Logs full stack trace with record ID
- Continues to next record (doesn't fail entire batch)
- Top-level handler re-raises to let Lambda runtime handle fatal errors

**Helper Functions**:
- `_extract_arn_from_event()` - Raises `NotImplementedError` (stub) or `ValueError` (invalid ARN)
- `_extract_event_time()` - Raises `NotImplementedError` (stub) or `ValueError` (invalid timestamp)
- `_describe_resource()` - Raises `NotImplementedError` (stub), `ValueError` (invalid resource), or `ClientError` (AWS API failure)

**Benefits**:
- No defensive checks in event loop (cleaner code)
- Validation logic lives in helper functions (single responsibility)
- Full stack traces for debugging
- Batch processing continues even if individual records fail

## TODOs

The following stubs need implementation when we have real CloudTrail event examples:

1. `_extract_arn_from_event(event)` - Extract resource ARN from CloudTrail event
2. `_extract_event_time(event)` - Extract timestamp when describe call was made
3. `_describe_resource(arn, account_id, service)` - Describe resource using AWS APIs

## Impact

- **Correctness**: Eliminates race conditions in findings and inventory updates
- **Performance**: More efficient event processing (direct ARN lookup vs scan)
- **Maintainability**: Cleaner separation of concerns, reusable policy filtering
- **Reliability**: Prevents stale data from overwriting fresh data
