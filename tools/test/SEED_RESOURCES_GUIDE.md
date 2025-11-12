# E2E Testing Guide - Seed Resources

**Date:** 2025-11-11  
**Status:** Active

## Overview

The `seed-resources` command creates **real AWS resources** in your test account to validate the complete qrie system end-to-end. Unlike `--seed-data` which populates DynamoDB with mock data, this creates actual S3 buckets, IAM users, and other resources that trigger CloudTrail events and generate real findings.

## Quick Start

```bash
# 1. Create non-compliant resources
./qop.py --seed-resources non-compliant --account-id 050261919630 --region us-east-1 --profile qop

# 2. Wait 2-3 minutes for CloudTrail events to process

# 3. Verify findings in UI or via API
curl "https://your-api-url/findings?account_id=050261919630"

# 4. Make resources compliant (test remediation)
./qop.py --seed-resources remediate --account-id 050261919630 --region us-east-1 --profile qop

# 5. Cleanup when done
./qop.py --seed-resources cleanup --account-id 050261919630 --region us-east-1 --profile qop
```

## Commands

### `--seed-resources non-compliant`
Creates non-compliant resources that violate active policies.

**What it does:**
- Registers account in `qrie_accounts` (if not already registered)
- Launches all 11 policies with default scope (if not already active)
- Creates S3 bucket without encryption, versioning, public access blocked
- Creates IAM user with weak password policy and old access key
- Tags all resources with `qrie-test=true`

**Expected findings:**
- S3BucketPublicReadProhibited
- S3BucketVersioningEnabled
- S3BucketEncryptionEnabled
- IAMPasswordPolicyCompliant
- IAMAccessKeyNotRotated
- IAMUserMFAEnabled

### `--seed-resources compliant`
Creates compliant resources that pass all policies.

**What it does:**
- Same setup as non-compliant
- Creates S3 bucket WITH encryption, versioning, public access blocked
- Creates IAM user with strong password policy, no access keys

**Expected findings:** None (all resources compliant)

### `--seed-resources remediate`
Makes existing resources compliant (tests remediation flow).

**What it does:**
- Updates S3 bucket configuration to be compliant
- Updates IAM password policy to be compliant
- Deletes IAM access keys

**Expected outcome:** Findings automatically resolve via CloudTrail events

### `--seed-resources cleanup`
Deletes all test resources and purges findings.

**What it does:**
- Deletes S3 buckets (empties first)
- Deletes IAM users and access keys
- **Purges ALL findings** for the account (ACTIVE + RESOLVED)
- Clean slate for next test run

## Test Scenarios

### Scenario 1: Non-Compliant → Findings Created
**Objective:** Verify event-driven finding creation

```bash
# Create non-compliant resources
./qop.py --seed-resources non-compliant --account-id 050261919630 --region us-east-1 --profile qop

# Wait 2-3 minutes for CloudTrail events

# Verify findings via API
curl "https://your-api-url/findings?account_id=050261919630" | jq '.findings | length'
# Expected: 6 findings

# Verify findings via UI
# Navigate to Findings page, filter by account
# Expected: 6 ACTIVE findings with evidence
```

### Scenario 2: Policy Deletion → Findings Purged
**Objective:** Verify findings are purged when policy is deleted

```bash
# Prerequisites: Scenario 1 completed (6 findings exist)

# Delete a policy via API
curl -X DELETE "https://your-api-url/policies/S3BucketEncryptionEnabled"

# Verify findings purged
curl "https://your-api-url/findings?policy_id=S3BucketEncryptionEnabled" | jq '.findings | length'
# Expected: 0 findings

# Re-launch policy
curl -X POST "https://your-api-url/policies/launch" \
  -H "Content-Type: application/json" \
  -d '{"policy_id": "S3BucketEncryptionEnabled", "scope": {}}'

# Wait 1-2 minutes for scan

# Verify findings return
curl "https://your-api-url/findings?policy_id=S3BucketEncryptionEnabled" | jq '.findings | length'
# Expected: 1 finding (S3 bucket)
```

### Scenario 3: Scope Exclusion → Findings Gone
**Objective:** Verify scope filtering works correctly

```bash
# Prerequisites: Scenario 1 completed (6 findings exist)

# Update policy to exclude test account
curl -X PUT "https://your-api-url/policies/S3BucketEncryptionEnabled" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": {
      "excluded_accounts": ["050261919630"]
    }
  }'

# Verify findings gone (filtered out by scope)
curl "https://your-api-url/findings?policy_id=S3BucketEncryptionEnabled&account_id=050261919630" | jq '.findings | length'
# Expected: 0 findings

# Update policy to re-include account
curl -X PUT "https://your-api-url/policies/S3BucketEncryptionEnabled" \
  -H "Content-Type: application/json" \
  -d '{"scope": {}}'

# Wait 1-2 minutes for re-scan

# Verify findings return
curl "https://your-api-url/findings?policy_id=S3BucketEncryptionEnabled&account_id=050261919630" | jq '.findings | length'
# Expected: 1 finding
```

