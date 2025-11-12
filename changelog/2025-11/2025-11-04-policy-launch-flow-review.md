# Policy Launch Flow & Management Operations Review

**Date**: 2025-11-04  
**Status**: Proposal + Implementation Gaps

## Overview
Review of the three main operational flows: Inventory Generation, Account Management, and Policy Management. This document identifies implementation gaps and proposes solutions.

---

## 1. Inventory Generation

### **Purpose**
Inventory is necessary for policy scans to function. Without inventory, policies have nothing to evaluate.

### **Current Implementation** ✅
- **Handler**: `inventory_handler.py`
- **Trigger Methods**:
  - Manual: Lambda invoke with `{"service": "all"}`
  - Scheduled: Weekly (Saturday 00:00 UTC) via EventBridge
- **Scan Types**: Per-service (`s3`, `ec2`, `iam`) or all services

### **Proposed Flow**
1. **On Qrie Onboarding** (first-time setup):
   - Customer follows onboarding instructions on qrie-ui website
   - Runs initial inventory generation: `./qop.py --generate-inventory --region us-east-1 --profile qop`
   - **Scan Type**: `bootstrap` (does NOT update drift metrics)
   - Wait for completion before proceeding
   - Check completion: Dashboard shows inventory count > 0

2. **Ongoing Operations**:
   - Weekly auto-scan (Saturday midnight)
   - **Scan Type**: `anti-entropy` (updates drift metrics)

### **Implementation Gaps**
- ❌ No `--generate-inventory` command in qop.py
- ❌ No clear "inventory in progress" indicator in UI
- ❌ No onboarding documentation in qrie-ui

---

## 2. Account Management

### **Purpose**
Manage customer AWS accounts that qrie monitors. New accounts need inventory before policies can evaluate them.

### **Current Implementation** ⚠️ Partial
- **Storage**: `qrie_accounts` DynamoDB table
- **Auto-Discovery**: Weekly scan catches new accounts
- **Manual Operations**: None implemented

### **Proposed Flow**
1. **Adding New Account**:
   - Add account to `qrie_accounts` table (manual DynamoDB operation for now)
   - **Option A**: Run manual bootstrap scan immediately
     ```bash
     ./qop.py --scan-account <account-id> --scan-type bootstrap --region us-east-1 --profile qop
     ```
   - **Option B**: Wait for next weekly auto-scan (Saturday midnight)
     - ⚠️ **Warning**: Findings will be reported as drift until first scan completes

2. **Removing Account**:
   - Remove from `qrie_accounts` table
   - Findings/inventory for that account remain in DB (soft delete)
   - Future: Hard delete option with confirmation

### **Implementation Gaps**
- ❌ No `--scan-account` command in qop.py
- ❌ No account add/remove CLI commands
- ❌ No drift flagging for accounts added between weekly scans
- ❌ No UI for account management

---

## 3. Policy Management

### **Purpose**
Launch, suspend, and manage security/compliance policies. Policy launch triggers initial evaluation of all resources.

### **Current Implementation** ⚠️ Partial
- **Launch Policy**: ✅ `POST /policies/launch`
- **Update Policy**: ✅ `PUT /policies/update` (can suspend)
- **Suspend Policy**: ✅ Status change to `suspended`
- **Findings Purge**: ❌ **NOT IMPLEMENTED**

### **Proposed Flow**

#### **Launching a Policy**
1. User clicks "Launch Policy" in UI
2. API: `POST /policies/launch` with policy_id, scope, severity, remediation
3. **Trigger Bootstrap Scan** (NEW):
   - After successful policy launch, trigger scan with `scan_type: bootstrap`
   - Scan evaluates all resources in scope against the new policy
   - Creates initial findings
   - Does NOT update drift metrics (this is the baseline)

```python
# In handle_launch_policy() after successful launch:
# Trigger bootstrap scan for the newly launched policy
lambda_client = boto3.client('lambda')
lambda_client.invoke(
    FunctionName='qrie_policy_scanner',
    InvocationType='Event',  # Async
    Payload=json.dumps({
        'policy_id': policy_id,
        'scan_type': 'bootstrap'  # Bootstrap scan, not anti-entropy
    })
)
```

#### **Suspending a Policy**
1. User clicks "Suspend Policy" in UI
2. API: `PUT /policies/update` with `status: suspended`
3. **Purge Findings** (NEW):
   - Update all findings for this policy to `State: RESOLVED`
   - Add `ResolvedReason: POLICY_SUSPENDED`
   - Add `ResolvedAt: <timestamp>`
   - ⚠️ **Warning**: Findings are purged and cannot be recovered

**Future Enhancements** (Roadmap):
- **Pause Policy**: Findings flagged but retained, can resume later
- **Findings Archive**: Export purged findings to S3 before deletion
- **Findings History**: Track policy suspension/resume events

#### **Important Notes**
- ⚠️ **Do not randomly enable/disable policies** - Policy launch is expensive:
  - Scans all resources in scope (potentially thousands)
  - Creates/updates findings in DynamoDB
  - Can take several minutes for large inventories
- **Best Practice**: Launch policies once, adjust scope/severity as needed

### **Implementation Gaps**
- ❌ No bootstrap scan trigger after policy launch
- ❌ No findings purge on policy suspension
- ❌ No warning in UI about expensive operations
- ❌ No roadmap link for future features

---

## Scan Type Refinement

### **Proposed Values**
- **`bootstrap`**: Initial/manual scans that establish baseline
  - Policy launch (first evaluation)
  - New account onboarding
  - Manual inventory generation
  - Does NOT update drift metrics
  
