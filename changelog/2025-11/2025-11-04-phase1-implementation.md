# Phase 1: Bootstrap vs Anti-Entropy Implementation

**Date**: 2025-11-04  
**Status**: ✅ Implemented

## Overview
Implemented explicit distinction between bootstrap and anti-entropy scans, added bootstrap scan trigger after policy launch, implemented findings purge on policy suspension, and added CLI commands for inventory generation and account scanning.

## Changes Implemented

### 1. ✅ Scan Type Distinction: `bootstrap` vs `anti-entropy`

**EventBridge Rules** (`stacks/core_stack.py`):
- Weekly inventory scan: Explicitly passes `scan_type: anti-entropy`
- Daily policy scan: Explicitly passes `scan_type: anti-entropy`

**Lambda Handlers**:
- `inventory_handler.py`: Only saves drift metrics for `anti-entropy` scans
- `scan_handler.py`: Only saves drift metrics for `anti-entropy` scans
- Default scan_type: `bootstrap` (fail-safe for manual invocations)

**Rationale**:
- **`bootstrap`**: Initial/manual scans that establish baseline (no drift metrics)
- **`anti-entropy`**: Scheduled scans that detect drift (updates drift metrics)

### 2. ✅ Bootstrap Scan Trigger After Policy Launch

**Implementation** (`lambda/api/policies_api.py`):
```python
# After successful policy launch
lambda_client = boto3.client('lambda')
scan_payload = {
    'policy_id': policy_id,
    'scan_type': 'bootstrap'  # Bootstrap scan, not anti-entropy
}
lambda_client.invoke(
    FunctionName='qrie_policy_scanner',
    InvocationType='Event',  # Async invocation
    Payload=json.dumps(scan_payload)
)
```

**Behavior**:
- Policy launch triggers async bootstrap scan
- Scan evaluates all resources in scope against new policy
- Creates initial findings
- Does NOT update drift metrics (this is the baseline)
- Errors logged but don't fail policy launch

**Response**:
```json
{
  "message": "Policy IAMAccessKeyNotRotated launched successfully",
  "bootstrap_scan_triggered": true
}
```

### 3. ✅ Findings Purge on Policy Suspension

**Implementation** (`lambda/data_access/findings_manager.py`):
```python
def purge_findings_for_policy(self, policy_id: str) -> int:
    """
    Purge all findings for a policy (when policy is suspended).
    Marks all findings as RESOLVED with reason POLICY_SUSPENDED.
    """
    # Scan for all ACTIVE findings with this policy
    response = self.table.scan(
        FilterExpression='Policy = :policy AND #state = :active_state',
        ...
    )
    
    # Update each finding to RESOLVED
    for item in response.get('Items', []):
        self.table.update_item(
            Key={'ARN': item['ARN'], 'Policy': item['Policy']},
            UpdateExpression='SET #state = :resolved, #lastEvaluated = :now, #resolvedReason = :reason',
            ExpressionAttributeValues={
                ':resolved': 'RESOLVED',
                ':now': now_ms,
                ':reason': 'POLICY_SUSPENDED'
            }
        )
```

**Behavior**:
- Called automatically when policy status changes to `suspended`
- Marks all ACTIVE findings as RESOLVED
- Adds `ResolvedReason: POLICY_SUSPENDED`
- Updates `LastEvaluated` timestamp
- Returns count of purged findings

**Response**:
```json
{
  "message": "Policy IAMAccessKeyNotRotated updated successfully",
  "findings_purged": 42
}
```

### 4. ✅ CLI Commands for Inventory and Scanning

**New Commands** (`qop.py`):

#### `--generate-inventory`
Generate inventory for all or specific account/service (bootstrap scan).

```bash
# Generate inventory for all accounts and services
./qop.py --generate-inventory --region us-east-1 --profile qop

# Generate inventory for specific account
./qop.py --generate-inventory --account-id 123456789012 --region us-east-1 --profile qop

# Generate inventory for specific service
./qop.py --generate-inventory --service s3 --region us-east-1 --profile qop
```

**Features**:
- Invokes `qrie_inventory_generator` Lambda
- Uses `scan_type: bootstrap` (no drift metrics)
- Displays resources found and duration
- Requires confirmation (unless `--skip-confirm`)

#### `--scan-account`
Scan specific account with all active policies (bootstrap or anti-entropy).

```bash
# Bootstrap scan for new account (default)
./qop.py --scan-account --account-id 123456789012 --region us-east-1 --profile qop

# Anti-entropy scan (for testing)
./qop.py --scan-account --account-id 123456789012 --scan-type anti-entropy --region us-east-1 --profile qop
```