### Scenario 4: Remediation → Findings Resolved
**Objective:** Verify findings resolve when resources become compliant

```bash
# Prerequisites: Scenario 1 completed (6 findings exist)

# Remediate resources
./qop.py --seed-resources remediate --account-id 050261919630 --region us-east-1 --profile qop

# Wait 2-3 minutes for CloudTrail events

# Verify findings resolved
curl "https://your-api-url/findings?account_id=050261919630&state=ACTIVE" | jq '.findings | length'
# Expected: 0 ACTIVE findings

curl "https://your-api-url/findings?account_id=050261919630&state=RESOLVED" | jq '.findings | length'
# Expected: 6 RESOLVED findings
```

### Scenario 5: Compliant Resources → No Findings
**Objective:** Verify compliant resources don't generate findings

```bash
# Cleanup first
./qop.py --seed-resources cleanup --account-id 050261919630 --region us-east-1 --profile qop

# Create compliant resources
./qop.py --seed-resources compliant --account-id 050261919630 --region us-east-1 --profile qop

# Wait 2-3 minutes

# Verify no findings
curl "https://your-api-url/findings?account_id=050261919630" | jq '.findings | length'
# Expected: 0 findings
```

### Scenario 6: Cleanup → Resources & Findings Purged
**Objective:** Verify cleanup removes everything

```bash
# Prerequisites: Any scenario completed

# Cleanup
./qop.py --seed-resources cleanup --account-id 050261919630 --region us-east-1 --profile qop

# Verify resources deleted (check AWS Console)
# - S3: qrie-test-bucket-050261919630 should not exist
# - IAM: qrie-test-user-050261919630 should not exist

# Verify findings purged
curl "https://your-api-url/findings?account_id=050261919630" | jq '.findings | length'
# Expected: 0 findings (both ACTIVE and RESOLVED purged)
```

### Scenario 7: Launch Available Policy → Scan Triggered
**Objective:** Verify launching a policy triggers a scan

```bash
# Prerequisites: Non-compliant resources exist, but policy not launched

# Delete policy first
curl -X DELETE "https://your-api-url/policies/S3BucketVersioningEnabled"

# Verify no findings for this policy
curl "https://your-api-url/findings?policy_id=S3BucketVersioningEnabled" | jq '.findings | length'
# Expected: 0

# Launch policy
curl -X POST "https://your-api-url/policies/launch" \
  -H "Content-Type: application/json" \
  -d '{"policy_id": "S3BucketVersioningEnabled", "scope": {}}'

# Wait 1-2 minutes for scan

# Verify findings created
curl "https://your-api-url/findings?policy_id=S3BucketVersioningEnabled" | jq '.findings | length'
# Expected: 1 finding (S3 bucket)
```

### Scenario 8: Inventory Validation
**Objective:** Verify inventory contains correct resource details

```bash
# Prerequisites: Resources created

# Check S3 inventory
curl "https://your-api-url/resources?service=s3&account_id=050261919630" | jq '.resources[0]'

# Expected fields:
# - ARN: arn:aws:s3:::qrie-test-bucket-050261919630
# - AccountService: 050261919630_s3
# - Configuration.Versioning: {Status: "Suspended"} or {Status: "Enabled"}
# - Configuration.Encryption: {...} or null
# - Configuration.PublicAccessBlock: {...}
# - LastSeenAt: recent timestamp

# Check IAM inventory
curl "https://your-api-url/resources?service=iam&account_id=050261919630" | jq '.resources[] | select(.ARN | contains("user"))'

# Expected fields:
# - ARN: arn:aws:iam::050261919630:user/qrie-test-user-050261919630
# - Configuration.AccessKeys: [{AccessKeyId, CreateDate, Status}]
# - Configuration.MFADevices: []
```

### Scenario 9: Event-Driven vs Scan-Based
**Objective:** Compare event-driven and scan-based evaluation

```bash
# Part A: Event-Driven (immediate)
./qop.py --seed-resources non-compliant --account-id 050261919630 --region us-east-1 --profile qop

# Check findings after 2-3 minutes
curl "https://your-api-url/findings?account_id=050261919630" | jq '.findings | length'
# Expected: 6 findings (created via CloudTrail events)

# Part B: Scan-Based (scheduled or manual)
# Trigger manual scan
curl -X POST "https://your-api-url/scan" \
  -H "Content-Type: application/json" \
  -d '{"account_id": "050261919630", "scan_type": "anti-entropy"}'

# Check findings after scan completes
curl "https://your-api-url/findings?account_id=050261919630" | jq '.findings | length'
# Expected: Same 6 findings (anti-entropy confirms consistency)
```

