# Scan Workflow Architecture


**Date:** November 6, 2025  
**Status:** Active

## Overview

Qrie uses a **decoupled scheduled workflow** for inventory and policy scanning, with real-time updates via EventBridge.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  NIGHTLY WORKFLOW (EventBridge Schedules)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Inventory Generation (12 AM UTC Saturday)               │
│     EventBridge Rule → qrie_inventory_generator             │
│     ├─ Scans all customer accounts                          │
│     ├─ Calls AWS APIs (ListBuckets, DescribeInstances, etc) │
│     └─ Writes to qrie_resources table                       │
│                                                             │
│  2. Policy Scanning (4 AM UTC Daily)                        │
│     EventBridge Rule → qrie_policy_scanner                  │
│     ├─ Reads from qrie_resources table (fresh data)         │
│     ├─ Evaluates all active policies                        │
│     └─ Writes to qrie_findings table                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  REAL-TIME WORKFLOW (EventBridge from Customer Accounts)    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Customer CloudTrail Event → EventBridge → qrie_event_processor
│  ├─ Updates qrie_resources (incremental)                    │
│  └─ Triggers policy evaluation for affected resource        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Design Rationale

### Why Decoupled Schedules?

**✅ Advantages:**
1. **Resilient** - Inventory failures don't block scans (uses last good data)
2. **Predictable Costs** - Scheduled AWS API calls, not on-demand
3. **Fresh Baseline** - Daily full inventory catches drift
4. **Real-time Updates** - EventBridge handles incremental changes
5. **Simple Debugging** - Clear separation of concerns
6. **Idempotent** - Can re-run scans without re-running inventory

### Why NOT Other Approaches?

**❌ Scan kicks off inventory (sync):**
- Tight coupling - scan waits for slow inventory
- Timeout risk - 15min Lambda limit for both operations
- Expensive - AWS API calls on every scan

**❌ Scans do their own list/describes:**
- Duplicate API calls - waste of AWS API quota
- No inventory table - can't query resources independently
- Slower scans - waiting for AWS APIs every time

## Implementation

### Scheduled Rules

**Inventory Generation (Weekly, Saturday 12 AM UTC):**
```python
# In core_stack.py
WeeklyInventorySchedule = events.Rule(
    self, "WeeklyInventorySchedule",
    schedule=events.Schedule.cron(
        minute="0",
        hour="0",
        week_day="SAT"
    ),
    targets=[targets.LambdaFunction(inventory_generator_lambda)]
)
```

**Policy Scanning (Daily, 4 AM UTC):**
```python
# In core_stack.py
DailyPolicyScanSchedule = events.Rule(
    self, "DailyPolicyScanSchedule",
    schedule=events.Schedule.cron(
        minute="0",
        hour="4"
    ),
    targets=[targets.LambdaFunction(policy_scanner_lambda)]
)
```

## Data Flows - Inventory Generation, Policy Scanning, Event Processing

### Inventory Generation

**Triggers:**

**Manual:**
- **Customer Onboarding:**
  ```bash
  aws lambda invoke \
    --function-name qrie_inventory_generator \
    --payload '{"service": "all"}' \
    --region us-east-1 \
    --profile qop \
    response.json
  ```

- **New Service Onboarding:**
  ```bash
  aws lambda invoke \
    --function-name qrie_inventory_generator \
    --payload '{"service": "s3"}' \
    --region us-east-1 \
    --profile qop \
    response.json
  ```

**Automated:**
- Weekly, Saturday 12 AM UTC (anti-entropy scan)
- Implementation: Search "WeeklyInventorySchedule" in `core_stack.py`