- **`anti-entropy`**: Scheduled scans that detect drift
  - Weekly inventory scan (Saturday midnight)
  - Daily policy scan (4 AM)
  - Updates drift metrics for monitoring

### **Implementation Changes**

#### **EventBridge Rules**:
```python
# Weekly inventory - anti-entropy
events.Rule(
    self, "WeeklyInventorySchedule",
    schedule=events.Schedule.cron(minute="0", hour="0", week_day="SAT"),
    targets=[targets.LambdaFunction(
        inventory_generator_fn,
        event=events.RuleTargetInput.from_object({
            "service": "all",
            "scan_type": "anti-entropy"  # Changed from "scheduled"
        })
    )],
    description="Weekly full inventory scan - Saturday 00:00 UTC (anti-entropy)"
)

# Daily policy scan - anti-entropy
events.Rule(
    self, "DailyPolicyScanSchedule",
    schedule=events.Schedule.cron(minute="0", hour="4"),
    targets=[targets.LambdaFunction(
        policy_scanner_fn,
        event=events.RuleTargetInput.from_object({
            "scan_type": "anti-entropy"  # Changed from "scheduled"
        })
    )],
    description="Daily policy scan - 04:00 UTC (anti-entropy)"
)
```

#### **Lambda Handlers**:
```python
# Only save drift metrics for anti-entropy scans
scan_type = event.get('scan_type', 'bootstrap')  # Default to bootstrap for safety

if scan_type == 'anti-entropy':
    # Save metrics to summary table
    summary_table.put_item(Item={
        'Type': 'last_inventory_scan',
        'timestamp_ms': scan_end_ms,
        # ... other metrics
    })
else:
    print(f"Skipping drift metrics for {scan_type} scan")
```

---

## Documentation Structure for qrie-ui

### **Proposed Sections**

#### **1. Onboarding** 📘
**Content**:
- Prerequisites (AWS account, IAM roles, EventBridge setup)
- Step-by-step onboarding instructions
- **Initial Inventory Generation**:
  - Command: `./qop.py --generate-inventory --region us-east-1 --profile qop`
  - Expected duration: 5-15 minutes depending on resource count
  - **Do nothing else until inventory completes**
  - How to check completion:
    - Dashboard shows "Resources: X" (X > 0)
    - Check inventory scan metrics: `anti_entropy.last_inventory_scan.timestamp_ms`
- Troubleshooting common issues

#### **2. Policy Management** 🛡️
**Content**:
- **Launching Policies**:
  - How to launch a policy from UI
  - Understanding scope (accounts, tags, OUs)
  - Customizing severity and remediation
  - ⚠️ **Warning**: Policy launch is expensive, don't enable/disable frequently
  - Bootstrap scan automatically triggered after launch
  - Expected duration: 2-10 minutes depending on resource count
  
- **Suspending Policies**:
  - How to suspend a policy from UI
  - ⚠️ **Warning**: Findings are purged and cannot be recovered
  - Alternative: Adjust scope to exclude resources instead
  
- **Future Features** (link to roadmap):
  - Policy pause (findings retained)
  - Findings archive to S3
  - Custom policy definitions

#### **3. Account Management** 🏢
**Content**:
- **Adding New Accounts**:
  - Prerequisites (IAM role, EventBridge rules)
  - Command: `./qop.py --add-account <account-id> --region us-east-1 --profile qop`
  - **Option 1**: Run bootstrap scan immediately (recommended)
    - Command: `./qop.py --scan-account <account-id> --scan-type bootstrap`
  - **Option 2**: Wait for next weekly auto-scan (Saturday midnight)
    - ⚠️ Findings reported as drift until first scan
  
- **Removing Accounts**:
  - Command: `./qop.py --remove-account <account-id> --region us-east-1 --profile qop`
  - Findings/inventory remain in DB (soft delete)
  - Future: Hard delete option

- **Viewing Accounts**:
  - Dashboard shows account count
  - Inventory page filters by account

---

## Implementation Priority

### **Phase 1: Critical Gaps** (Immediate)
1. ✅ Update scan_type from `scheduled` to `anti-entropy`
2. ✅ Add bootstrap scan trigger after policy launch
3. ✅ Implement findings purge on policy suspension
4. ✅ Add `--generate-inventory` command to qop.py
5. ✅ Add `--scan-account` command to qop.py

### **Phase 2: Documentation** (Next)
1. Create Documentation section in qrie-ui
2. Write Onboarding guide
3. Write Policy Management guide
4. Write Account Management guide

### **Phase 3: UI Enhancements** (Later)
1. Add "Inventory in Progress" indicator
2. Add warning dialogs for expensive operations
3. Add account management UI
4. Add policy suspension confirmation dialog

---

## Files to Modify

1. **`stacks/core_stack.py`**: Update EventBridge rules with `anti-entropy` scan_type
2. **`lambda/inventory_generator/inventory_handler.py`**: Check scan_type, only save metrics for `anti-entropy`
3. **`lambda/scan_processor/scan_handler.py`**: Check scan_type, only save metrics for `anti-entropy`
4. **`lambda/api/policies_api.py`**: Trigger bootstrap scan after policy launch
5. **`lambda/data_access/findings_manager.py`**: Add `purge_findings_for_policy()` method
6. **`qop.py`**: Add `--generate-inventory` and `--scan-account` commands
7. **`qrie-ui/app/docs/`**: Create new documentation section (new directory)
