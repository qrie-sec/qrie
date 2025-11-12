# Testing Inventory Generation and Scanning

This guide provides comprehensive instructions for testing the inventory generation and policy scanning features in qrie.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Testing Inventory Generation](#testing-inventory-generation)
4. [Testing Policy Scanning](#testing-policy-scanning)
5. [End-to-End Testing](#end-to-end-testing)
6. [Monitoring and Debugging](#monitoring-and-debugging)
7. [Common Issues](#common-issues)

---

## Prerequisites

### Required Setup
1. **Deployed QOP Infrastructure**
   ```bash
   ./qop.py --info --region us-east-1 --profile qop
   ```
   Verify that QrieCore stack is deployed and shows:
   - API URL
   - Lambda functions (qrie_inventory_generator, qrie_policy_scanner)
   - DynamoDB tables (qrie_resources, qrie_findings, qrie_policies)

2. **Customer Accounts Onboarded**
   - At least one customer AWS account should be onboarded
   - EventBridge rules configured to forward CloudTrail events
   - Verify accounts are registered in the system

3. **AWS CLI Configured**
   ```bash
   aws sts get-caller-identity --profile qop --region us-east-1
   ```

### Environment Variables
```bash
export AWS_REGION=us-east-1
export AWS_PROFILE=qop
export API_URL=$(./qop.py --info --region us-east-1 --profile qop | grep "API URL" | awk '{print $3}')
```

---

## Architecture Overview

### Inventory Generation Flow
```
Customer AWS Account → EventBridge → QOP Account → Inventory Generator Lambda
                                                           ↓
                                                    qrie_resources table
```

### Scanning Flow
```
Policy Launch → Bootstrap Scan → Policy Scanner Lambda
                                        ↓
                                 Read: qrie_resources
                                 Write: qrie_findings
```

### Key Components
- **Inventory Generator Lambda** (`qrie_inventory_generator`): Scans customer accounts and populates resource inventory
- **Policy Scanner Lambda** (`qrie_policy_scanner`): Evaluates policies against inventory and creates findings
- **DynamoDB Tables**:
  - `qrie_resources`: Resource inventory (AccountService + ARN)
  - `qrie_findings`: Security findings (ARN + Policy)
  - `qrie_policies`: Launched policy configurations

---

## Testing Inventory Generation

### 1. Manual Inventory Generation (Bootstrap)

#### Generate Inventory for All Services and Accounts
```bash
aws lambda invoke \
  --function-name qrie_inventory_generator \
  --region us-east-1 \
  --profile qop \
  --payload '{"service": "all", "scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/inventory-all.json

cat /tmp/inventory-all.json | jq .
```

**Expected Output:**
```json
{
  "statusCode": 200,
  "body": {
    "message": "Inventory generation completed",
    "results": {
      "s3": [...],
      "ec2": [...],
      "iam": [...]
    },
    "scan_duration_ms": 5234,
    "total_resources": 127
  }
}
```

#### Generate Inventory for Specific Service
```bash
# S3 buckets only
aws lambda invoke \
  --function-name qrie_inventory_generator \
  --region us-east-1 \
  --profile qop \
  --payload '{"service": "s3", "scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/inventory-s3.json

# EC2 instances only
aws lambda invoke \
  --function-name qrie_inventory_generator \
  --region us-east-1 \
  --profile qop \
  --payload '{"service": "ec2", "scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/inventory-ec2.json

# IAM resources only
aws lambda invoke \
  --function-name qrie_inventory_generator \
  --region us-east-1 \
  --profile qop \
  --payload '{"service": "iam", "scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/inventory-iam.json
```

#### Generate Inventory for Specific Account
```bash
aws lambda invoke \
  --function-name qrie_inventory_generator \
  --region us-east-1 \
  --profile qop \
  --payload '{"service": "all", "account_id": "123456789012", "scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/inventory-account.json
```

### 2. Verify Inventory in DynamoDB

#### Check Total Resource Count
```bash
aws dynamodb scan \
  --table-name qrie_resources \
  --select COUNT \
  --region us-east-1 \
  --profile qop
```

#### Query Resources by Account and Service
```bash
# Get all S3 buckets for account 123456789012
aws dynamodb query \
  --table-name qrie_resources \
  --key-condition-expression "AccountService = :as" \
  --expression-attribute-values '{":as":{"S":"123456789012_s3"}}' \
  --region us-east-1 \
  --profile qop
```

#### Sample Resource Item
```bash
aws dynamodb get-item \
  --table-name qrie_resources \
  --key '{"AccountService":{"S":"123456789012_s3"},"ARN":{"S":"arn:aws:s3:::my-bucket"}}' \
  --region us-east-1 \
  --profile qop
```

**Expected Structure:**
```json
{
  "Item": {
    "AccountService": {"S": "123456789012_s3"},
    "ARN": {"S": "arn:aws:s3:::my-bucket"},
    "Configuration": {"M": {...}},
    "DescribeTime": {"N": "1699123456789"},
    "LastSeenAt": {"N": "1699123456789"}
  }
}
```

### 3. Verify Inventory via API

#### Get All Resources
```bash
curl -s "${API_URL}/resources" | jq .
```

#### Get Resources by Service
```bash
curl -s "${API_URL}/resources?service=s3" | jq .
curl -s "${API_URL}/resources?service=ec2" | jq .
curl -s "${API_URL}/resources?service=iam" | jq .
```

#### Get Resources by Account
```bash
curl -s "${API_URL}/resources?account_id=123456789012" | jq .
```

#### Get Resources Summary
```bash
curl -s "${API_URL}/summary/resources" | jq .
```

**Expected Output:**
```json
{
  "total_resources": 127,
  "total_accounts": 3,
  "total_findings": 45,
  "critical_findings": 5,
  "high_findings": 12,
  "resource_types": [
    {
      "resource_type": "s3",
      "all_resources": 45,
      "non_compliant": 12
    },
    {
      "resource_type": "ec2",
      "all_resources": 67,
      "non_compliant": 23
    },
    {
      "resource_type": "iam",
      "all_resources": 15,
      "non_compliant": 10
    }
  ]
}
```

### 4. Test Anti-Entropy Scans

Anti-entropy scans run on a schedule to detect drift. Test manually:

```bash
aws lambda invoke \
  --function-name qrie_inventory_generator \
  --region us-east-1 \
  --profile qop \
  --payload '{"service": "all", "scan_type": "anti-entropy"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/inventory-anti-entropy.json
```

**Verify Metrics Saved:**
```bash
aws dynamodb get-item \
  --table-name qrie_summary \
  --key '{"Type":{"S":"last_inventory_scan"}}' \
  --region us-east-1 \
  --profile qop
```

**Expected Metrics:**
```json
{
  "Item": {
    "Type": {"S": "last_inventory_scan"},
    "timestamp_ms": {"N": "1699123456789"},
    "duration_ms": {"N": "5234"},
    "service": {"S": "all"},
    "account_id": {"S": "all"},
    "resources_found": {"N": "127"},
    "scan_type": {"S": "anti-entropy"}
  }
}
```

---

## Testing Policy Scanning

### 1. Launch a Policy

#### List Available Policies
```bash
curl -s "${API_URL}/policies/available" | jq .
```

#### Launch a Policy via API
```bash
curl -X POST "${API_URL}/policies/launch" \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "S3BucketPublicReadProhibited",
    "scope": {
      "include_accounts": [],
      "exclude_accounts": [],
      "include_tags": {},
      "exclude_tags": {},
      "include_ou_paths": [],
      "exclude_ou_paths": []
    },
    "severity": 90,
    "remediation": "Update bucket policy to remove public read access"
  }' | jq .
```

**Expected Response:**
```json
{
  "message": "Policy S3BucketPublicReadProhibited launched successfully",
  "bootstrap_scan_triggered": true
}
```

**What Happens:**
1. Policy is saved to `qrie_policies` table with status `active`
2. Bootstrap scan is automatically triggered for this policy
3. Scanner evaluates all S3 resources against the policy
4. Findings are created in `qrie_findings` table

### 2. Manual Policy Scan

#### Scan All Active Policies
```bash
aws lambda invoke \
  --function-name qrie_policy_scanner \
  --region us-east-1 \
  --profile qop \
  --payload '{"scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/scan-all.json

cat /tmp/scan-all.json | jq .
```

**Expected Output:**
```json
{
  "statusCode": 200,
  "body": {
    "processed_resources": 127,
    "skipped_resources": 0,
    "findings_created": 45,
    "findings_closed": 82,
    "policies_evaluated": 5,
    "accounts_processed": 3,
    "scan_duration_ms": 3456
  }
}
```

#### Scan Specific Policy
```bash
aws lambda invoke \
  --function-name qrie_policy_scanner \
  --region us-east-1 \
  --profile qop \
  --payload '{"policy_id": "S3BucketPublicReadProhibited", "scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/scan-policy.json
```

#### Scan Specific Service
```bash
aws lambda invoke \
  --function-name qrie_policy_scanner \
  --region us-east-1 \
  --profile qop \
  --payload '{"service": "s3", "scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/scan-service.json
```

### 3. Verify Findings in DynamoDB

#### Check Total Findings Count
```bash
aws dynamodb scan \
  --table-name qrie_findings \
  --select COUNT \
  --region us-east-1 \
  --profile qop
```

#### Query Findings by Account and Service
```bash
aws dynamodb query \
  --table-name qrie_findings \
  --index-name AccountService-index \
  --key-condition-expression "AccountService = :as" \
  --expression-attribute-values '{":as":{"S":"123456789012_s3"}}' \
  --region us-east-1 \
  --profile qop
```

#### Get Specific Finding
```bash
aws dynamodb get-item \
  --table-name qrie_findings \
  --key '{"ARN":{"S":"arn:aws:s3:::my-bucket"},"Policy":{"S":"S3BucketPublicReadProhibited"}}' \
  --region us-east-1 \
  --profile qop
```

**Expected Structure:**
```json
{
  "Item": {
    "ARN": {"S": "arn:aws:s3:::my-bucket"},
    "Policy": {"S": "S3BucketPublicReadProhibited"},
    "AccountService": {"S": "123456789012_s3"},
    "Severity": {"N": "90"},
    "State": {"S": "ACTIVE"},
    "FirstSeen": {"N": "1699123456789"},
    "LastEvaluated": {"N": "1699123456789"},
    "Evidence": {"S": "{\"PublicAccessBlockConfiguration\": {...}}"}
  }
}
```

### 4. Verify Findings via API

#### Get All Findings
```bash
curl -s "${API_URL}/findings" | jq .
```

#### Get Findings by State
```bash
curl -s "${API_URL}/findings?state=ACTIVE" | jq .
curl -s "${API_URL}/findings?state=RESOLVED" | jq .
```

#### Get Findings by Severity
```bash
curl -s "${API_URL}/findings?min_severity=80" | jq .
```

#### Get Findings by Policy
```bash
curl -s "${API_URL}/findings?policy=S3BucketPublicReadProhibited" | jq .
```

#### Get Findings Summary
```bash
curl -s "${API_URL}/summary/findings" | jq .
```

**Expected Output:**
```json
{
  "total_findings": 45,
  "critical_findings": 5,
  "high_findings": 12,
  "medium_findings": 18,
  "low_findings": 10,
  "policies": [
    {
      "policy": "S3BucketPublicReadProhibited",
      "open_findings": 12,
      "max_severity": 90
    },
    {
      "policy": "IAMAccessKeyNotRotated",
      "open_findings": 8,
      "max_severity": 70
    }
  ]
}
```

### 5. Test Policy Updates

#### Suspend a Policy
```bash
curl -X PUT "${API_URL}/policies/update" \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "S3BucketPublicReadProhibited",
    "status": "suspended"
  }' | jq .
```

**Expected Response:**
```json
{
  "message": "Policy S3BucketPublicReadProhibited updated successfully",
  "findings_purged": 12
}
```

**Verify Findings Purged:**
```bash
curl -s "${API_URL}/findings?policy=S3BucketPublicReadProhibited" | jq '.findings | length'
# Should return 0
```

#### Reactivate Policy
```bash
curl -X PUT "${API_URL}/policies/update" \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "S3BucketPublicReadProhibited",
    "status": "active"
  }' | jq .
```

**Then trigger a scan to regenerate findings:**
```bash
aws lambda invoke \
  --function-name qrie_policy_scanner \
  --region us-east-1 \
  --profile qop \
  --payload '{"policy_id": "S3BucketPublicReadProhibited", "scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/scan-reactivated.json
```

---

## End-to-End Testing

### Complete Workflow Test

```bash
#!/bin/bash
# test-e2e-inventory-scanning.sh

set -e

REGION="us-east-1"
PROFILE="qop"
API_URL=$(./qop.py --info --region $REGION --profile $PROFILE | grep "API URL" | awk '{print $3}')

echo "=== Step 1: Generate Inventory ==="
aws lambda invoke \
  --function-name qrie_inventory_generator \
  --region $REGION \
  --profile $PROFILE \
  --payload '{"service": "all", "scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/e2e-inventory.json

RESOURCES=$(cat /tmp/e2e-inventory.json | jq -r '.body' | jq -r '.total_resources')
echo "✅ Generated inventory: $RESOURCES resources"

echo ""
echo "=== Step 2: Verify Inventory via API ==="
RESOURCES_API=$(curl -s "${API_URL}/summary/resources" | jq -r '.total_resources')
echo "✅ API reports: $RESOURCES_API resources"

echo ""
echo "=== Step 3: Launch a Policy ==="
curl -X POST "${API_URL}/policies/launch" \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "S3BucketPublicReadProhibited",
    "scope": {"include_accounts": [], "exclude_accounts": [], "include_tags": {}, "exclude_tags": {}, "include_ou_paths": [], "exclude_ou_paths": []},
    "severity": 90
  }' > /tmp/e2e-launch.json

echo "✅ Policy launched"

echo ""
echo "=== Step 4: Wait for Bootstrap Scan ==="
sleep 5

echo ""
echo "=== Step 5: Verify Findings ==="
FINDINGS=$(curl -s "${API_URL}/findings?policy=S3BucketPublicReadProhibited" | jq -r '.count')
echo "✅ Found $FINDINGS findings for policy"

echo ""
echo "=== Step 6: Suspend Policy ==="
curl -X PUT "${API_URL}/policies/update" \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "S3BucketPublicReadProhibited",
    "status": "suspended"
  }' > /tmp/e2e-suspend.json

PURGED=$(cat /tmp/e2e-suspend.json | jq -r '.findings_purged')
echo "✅ Policy suspended, purged $PURGED findings"

echo ""
echo "=== Step 7: Verify Findings Purged ==="
FINDINGS_AFTER=$(curl -s "${API_URL}/findings?policy=S3BucketPublicReadProhibited" | jq -r '.count')
echo "✅ Findings after suspension: $FINDINGS_AFTER (should be 0)"

echo ""
echo "=== E2E Test Complete ==="
```

**Run the test:**
```bash
chmod +x test-e2e-inventory-scanning.sh
./test-e2e-inventory-scanning.sh
```

---

## Monitoring and Debugging

### 1. Monitor Lambda Logs

#### Real-time Log Monitoring with Color Coding
```bash
# Monitor inventory generator
./tools/debug/monitor-lambda-logs.sh us-east-1 qop | grep inventory_generator

# Monitor policy scanner
./tools/debug/monitor-lambda-logs.sh us-east-1 qop | grep policy_scanner
```

#### View Recent Logs
```bash
# Inventory generator logs
aws logs tail /aws/lambda/qrie_inventory_generator \
  --follow \
  --region us-east-1 \
  --profile qop

# Policy scanner logs
aws logs tail /aws/lambda/qrie_policy_scanner \
  --follow \
  --region us-east-1 \
  --profile qop
```

### 2. Search Logs by Request ID

```bash
# Find all operations for a specific request
aws logs filter-log-events \
  --log-group-name /aws/lambda/qrie_policy_scanner \
  --filter-pattern "[abc123-def456]" \
  --region us-east-1 \
  --profile qop
```

### 3. Check Scan Metrics

#### Last Inventory Scan
```bash
aws dynamodb get-item \
  --table-name qrie_summary \
  --key '{"Type":{"S":"last_inventory_scan"}}' \
  --region us-east-1 \
  --profile qop | jq '.Item'
```

#### Last Policy Scan
```bash
aws dynamodb get-item \
  --table-name qrie_summary \
  --key '{"Type":{"S":"last_policy_scan"}}' \
  --region us-east-1 \
  --profile qop | jq '.Item'
```

### 4. Debug Specific Resource

```bash
# Get resource from inventory
RESOURCE_ARN="arn:aws:s3:::my-bucket"
ACCOUNT_SERVICE="123456789012_s3"

aws dynamodb get-item \
  --table-name qrie_resources \
  --key "{\"AccountService\":{\"S\":\"$ACCOUNT_SERVICE\"},\"ARN\":{\"S\":\"$RESOURCE_ARN\"}}" \
  --region us-east-1 \
  --profile qop

# Get all findings for this resource
aws dynamodb query \
  --table-name qrie_findings \
  --key-condition-expression "ARN = :arn" \
  --expression-attribute-values "{\":arn\":{\"S\":\"$RESOURCE_ARN\"}}" \
  --region us-east-1 \
  --profile qop
```

---

## Common Issues

### Issue 1: No Resources Found

**Symptoms:**
- Inventory scan completes but `total_resources: 0`
- API returns empty resource list

**Debugging:**
```bash
# Check if customer accounts are registered
curl -s "${API_URL}/accounts" | jq .

# Check Lambda execution role permissions
aws iam get-role-policy \
  --role-name qrie_inventory_generator_role \
  --policy-name AssumeCustomerAccountRole \
  --region us-east-1 \
  --profile qop

# Check CloudWatch logs for errors
aws logs tail /aws/lambda/qrie_inventory_generator \
  --since 10m \
  --region us-east-1 \
  --profile qop
```

**Common Causes:**
- Customer accounts not onboarded
- Missing cross-account IAM role
- Insufficient permissions on cross-account role

### Issue 2: Findings Not Created

**Symptoms:**
- Policy scan completes but no findings created
- `findings_created: 0` in scan results

**Debugging:**
```bash
# Verify policy is active
curl -s "${API_URL}/policies/active" | jq '.[] | select(.policy_id=="S3BucketPublicReadProhibited")'

# Check if resources exist for the policy's service
curl -s "${API_URL}/resources?service=s3" | jq '.count'

# Check scanner logs for evaluation errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/qrie_policy_scanner \
  --filter-pattern "Error evaluating" \
  --region us-east-1 \
  --profile qop
```

**Common Causes:**
- No resources in inventory for policy's service
- Policy evaluation logic error
- Scoping rules excluding all resources

### Issue 3: Stale Inventory Data

**Symptoms:**
- Resources deleted in AWS still appear in inventory
- New resources not showing up

**Debugging:**
```bash
# Check last inventory scan time
aws dynamodb get-item \
  --table-name qrie_summary \
  --key '{"Type":{"S":"last_inventory_scan"}}' \
  --region us-east-1 \
  --profile qop | jq -r '.Item.timestamp_ms.N'

# Trigger manual inventory refresh
aws lambda invoke \
  --function-name qrie_inventory_generator \
  --region us-east-1 \
  --profile qop \
  --payload '{"service": "all", "scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/refresh.json
```

**Common Causes:**
- Anti-entropy scans not scheduled
- EventBridge rules not forwarding events
- Lambda timeout during large scans

### Issue 4: Bootstrap Scan Not Triggered

**Symptoms:**
- Policy launched successfully but no findings appear
- No scan logs after policy launch

**Debugging:**
```bash
# Check if bootstrap scan was triggered
aws logs filter-log-events \
  --log-group-name /aws/lambda/qrie_policy_scanner \
  --filter-pattern "Bootstrap scan triggered" \
  --start-time $(date -u -d '5 minutes ago' +%s)000 \
  --region us-east-1 \
  --profile qop

# Manually trigger scan
aws lambda invoke \
  --function-name qrie_policy_scanner \
  --region us-east-1 \
  --profile qop \
  --payload '{"policy_id": "S3BucketPublicReadProhibited", "scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/manual-scan.json
```

**Common Causes:**
- Lambda invocation failed (check IAM permissions)
- Scanner lambda not deployed
- Async invocation error (check dead letter queue)

---

## Performance Testing

### Load Test: Large Inventory Scan

```bash
# Generate inventory for 1000+ resources
time aws lambda invoke \
  --function-name qrie_inventory_generator \
  --region us-east-1 \
  --profile qop \
  --payload '{"service": "all", "scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/load-test.json

# Check duration
cat /tmp/load-test.json | jq -r '.body' | jq '.scan_duration_ms'
```

### Load Test: Multiple Policy Scan

```bash
# Launch 10 policies
for policy in S3BucketPublicReadProhibited IAMAccessKeyNotRotated EC2PublicIPProhibited; do
  curl -X POST "${API_URL}/policies/launch" \
    -H "Content-Type: application/json" \
    -d "{\"policy_id\": \"$policy\", \"scope\": {}}"
  sleep 2
done

# Scan all policies
time aws lambda invoke \
  --function-name qrie_policy_scanner \
  --region us-east-1 \
  --profile qop \
  --payload '{"scan_type": "bootstrap"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/multi-policy-scan.json
```

---

## Automated Test Suite

Create a comprehensive test script:

```bash
#!/bin/bash
# tools/test/test-inventory-scanning.sh

source tools/test/test-helpers.sh

test_inventory_generation() {
  echo "Testing inventory generation..."
  
  # Test all services
  invoke_lambda qrie_inventory_generator '{"service": "all", "scan_type": "bootstrap"}' /tmp/test-inv-all.json
  assert_success /tmp/test-inv-all.json
  
  # Test specific service
  invoke_lambda qrie_inventory_generator '{"service": "s3", "scan_type": "bootstrap"}' /tmp/test-inv-s3.json
  assert_success /tmp/test-inv-s3.json
  
  echo "✅ Inventory generation tests passed"
}

test_policy_scanning() {
  echo "Testing policy scanning..."
  
  # Launch test policy
  api_post "/policies/launch" '{"policy_id": "TestPolicy", "scope": {}}' /tmp/test-launch.json
  assert_success /tmp/test-launch.json
  
  # Verify scan triggered
  sleep 5
  api_get "/findings?policy=TestPolicy" /tmp/test-findings.json
  assert_not_empty /tmp/test-findings.json
  
  echo "✅ Policy scanning tests passed"
}

# Run all tests
test_inventory_generation
test_policy_scanning
```

---

## Summary

This testing guide covers:
- ✅ Manual inventory generation (bootstrap and anti-entropy)
- ✅ Inventory verification (DynamoDB and API)
- ✅ Policy launching and scanning
- ✅ Finding verification and lifecycle
- ✅ End-to-end workflow testing
- ✅ Monitoring and debugging techniques
- ✅ Common issues and troubleshooting
- ✅ Performance testing

For additional help:
- Check `qrie-infra/README.md` for architecture details
- Review `qrie-infra/qrie_apis.md` for API documentation
- Use `./qop.py --info` for deployment information
- Monitor logs with `./tools/debug/monitor-lambda-logs.sh`