**Data Flow:**
```
EventBridge Schedule (Weekly)
├─ Triggers qrie_inventory_generator Lambda
├─ For each customer account:
│  ├─ AssumeRole to customer account
│  ├─ Call AWS APIs:
│  │  ├─ S3: ListBuckets, GetBucketEncryption, GetBucketVersioning, etc.
│  │  ├─ EC2: DescribeInstances, DescribeSecurityGroups, etc.
│  │  ├─ IAM: ListUsers, ListAccessKeys, GetAccountPasswordPolicy, etc.
│  │  └─ Other services as configured
│  └─ Upsert to qrie_resources table:
│     ├─ PK: AccountService (e.g., "123456789012_s3")
│     ├─ SK: ARN
│     ├─ Configuration: Full resource config (JSON)
│     └─ LastSeenAt: Timestamp
└─ Complete (~30-45 min for typical deployment)
```

### Policy Scanning

**Triggers:**

**Manual:**
- **Customer Onboarding:** Happens automatically through daily scans, can be triggered manually:
  ```bash
  aws lambda invoke \
    --function-name qrie_policy_scanner \
    --payload '{}' \
    --region us-east-1 \
    --profile qop \
    response.json
  ```

- **New Policy Launch:** Automatically triggered by `POST /policies/launch` API
  ```bash
  # Via API (automatic)
  curl -X POST https://api-url/policies/launch \
    -H "Content-Type: application/json" \
    -d '{"policy_id": "S3BucketPublicReadProhibited", "scope": {"type": "all"}}'
  
  # Or manually trigger scan for specific policy
  aws lambda invoke \
    --function-name qrie_policy_scanner \
    --payload '{"policy_id": "S3BucketPublicReadProhibited"}' \
    --region us-east-1 \
    --profile qop \
    response.json
  ```

**Automated:**
- Daily, 4 AM UTC
- Implementation: Search "DailyPolicyScanSchedule" in `core_stack.py`

**Data Flow:**
```
EventBridge Schedule (Daily) OR Manual Trigger OR Policy Launch
├─ Triggers qrie_policy_scanner Lambda
├─ Reads active policies from qrie_policies table
├─ For each active policy:
│  ├─ Reads resources from qrie_resources table
│  ├─ Filters by policy scope (all/account/tags)
│  ├─ Evaluates policy against each resource:
│  │  ├─ Loads policy evaluation module
│  │  ├─ Runs evaluation logic
│  │  └─ Determines PASS/FAIL
│  └─ Writes/updates findings in qrie_findings table:
│     ├─ PK: ARN
│     ├─ SK: PolicyId
│     ├─ State: ACTIVE or RESOLVED
│     ├─ Severity: From policy or override
│     ├─ Evidence: JSON snippet of offending config
│     └─ Timestamps: FirstSeen, LastEvaluated
└─ Complete (~10-30 min depending on resource count)
```

### Event Processing (Real-Time)

**Triggers:** CloudTrail events from customer accounts forwarded via EventBridge

**Supported Events:**
- S3: CreateBucket, PutBucketEncryption, PutBucketVersioning, DeleteBucket, etc.
- EC2: RunInstances, TerminateInstances, ModifyInstanceAttribute, etc.
- IAM: CreateUser, DeleteUser, CreateAccessKey, UpdateAccountPasswordPolicy, etc.
- Other services as configured in customer EventBridge rules

**Data Flow:**
```
Customer Account Change (e.g., S3 bucket created)
├─ CloudTrail logs event
├─ EventBridge rule matches event pattern
├─ Forwards event to QOP account EventBridge
├─ QOP EventBridge routes to SQS queue (qrie_events_queue)
│  └─ Provides buffering and retry logic
├─ SQS triggers qrie_event_processor Lambda
├─ Event Processor Lambda:
│  ├─ Parses CloudTrail event
│  ├─ Extracts resource ARN and configuration
│  ├─ Updates qrie_resources table (incremental):
│  │  ├─ For CREATE/MODIFY: Upsert resource with new config
│  │  ├─ For DELETE: Mark resource as deleted or remove
│  │  └─ Update LastSeenAt timestamp
│  ├─ Identifies affected policies:
│  │  ├─ Queries qrie_policies for active policies
│  │  ├─ Filters by service and scope
│  │  └─ Gets list of policies to evaluate
│  └─ Triggers policy evaluation for affected resource:
│     ├─ For each applicable policy:
│     │  ├─ Loads policy evaluation module
│     │  ├─ Evaluates resource against policy
│     │  └─ Updates qrie_findings table:
│     │     ├─ Creates new finding if violation detected
│     │     ├─ Resolves existing finding if now compliant
│     │     └─ Updates LastEvaluated timestamp
│     └─ Returns evaluation results
└─ Complete (~1-5 seconds per event)
```

