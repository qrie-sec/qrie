# Real-Time Event Processing Implementation

**Date**: 2025-11-04  
**Status**: ✅ Implemented

## Overview
Implemented real-time CloudTrail event processing to enable drift detection and immediate policy evaluation when resources change in customer AWS accounts.

## Problem Statement
Previously, qrie only worked with scheduled scans (weekly inventory, daily policy scans). There was no real-time processing of CloudTrail events, meaning:
- Configuration changes weren't detected until the next scheduled scan
- Drift detection had significant lag (up to 24 hours for policy changes, 7 days for inventory)
- The `event_handler.py` had placeholder functions that raised `NotImplementedError`

## Solution
Implemented three critical functions in `event_handler.py`:
1. `_extract_arn_from_event()` - Extract resource ARN from CloudTrail events
2. `_extract_event_time()` - Extract event timestamp
3. `_describe_resource()` - Describe resource using AWS APIs (with S3 implementation)

## Implementation Details

### 1. ARN Extraction (`_extract_arn_from_event`)

**Strategy**: Two-method approach with fallback

**Method 1: Resources Array** (preferred)
```python
resources = detail.get('resources', [])
if resources and len(resources) > 0:
    arn = resources[0].get('ARN')
    if arn:
        return arn
```

**Method 2: Construct from Service-Specific Fields** (fallback)
```python
# S3 example
if event_source == 's3.amazonaws.com':
    bucket_name = request_params.get('bucketName')
    if bucket_name:
        return f"arn:aws:s3:::{bucket_name}"
```

**Key Observations from Real Events**:
- `CreateBucket` events have **empty** `resources[]` array
- `PutBucketVersioning`, `PutBucketPublicAccessBlock`, `DeleteBucket` have ARN in `resources[0].ARN`
- Fallback to `requestParameters.bucketName` handles CreateBucket case

**Supported Services**:
- ✅ S3 (fully implemented)
- 🚧 EC2 (TODO placeholder)
- 🚧 IAM (TODO placeholder)

### 2. Event Time Extraction (`_extract_event_time`)

**Source**: `detail.eventTime` from CloudTrail event

**Format**: ISO 8601 timestamp (e.g., `"2025-11-05T02:28:06Z"`)

**Implementation**:
```python
event_time_str = detail.get('eventTime')
event_time = datetime.datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
return int(event_time.timestamp() * 1000)  # Convert to milliseconds
```

**Result**: Millisecond timestamp for comparison with inventory `LastSeenAt`

### 3. Resource Description (`_describe_resource` + `_describe_s3_bucket`)

**Purpose**: Fetch current resource configuration using AWS APIs

**S3 Implementation**:
1. **Cross-Account Access**: Assumes `QrieInventoryRole` in customer account
2. **Configuration Fetched**:
   - Bucket name and ARN
   - Location (region)
   - **PublicAccessBlockConfiguration** (critical for S3BucketPublic policy)
   - Versioning status
   - Encryption configuration
   - Logging configuration

**Error Handling**:
- Graceful degradation: Missing configs don't fail the entire describe
- `NoSuchPublicAccessBlockConfiguration` → `PublicAccessBlockConfiguration: None` (indicates potentially public bucket)
- Other errors logged as debug, don't block evaluation

**Cross-Account Role**:
```python
role_arn = f"arn:aws:iam::{account_id}:role/QrieInventoryRole"
assumed_role = sts.assume_role(
    RoleArn=role_arn,
    RoleSessionName=f"qrie-event-processor-{account_id}"
)
```

## Event Flow

### **Complete Processing Flow**:

1. **EventBridge** forwards CloudTrail event to SQS queue
2. **Lambda** receives SQS message with event in `Records[].body`
3. **Parse** JSON body to get CloudTrail event structure
4. **Extract ARN** from `detail.resources[]` or construct from service fields
5. **Extract timestamp** from `detail.eventTime`
6. **Check staleness**: Compare event time with existing inventory `LastSeenAt`
7. **Describe resource**: Fetch current config via AWS API (with cross-account assume role)
8. **Compare configs**: Check if configuration actually changed
9. **Update inventory**: Store new config with describe timestamp
10. **Evaluate policies**: Run all active policies for the service
11. **Create/resolve findings**: Based on policy evaluation results

### **Staleness Check**:
```python
if existing_resource:
    existing_snapshot_time = existing_resource.get('LastSeenAt', '')
    if event_time <= existing_snapshot_time:
        debug(f"Skipping stale event - event time {event_time} <= existing snapshot {existing_snapshot_time}")
        continue
```

