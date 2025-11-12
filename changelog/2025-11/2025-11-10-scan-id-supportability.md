# Scan ID Supportability Enhancement

**Date:** 2025-11-10  
**Status:** ✅ Complete

## Summary

Added unique `scan_id` (UUID) to every inventory generation and policy scan for improved supportability and traceability. Scan IDs are now included in all log messages, stored in metrics tables, and returned in API responses.

## Changes Implemented

### 1. Inventory Generation (`inventory_handler.py`)

**Added:**
- Generate unique `scan_id` using `uuid.uuid4()` at the start of each inventory generation
- Include `scan_id` in all log messages with `[{scan_id}]` prefix
- Store `scan_id` in summary table metrics (`last_inventory_scan`)
- Return `scan_id` in Lambda response body
- Include `scan_id` in error responses

**Example Log Output:**
```
[a1b2c3d4-e5f6-7890-abcd-ef1234567890] Starting inventory generation: service=s3, account=all, scan_type=bootstrap
[a1b2c3d4-e5f6-7890-abcd-ef1234567890] Saved inventory scan metrics (anti-entropy): 150 resources found in 2500ms
```

**Response Format:**
```json
{
  "statusCode": 200,
  "body": {
    "message": "Inventory generation completed",
    "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "results": [...],
    "scan_duration_ms": 2500,
    "total_resources": 150
  }
}
```

---

### 2. Policy Scanning (`scan_handler.py`)

**Added:**
- Generate unique `scan_id` using `uuid.uuid4()` at the start of each policy scan
- Include `scan_id` in all log messages with `[{scan_id}]` prefix
- Store `scan_id` in summary table metrics (`last_policy_scan`)
- Return `scan_id` in Lambda response body

**Example Log Output:**
```
[b2c3d4e5-f6a7-8901-bcde-f12345678901] Starting policy scan: policy_id=all, service=all, scan_type=bootstrap
[b2c3d4e5-f6a7-8901-bcde-f12345678901] Error evaluating arn:aws:s3:::bucket with policy S3BucketPublic: ...
[b2c3d4e5-f6a7-8901-bcde-f12345678901] Saved policy scan metrics (anti-entropy): 500 resources processed in 15000ms
```

**Response Format:**
```json
{
  "statusCode": 200,
  "body": {
    "scan_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "processed_resources": 500,
    "skipped_resources": 2,
    "findings_created": 15,
    "findings_closed": 8,
    "policies_evaluated": 10,
    "accounts_processed": 3,
    "scan_duration_ms": 15000
  }
}
```

---

### 3. Dashboard Metrics (`dashboard_manager.py`)

**Added:**
- Include `scan_id` in anti-entropy metrics for last inventory scan
- Include `scan_id` in anti-entropy metrics for last policy scan

**Response Format:**
```json
{
  "anti_entropy": {
    "last_inventory_scan": {
      "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "timestamp_ms": 1699564800000,
      "age_hours": 2.5,
      "duration_ms": 2500,
      "resources_found": 150
    },
    "last_policy_scan": {
      "scan_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "timestamp_ms": 1699568400000,
      "age_hours": 1.0,
      "duration_ms": 15000,
      "processed_resources": 500,
      "findings_created": 15,
      "findings_closed": 8
    },
    "drift_detected": false
  }
}
```

---

### 4. QOP Orchestrator (`qop.py`)

**Updated:**
- Display `scan_id` in inventory generation output
- Display `scan_id` in policy scan output

**Example Output:**
```
✅ Inventory generation completed:
   - Scan ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
   - Resources found: 150
   - Duration: 2500ms

✅ Policy scan completed:
   - Scan ID: b2c3d4e5-f6a7-8901-bcde-f12345678901
   - Resources processed: 500
   - Findings created: 15
   - Findings closed: 8
   - Duration: 15000ms
```

---

## Benefits

### 1. **Improved Debugging**
- Every scan operation has a unique identifier
- Easy to correlate logs across different services
- Can trace entire scan lifecycle from start to finish

### 2. **Better Supportability**
- Customer support can reference specific scan IDs when investigating issues
- Scan IDs stored in metrics tables for historical analysis
- Error messages include scan ID for quick log filtering

### 3. **Enhanced Monitoring**
- Dashboard shows scan IDs for last inventory and policy scans
- Can track which specific scan detected drift
- Easier to identify problematic scans

### 4. **Log Filtering**
```bash
# Filter CloudWatch logs by scan ID
aws logs filter-log-events \
  --log-group-name /aws/lambda/qrie_inventory_generator \
  --filter-pattern "[a1b2c3d4-e5f6-7890-abcd-ef1234567890]"
```

---

## Files Modified

1. **`lambda/inventory_generator/inventory_handler.py`**
   - Added `import uuid`
   - Generate `scan_id` at start of `lambda_handler()`
   - Include `scan_id` in all log messages
   - Store `scan_id` in metrics table
   - Return `scan_id` in response

2. **`lambda/scan_processor/scan_handler.py`**
   - Added `import uuid`
   - Generate `scan_id` at start of `scan_policy()`
   - Include `scan_id` in all log messages
   - Store `scan_id` in metrics table
   - Return `scan_id` in response

3. **`lambda/data_access/dashboard_manager.py`**
   - Include `scan_id` in `_get_anti_entropy_metrics()` response

4. **`qop.py`**
   - Display `scan_id` in inventory generation output
   - Display `scan_id` in policy scan output

---

## Testing

**Manual Testing:**
```bash
# Generate inventory and capture scan ID
./qop.py --generate-inventory --region us-east-1 --profile qop

# Check logs for scan ID
aws logs tail /aws/lambda/qrie_inventory_generator --follow --region us-east-1 --profile qop

# Verify scan ID in dashboard
curl https://api.example.com/summary/dashboard
```

---

## Future Enhancements

1. **UI Integration:**
   - Display scan IDs in dashboard UI
   - Add "View Scan Details" link that filters logs by scan ID
   - Show scan history with scan IDs

2. **Scan ID Propagation:**
   - Pass scan ID to child operations (e.g., resource describe calls)
   - Include scan ID in findings metadata
   - Track scan ID through entire evaluation pipeline

3. **Alerting:**
   - Include scan ID in alert notifications
   - Link directly to CloudWatch logs filtered by scan ID

4. **Metrics:**
   - Track scan success/failure rates by scan ID
   - Identify slow scans by scan ID
   - Correlate scan IDs with error rates