**Features**:
- Two-step process:
  1. Generates inventory for account
  2. Runs policy scan
- Uses `scan_type: bootstrap` by default
- Displays findings created/closed and duration
- Requires confirmation (unless `--skip-confirm`)

**Optional Parameters**:
- `--account-id`: AWS account ID (required for `--scan-account`)
- `--service`: Service to scan (for `--generate-inventory`, default: all)
- `--scan-type`: Scan type (for `--scan-account`, choices: bootstrap|anti-entropy, default: bootstrap)

## Files Modified

1. **`stacks/core_stack.py`**:
   - Added `scan_type: anti-entropy` to EventBridge rules

2. **`lambda/inventory_generator/inventory_handler.py`**:
   - Added `scan_type` parameter with default `bootstrap`
   - Only save drift metrics for `anti-entropy` scans

3. **`lambda/scan_processor/scan_handler.py`**:
   - Added `scan_type` parameter with default `bootstrap`
   - Only save drift metrics for `anti-entropy` scans

4. **`lambda/api/policies_api.py`**:
   - Added boto3 import
   - Trigger bootstrap scan after policy launch
   - Purge findings when policy is suspended
   - Include purged count in response

5. **`lambda/data_access/findings_manager.py`**:
   - Added `purge_findings_for_policy()` method
   - Marks findings as RESOLVED with `POLICY_SUSPENDED` reason

6. **`qop.py`**:
   - Added `generate_inventory()` method
   - Added `scan_account()` method
   - Added `--generate-inventory` command
   - Added `--scan-account` command
   - Added optional parameters: `--account-id`, `--service`, `--scan-type`

## Testing

### Manual Testing

**1. Test Bootstrap vs Anti-Entropy**:
```bash
# Bootstrap scan (should NOT update drift metrics)
./qop.py --generate-inventory --region us-east-1 --profile qop

# Check dashboard - drift metrics should NOT change
curl -X GET "https://your-api-url/summary/dashboard"

# Wait for scheduled anti-entropy scan (Saturday midnight or Monday 4AM)
# Check dashboard - drift metrics SHOULD update
```

**2. Test Policy Launch Bootstrap Scan**:
```bash
# Launch a policy via API
curl -X POST "https://your-api-url/policies/launch" \
  -H "Content-Type: application/json" \
  -d '{"policy_id":"IAMAccessKeyNotRotated","scope":{"include_accounts":["123456789012"]}}'

# Response should include: "bootstrap_scan_triggered": true

# Check CloudWatch logs for qrie_policy_scanner
# Should see: "Skipping drift metrics for bootstrap scan"
```

**3. Test Findings Purge on Suspension**:
```bash
# Suspend a policy via API
curl -X PUT "https://your-api-url/policies/update" \
  -H "Content-Type: application/json" \
  -d '{"policy_id":"IAMAccessKeyNotRotated","status":"suspended"}'

# Response should include: "findings_purged": <count>

# Verify findings are marked as RESOLVED
# Check DynamoDB qrie_findings table - State should be RESOLVED, ResolvedReason should be POLICY_SUSPENDED
```

**4. Test CLI Commands**:
```bash
# Test generate-inventory
./qop.py --generate-inventory --region us-east-1 --profile qop --skip-confirm

# Test scan-account
./qop.py --scan-account --account-id 123456789012 --region us-east-1 --profile qop --skip-confirm
```

## Impact

**Operational Benefits**:
- **Clear Intent**: Bootstrap vs anti-entropy distinction makes scan purpose explicit
- **Accurate Drift Detection**: Only scheduled scans update drift metrics
- **Automated Policy Evaluation**: Policy launch automatically triggers initial scan
- **Clean Suspension**: Findings purged when policies are suspended
- **CLI Convenience**: Easy commands for inventory generation and account scanning

**User Experience**:
- Policy launch is now a one-step operation (scan triggered automatically)
- Policy suspension cleanly removes findings (no orphaned data)
- Clear feedback on findings purged and scans triggered
- CLI commands for common operational tasks

## Next Steps (Phase 2)

1. **Documentation**: Create docs section in qrie-ui with:
   - Onboarding guide (inventory generation)
   - Policy Management guide (launch/suspend)
   - Account Management guide (add/remove accounts)

2. **UI Enhancements**:
   - Add "Inventory in Progress" indicator
   - Add warning dialogs for expensive operations
   - Add policy suspension confirmation with findings count
   - Add account management UI

3. **Future Features** (Roadmap):
   - Policy pause (findings retained, not purged)
   - Findings archive to S3 before purge
   - Findings history tracking