**Error Handling:**
- SQS Dead Letter Queue (DLQ) for failed events
- Automatic retries (3 attempts) before moving to DLQ
- CloudWatch alarms for DLQ depth
- Full stack traces logged for debugging
### Lambda Functions

**qrie_inventory_generator:**
- Handler: `inventory_generator.inventory_handler.lambda_handler`
- Timeout: 15 minutes
- Permissions: Read accounts, Write resources, AssumeRole to customer accounts
- Event format: `{"service": "all"}` or `{"service": "s3", "account_id": "123456789012"}`

**qrie_policy_scanner:**
- Handler: `scan_handler.scan_policy`
- Timeout: 15 minutes
- Permissions: Read accounts/resources/policies, Write findings
- Event format: `{}` (scans all) or `{"policy_id": "S3BucketPublicReadProhibited"}`

**qrie_event_processor:**
- Handler: `event_handler.lambda_handler`
- Triggered by: SQS queue (fed by customer EventBridge)
- Permissions: Write resources, Write findings


## Manual Operations

### Trigger Inventory Manually

```bash
aws lambda invoke \
  --function-name qrie_inventory_generator \
  --payload '{"service": "all"}' \
  --region us-east-1 \
  --profile qop \
  response.json
```

### Trigger Scan Manually

```bash
aws lambda invoke \
  --function-name qrie_policy_scanner \
  --payload '{}' \
  --region us-east-1 \
  --profile qop \
  response.json
```

### Scan Specific Policy

```bash
aws lambda invoke \
  --function-name qrie_policy_scanner \
  --payload '{"policy_id": "S3BucketPublicReadProhibited"}' \
  --region us-east-1 \
  --profile qop \
  response.json
```

### Scan Specific Service

```bash
aws lambda invoke \
  --function-name qrie_policy_scanner \
  --payload '{"service": "s3"}' \
  --region us-east-1 \
  --profile qop \
  response.json
```

## Monitoring

### CloudWatch Logs

```bash
# Monitor inventory generation
aws logs tail /aws/lambda/qrie_inventory_generator --follow --region us-east-1 --profile qop

# Monitor policy scanning
aws logs tail /aws/lambda/qrie_policy_scanner --follow --region us-east-1 --profile qop

# Monitor real-time events
aws logs tail /aws/lambda/qrie_event_processor --follow --region us-east-1 --profile qop
```

### Metrics to Watch

- **Inventory Duration** - Should complete in < 1 hour
- **Scan Duration** - Should complete in < 30 minutes
- **Error Rate** - Should be < 1%
- **Resources Scanned** - Should match expected inventory size
- **Findings Created/Closed** - Track policy compliance trends

## Troubleshooting

### Inventory Not Running

1. Check EventBridge rule is enabled:
   ```bash
   aws events describe-rule --name NightlyInventorySchedule --region us-east-1 --profile qop
   ```

2. Check Lambda permissions for AssumeRole

3. Check CloudWatch logs for errors

### Scans Not Finding Resources

1. Verify inventory ran successfully (check CloudWatch logs)
2. Query qrie_resources table to confirm data exists
3. Check scan is reading from correct account/service

### Stale Data

- Inventory runs nightly at 2 AM UTC
- Real-time updates via EventBridge should catch most changes
- Manual trigger available if needed

## Future Enhancements

- **Incremental Scans** - Only scan resources that changed since last scan
- **Parallel Execution** - Fan-out inventory/scans across multiple Lambdas
- **Smart Scheduling** - Adjust schedule based on change frequency
- **Cost Optimization** - Cache AWS API responses, use pagination efficiently