### Scenario 10: Dashboard Caching
**Objective:** Verify dashboard caching behavior

```bash
# Create non-compliant resources
./qop.py --seed-resources non-compliant --account-id 050261919630 --region us-east-1 --profile qop

# Wait 2-3 minutes

# Check dashboard (may be cached)
curl "https://your-api-url/summary/dashboard" | jq '.summary.total_findings'

# Hard refresh (bypass cache)
curl "https://your-api-url/summary/dashboard?refresh=true" | jq '.summary.total_findings'

# Expected: total_findings includes the 6 new findings
```

## Resources Created

### S3 Bucket
- **Name:** `qrie-test-bucket-{account_id}`
- **Tags:** `qrie-test=true`, `Purpose=E2E Testing`
- **Non-Compliant Config:**
  - Public access allowed
  - Versioning suspended
  - No encryption
- **Compliant Config:**
  - Public access blocked
  - Versioning enabled
  - AES256 encryption

### IAM User
- **Name:** `qrie-test-user-{account_id}`
- **Tags:** `qrie-test=true`, `Purpose=E2E Testing`
- **Non-Compliant Config:**
  - Weak password policy (min length 8, no requirements)
  - Access key created (appears as not rotated)
  - No MFA
- **Compliant Config:**
  - Strong password policy (min length 14, all requirements)
  - No access keys
  - No MFA (cannot be enabled programmatically)

### IAM Password Policy
- **Non-Compliant:**
  - MinimumPasswordLength: 8
  - RequireSymbols: False
  - RequireNumbers: False
  - RequireUppercase: False
  - RequireLowercase: False
- **Compliant:**
  - MinimumPasswordLength: 14
  - RequireSymbols: True
  - RequireNumbers: True
  - RequireUppercase: True
  - RequireLowercase: True
  - MaxPasswordAge: 90
  - PasswordReusePrevention: 24

## Cost Estimate

**Per test run:** < $0.05

- S3 bucket: $0.023/month (prorated)
- IAM user: Free
- IAM access key: Free
- CloudTrail events: Included in management events
- DynamoDB writes: ~$0.01

**Note:** Cleanup deletes all resources, so costs only accrue during testing.

## Prerequisites

1. **QrieCore stack deployed** in target region
2. **Account onboarded** (EventBridge rules configured)
3. **AWS credentials** configured for target account
4. **Policies available** (all 11 policies defined in code)

## Troubleshooting

### No findings after 3 minutes
- Check CloudTrail events are being forwarded to QOP account
- Verify EventBridge rules are active
- Check Lambda logs for event processing errors
- Manually trigger inventory scan: `./qop.py --generate-inventory --account-id 050261919630 --region us-east-1 --profile qop`

### Findings not resolving after remediation
- Wait longer (CloudTrail events can take 2-5 minutes)
- Check Lambda logs for event processing errors
- Manually trigger scan: `./qop.py --scan-account --account-id 050261919630 --region us-east-1 --profile qop`

### Cleanup fails
- Check AWS permissions (S3:DeleteBucket, IAM:DeleteUser, etc.)
- Manually delete resources via AWS Console
- Manually purge findings via DynamoDB Console

### Policy not launching
- Check policy definition exists in `/qrie-infra/lambda/policies/`
- Verify policy ID is correct (case-sensitive)
- Check Lambda logs for errors

## Best Practices

1. **Always cleanup after testing** to avoid costs
2. **Use dedicated test account** (not production)
3. **Tag resources** for easy identification
4. **Document test results** in changelog
5. **Run full test suite** before major releases
6. **Monitor costs** via AWS Cost Explorer
7. **Set TTL=0** for backend caching during E2E testing

## Integration with CI/CD

```bash
# Example GitHub Actions workflow
- name: E2E Test
  run: |
    ./qop.py --seed-resources non-compliant --account-id $TEST_ACCOUNT --region us-east-1 --profile qop
    sleep 180  # Wait for CloudTrail events
    ./tools/test/test_apis.py --verify-findings
    ./qop.py --seed-resources cleanup --account-id $TEST_ACCOUNT --region us-east-1 --profile qop
```

## Related Documentation

- [Seed Resources Proposal](/changelog/2025-11/2025-11-11-seed-resources-proposal.md)
- [Testing Inventory and Scanning](/tools/test/TESTING_INVENTORY_AND_SCANNING.md)
- [API Testing](/tools/test/test_apis.py)
- [Qrie Architecture](/changelog/documentation/qrie-architecture.md)