**Why**: Prevents processing old events that are already reflected in inventory (e.g., backfill from CloudTrail)

## Real Event Examples Analyzed

### **Event 1: CreateBucket**
```json
{
  "detail": {
    "eventName": "CreateBucket",
    "eventTime": "2025-11-05T02:28:06Z",
    "eventSource": "s3.amazonaws.com",
    "resources": [],  // EMPTY!
    "requestParameters": {
      "bucketName": "qrie-test-1762309684"
    }
  }
}
```
**Handling**: Fallback to `requestParameters.bucketName` to construct ARN

### **Event 2: PutBucketVersioning**
```json
{
  "detail": {
    "eventName": "PutBucketVersioning",
    "eventTime": "2025-11-05T02:29:55Z",
    "resources": [{
      "accountId": "050261919630",
      "type": "AWS::S3::Bucket",
      "ARN": "arn:aws:s3:::qrie-test-1762309684"
    }]
  }
}
```
**Handling**: Use `resources[0].ARN` directly

### **Event 3: PutBucketPublicAccessBlock**
```json
{
  "detail": {
    "eventName": "PutBucketPublicAccessBlock",
    "eventTime": "2025-11-05T02:30:03Z",
    "resources": [{
      "ARN": "arn:aws:s3:::qrie-test-1762309684"
    }],
    "requestParameters": {
      "PublicAccessBlockConfiguration": {
        "RestrictPublicBuckets": true,
        "BlockPublicPolicy": true,
        "BlockPublicAcls": true,
        "IgnorePublicAcls": true
      }
    }
  }
}
```
**Handling**: ARN from resources, triggers S3BucketPublic policy evaluation

### **Event 4: DeleteBucket**
```json
{
  "detail": {
    "eventName": "DeleteBucket",
    "eventTime": "2025-11-05T02:31:13Z",
    "resources": [{
      "ARN": "arn:aws:s3:::qrie-test-1762309684"
    }]
  }
}
```
**Handling**: ARN from resources, describe will fail (bucket deleted), error logged but not fatal

## Configuration Comparison

**Purpose**: Only process events that actually change configuration

**Implementation** (`_configs_differ`):
```python
def normalize(c):
    if not c:
        return {}
    # Remove timestamps and metadata that change on every describe
    filtered = {k: v for k, v in c.items() if k not in ['LastSeenAt', 'Metadata', 'LastModified']}
    return json.dumps(filtered, sort_keys=True, default=str)

return normalize(old_config) != normalize(new_config)
```

**Why**: Prevents unnecessary policy evaluations when only metadata changes (e.g., LastModified timestamp)

## Policy Evaluation Trigger

**When**: After inventory update, if config changed

**Process**:
```python
service_policies = policy_manager.get_active_policies_for_service(service)

for policy in service_policies:
    evaluator = policy_manager.create_policy_evaluator(policy.policy_id, policy)
    result = evaluator.evaluate(resource_arn, new_config, describe_time_ms)
```

**Result**: 
- New findings created for non-compliant resources
- Existing findings resolved if resource becomes compliant
- Findings include evidence from the new configuration

## Files Modified

### **`qrie-infra/lambda/event_processor/event_handler.py`**
- ✅ Implemented `_extract_arn_from_event()` (lines 91-142)
- ✅ Implemented `_extract_event_time()` (lines 145-173)
- ✅ Implemented `_describe_resource()` (lines 176-206)
- ✅ Implemented `_describe_s3_bucket()` (lines 209-291)
- ✅ Existing `_configs_differ()` already implemented (lines 294-306)

### **`qrie-infra/stacks/core_stack.py`**
- Updated Lambda handler paths to use module structure:
  - `scan_processor.scan_handler.scan_policy`
  - `event_processor.event_handler.process_event`
- Changed code asset path from subdirectory to `lambda/` root

## Testing

### **Manual Testing Steps**:

1. **Trigger S3 events** in monitored account:
```bash
BUCKET=qrie-test-$(date +%s)
aws s3 mb s3://$BUCKET --region us-east-1
aws s3api put-bucket-versioning --bucket $BUCKET --versioning-configuration Status=Enabled
aws s3api put-public-access-block --bucket $BUCKET \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

2. **Monitor event processor logs**:
```bash
./tools/debug/monitor-logs.sh event us-east-1 qop
```

3. **Verify processing**:
- Check logs for "Config changed for arn:aws:s3:::..." messages
- Check inventory table for updated bucket configuration
- Check findings table for S3BucketPublic policy evaluation results

4. **Check UI**:
- Navigate to Inventory page → filter by S3
- Verify bucket appears with correct configuration
- Navigate to Findings page → check for S3 findings

### **Expected Behavior**:

**CreateBucket Event**:
- ARN extracted from `requestParameters.bucketName`
- Bucket described (all configs fetched)
- Inventory updated
- S3BucketPublic policy evaluated (likely non-compliant if no public access block)

**PutBucketPublicAccessBlock Event**:
- ARN extracted from `resources[0].ARN`
- Bucket described (public access block config updated)
- Config comparison shows change
- S3BucketPublic policy re-evaluated (likely becomes compliant)
- Previous finding resolved

**DeleteBucket Event**:
- ARN extracted from `resources[0].ARN`
- Describe fails (bucket doesn't exist)
- Error logged but not fatal
- Inventory not updated (bucket already gone)

## Error Handling

### **Graceful Degradation**:
- Missing ARN → ValueError, event skipped, logged
- Missing timestamp → ValueError, event skipped, logged
- Describe failure → Exception raised, logged with stack trace, event fails
- Missing config fields → Logged as debug, evaluation continues with partial config
- Policy evaluation error → Logged with stack trace, other policies still evaluated

### **Fail-Fast Principle**:
- Top-level `process_event()` catches all exceptions, logs, and re-raises
- Lambda runtime handles retries (SQS message visibility timeout)
- Failed events return to queue for retry

## Performance Considerations

### **Cross-Account Assume Role**:
- **Cost**: STS AssumeRole call per event (~$0.00002 per call)
- **Latency**: ~100-200ms for assume role + describe calls
- **Optimization**: Could cache credentials per account (15min-1hr TTL)

### **Describe API Calls**:
- **S3**: 5-6 API calls per bucket (location, public access block, versioning, encryption, logging)
- **Cost**: Negligible (S3 API calls are free for most operations)
- **Latency**: ~50-100ms per API call, ~300-500ms total per bucket

### **Config Comparison**:
- **CPU**: JSON serialization + string comparison
- **Memory**: Negligible (configs are small, <10KB typically)
- **Optimization**: Already normalized to skip metadata fields

## Future Enhancements

### **EC2 Support**:
- Implement `_describe_ec2_instance()`
- Extract instance ID from CloudTrail event
- Fetch instance config (security groups, IAM role, public IP, etc.)
- Evaluate EC2 policies (public instances, unencrypted volumes, etc.)

### **IAM Support**:
- Implement `_describe_iam_user()` / `_describe_iam_role()`
- Extract user/role ARN from CloudTrail event
- Fetch IAM config (policies, MFA, access keys, etc.)
- Evaluate IAM policies (MFA, key rotation, overly permissive policies)

### **Credential Caching**:
- Cache assumed role credentials per account
- Reduce STS API calls (currently 1 per event)
- Use TTL-based cache (15 minutes)

### **Batch Processing**:
- Process multiple events from same account in batch
- Single assume role for multiple describes
- Reduce latency and API calls

### **DeleteBucket Handling**:
- Detect delete events and mark inventory as deleted
- Don't fail on describe errors for delete events
- Resolve all findings for deleted resources

## Impact

### **User Benefits**:
- **Real-time drift detection**: Changes detected within seconds, not hours/days
- **Immediate policy evaluation**: Security issues flagged as they happen
- **Accurate inventory**: Always reflects current state, not stale snapshots
- **Faster remediation**: Issues discovered and remediated immediately

### **Operational Benefits**:
- **Reduced scheduled scan load**: Only scan for baseline, not for every change
- **Lower costs**: Fewer full inventory scans needed
- **Better compliance**: Real-time enforcement of security policies
- **Audit trail**: Every change tracked with timestamp and evidence

## Deployment

### **Build and Deploy**:
```bash
cd qrie-infra
source .venv/bin/activate
cdk deploy QrieCore --region us-east-1 --profile qop
```

### **Verification**:
1. Check Lambda function updated: `qrie_event_processor`
2. Trigger test S3 events (see Testing section)
3. Monitor CloudWatch logs for event processing
4. Verify inventory and findings tables updated

### **Rollback**:
If issues occur, revert to previous version:
```bash
git revert <commit-hash>
cdk deploy QrieCore --region us-east-1 --profile qop
```

## Notes

- Real-time processing complements scheduled scans (doesn't replace them)
- Scheduled scans still needed for baseline and anti-entropy
- Event processing only updates resources that changed (efficient)
- S3 is first service implemented; EC2 and IAM coming next
- Cross-account role must exist in customer accounts (setup during onboarding)
