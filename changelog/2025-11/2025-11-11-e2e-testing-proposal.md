# E2E Testing with Real AWS Resources - Proposal

**Date:** 2025-11-11  
**Status:** Proposal

## Summary

Current `--seed-data` populates DynamoDB tables with mock data for API/UI testing. This proposal adds `--seed-resources` commands to create **actual AWS resources** (compliant or non-compliant) in a test account, enabling end-to-end testing of:
- Event-driven policy evaluation (CloudTrail events)
- Inventory generation (bootstrap scans)
- Policy scanning (anti-entropy)
- Real-time drift detection
- Policy lifecycle (launch/update/delete)
- Scope changes and finding resolution

## Current State: Seed Data Analysis

### What `seed_data.py` Does ✅
- **Populates DynamoDB tables** with mock data:
  - `qrie_accounts`: 5 test accounts
  - `qrie_resources`: 750+ mock resources (S3, EC2, RDS, Lambda, DynamoDB)
  - `qrie_policies`: 6 launched policies
  - `qrie_findings`: 200+ historical findings
- **Does NOT create actual AWS resources**
- **Purpose**: API testing, UI pagination testing, dashboard testing

### What Seed Data Does NOT Do ❌
- Create real AWS resources
- Trigger CloudTrail events
- Test inventory generation from AWS APIs
- Test event-driven policy evaluation
- Test real-time drift detection

## Proposed Solution: Resource Seeding Commands

### Command Interface
```bash
# Create/update resources to be non-compliant (or create if doesn't exist)
./qop.py --seed-resources --non-compliant --account 050261919630 --region us-east-1 --profile qop

# Create/update resources to be compliant (or create if doesn't exist)
./qop.py --seed-resources --compliant --account 050261919630 --region us-east-1 --profile qop

# Remediate resources (make compliant, findings resolve automatically)
./qop.py --seed-resources --remediate --account 050261919630 --region us-east-1 --profile qop

# Cleanup/delete all test resources (findings purged)
./qop.py --seed-resources --cleanup --account 050261919630 --region us-east-1 --profile qop
```

### Naming Rationale
- `--seed-data`: Populates DynamoDB with mock data (accounts, resources, findings) - **end result**
- `--seed-resources`: Creates/modifies actual AWS resources - **input that triggers system**
- Flags: `--non-compliant`, `--compliant`, `--remediate`, `--cleanup` - clear intent

### What It Creates

#### 1. **S3 Resources** (4 policies)
```python
# S3BucketPublic (severity: 90)
- Bucket: qrie-test-public-bucket-{timestamp}
- Config: Block Public Access = ALL FALSE
- Expected: ACTIVE finding

# S3BucketVersioningDisabled (severity: 60)
- Bucket: qrie-test-no-versioning-{timestamp}
- Config: Versioning = Suspended
- Expected: ACTIVE finding

# S3BucketEncryptionDisabled (severity: 90)
- Bucket: qrie-test-no-encryption-{timestamp}
- Config: No default encryption
- Expected: ACTIVE finding

# S3BucketMfaDeleteDisabled (severity: 70)
- Bucket: qrie-test-no-mfa-delete-{timestamp}
- Config: Versioning enabled, MFA delete disabled
- Expected: ACTIVE finding
```

#### 2. **EC2 Resources** (1 policy)
```python
# EC2UnencryptedEBS (severity: 85)
- Instance: t3.micro with unencrypted EBS volume
- Config: EBS volume with Encrypted=false
- Expected: ACTIVE finding
- Note: Instance will be stopped immediately to minimize cost
```

#### 3. **IAM Resources** (5 policies)
```python
# IAMUserMfaDisabled (severity: 85)
- User: qrie-test-user-no-mfa-{timestamp}
- Config: Console access enabled, no MFA device
- Expected: ACTIVE finding

# IAMAccessKeyNotRotated (severity: 70)
- User: qrie-test-user-old-key-{timestamp}
- Config: Access key with LastRotated > 90 days (simulated via backdating)
- Expected: ACTIVE finding

# IAMAccessKeyUnused (severity: 60)
- User: qrie-test-user-unused-key-{timestamp}
- Config: Access key with LastUsed > 90 days
- Expected: ACTIVE finding

# IAMPolicyOverlyPermissive (severity: 80)
- Policy: qrie-test-wildcard-policy-{timestamp}
- Config: Policy with Action: "*", Resource: "*"
- User: qrie-test-user-wildcard-{timestamp} with policy attached
- Expected: ACTIVE finding

# IAMRootAccountActive (severity: 95)
- Cannot create (requires root credentials)
- Skip with warning message
```

#### 4. **RDS Resources** (1 policy)
```python
# RDSPublicAccess (severity: 90)
- Instance: qrie-test-public-db-{timestamp}
- Config: db.t3.micro, PubliclyAccessible=true
- Expected: ACTIVE finding
- Note: Will be deleted immediately after creation to minimize cost
```

### Resource Tagging
All resources tagged with:
```python
{
    'qrie-test': 'true',
    'qrie-test-run': '{timestamp}',
    'qrie-test-policy': '{policy_id}',
    'auto-cleanup': 'true'
}
```

### Comprehensive Test Flow

#### Prerequisites
1. **QOP account deployed** with QrieCore and QrieWeb stacks
2. **Test account onboarded** with EventBridge rules forwarding to QOP
3. **Account added to qrie_accounts table**
4. **All policies active with default scope** (empty scope = applies to all accounts)
5. **Caching disabled for testing** (set TTL=0 via environment variable)

#### Test Scenarios

##### Scenario 1: Non-Compliant Resources → Findings Created
```bash
# 1. Create non-compliant resources
./qop.py --seed-resources --non-compliant --account 050261919630 --region us-east-1 --profile qop

# Expected: Resources created with qrie-test tags
# Expected: CloudTrail events trigger policy evaluation within 1-2 minutes
# Expected: Findings appear in qrie_findings table

# 2. Verify findings via API
curl 'https://API-URL/findings?account=050261919630'

# 3. Verify findings via UI (hard refresh to bypass cache)
# Navigate to Findings page, verify evidence details

# 4. Verify inventory
./qop.py --generate-inventory --account-id 050261919630 --region us-east-1 --profile qop
# Expected: Resources appear in qrie_resources table with correct configurations
```

##### Scenario 2: Policy Deletion → Findings Purged
```bash
# 1. Delete a policy (e.g., S3BucketPublic)
curl -X DELETE 'https://API-URL/policies/S3BucketPublic'

# Expected: Policy status changed to deleted
# Expected: All S3BucketPublic findings marked as RESOLVED with reason POLICY_SUSPENDED

# 2. Verify findings gone
curl 'https://API-URL/findings?policy=S3BucketPublic&state=ACTIVE'
# Expected: Empty results
```

##### Scenario 3: Scope Change → Findings Excluded
```bash
# 1. Update policy scope to exclude test account
curl -X PUT 'https://API-URL/policies/S3BucketEncryptionDisabled' \
  -H 'Content-Type: application/json' \
  -d '{
    "scope": {
      "ExcludeAccounts": ["050261919630"]
    }
  }'

# Expected: Policy updated with new scope
# Expected: Findings for excluded account marked as RESOLVED with reason SCOPE_EXCLUDED

# 2. Verify findings gone
curl 'https://API-URL/findings?account=050261919630&policy=S3BucketEncryptionDisabled&state=ACTIVE'
# Expected: Empty results
```

##### Scenario 4: Scope Re-inclusion → Findings Return
```bash
# 1. Update policy scope to include test account again
curl -X PUT 'https://API-URL/policies/S3BucketEncryptionDisabled' \
  -H 'Content-Type: application/json' \
  -d '{
    "scope": {
      "ExcludeAccounts": []
    }
  }'

# Expected: Policy updated with new scope
# Expected: Anti-entropy scan (within 24 hours) re-evaluates resources
# Expected: Findings reappear if resources still non-compliant

# 2. Trigger immediate scan (don't wait 24 hours)
./qop.py --scan-account --account-id 050261919630 --scan-type anti-entropy --region us-east-1 --profile qop

# 3. Verify findings returned
curl 'https://API-URL/findings?account=050261919630&policy=S3BucketEncryptionDisabled&state=ACTIVE'
# Expected: Findings present again
```

##### Scenario 5: Remediation → Findings Resolved
```bash
# 1. Remediate resources (make compliant)
./qop.py --seed-resources --remediate --account 050261919630 --region us-east-1 --profile qop

# Expected: Resources updated to compliant configurations
# Expected: CloudTrail events trigger policy re-evaluation
# Expected: Findings marked as RESOLVED within 1-2 minutes

# 2. Verify findings resolved
curl 'https://API-URL/findings?account=050261919630&state=ACTIVE'
# Expected: Empty results (all findings resolved)

curl 'https://API-URL/findings?account=050261919630&state=RESOLVED'
# Expected: All previous findings now in RESOLVED state
```

##### Scenario 6: Compliant Resources → No Findings
```bash
# 1. Create compliant resources from scratch
./qop.py --seed-resources --compliant --account 050261919630 --region us-east-1 --profile qop

# Expected: Resources created with compliant configurations
# Expected: CloudTrail events trigger policy evaluation
# Expected: No findings created (all resources compliant)

# 2. Verify no findings
curl 'https://API-URL/findings?account=050261919630&state=ACTIVE'
# Expected: Empty results
```

##### Scenario 7: Make Compliant → Cleanup → Findings Purged
```bash
# 1. Make resources compliant first
./qop.py --seed-resources --compliant --account 050261919630 --region us-east-1 --profile qop

# 2. Wait for findings to resolve (1-2 minutes)

# 3. Delete all test resources
./qop.py --seed-resources --cleanup --account 050261919630 --region us-east-1 --profile qop

# Expected: All resources with qrie-test tags deleted
# Expected: Inventory updated (resources removed from qrie_resources)
# Expected: All findings purged from qrie_findings (both ACTIVE and RESOLVED)

# 4. Verify resources gone
curl 'https://API-URL/resources?account=050261919630'
# Expected: No qrie-test tagged resources

# 5. Verify findings purged
curl 'https://API-URL/findings?account=050261919630'
# Expected: Empty results
```

##### Scenario 8: Launch Available Policy → Scan Triggered
```bash
# 1. Ensure non-compliant resources exist
./qop.py --seed-resources --non-compliant --account 050261919630 --region us-east-1 --profile qop

# 2. List available policies
curl 'https://API-URL/policies?status=available'

# 3. Launch a new policy (e.g., S3BucketMfaDeleteDisabled)
curl -X POST 'https://API-URL/policies' \
  -H 'Content-Type: application/json' \
  -d '{
    "policy_id": "S3BucketMfaDeleteDisabled",
    "scope": {}
  }'

# Expected: Policy launched with default scope (all accounts)
# Expected: Automatic scan triggered for S3 resources
# Expected: Findings created for non-compliant S3 buckets within 1-2 minutes

# 4. Verify findings created
curl 'https://API-URL/findings?policy=S3BucketMfaDeleteDisabled&state=ACTIVE'
# Expected: Findings for S3 buckets without MFA delete
```

##### Scenario 9: Inventory Validation
```bash
# 1. Create resources
./qop.py --seed-resources --non-compliant --account 050261919630 --region us-east-1 --profile qop

# 2. Run inventory generation
./qop.py --generate-inventory --account-id 050261919630 --service s3 --region us-east-1 --profile qop

# 3. Verify inventory completeness
curl 'https://API-URL/resources?account=050261919630&service=s3'

# Expected inventory fields for each resource:
# - ARN: Correct format (arn:aws:s3:::qrie-test-*)
# - AccountService: {account}_s3
# - Configuration: Complete S3 bucket configuration
#   - PublicAccessBlockConfiguration (all 4 settings)
#   - Versioning (Status, MFADelete)
#   - Encryption (ServerSideEncryptionConfiguration)
#   - Tags (including qrie-test tags)
# - LastSeenAt: Recent timestamp
# - DescribeTime: Timestamp of describe call

# 4. Verify configuration accuracy
# Compare API response with actual AWS resource configuration
aws s3api get-bucket-versioning --bucket qrie-test-no-versioning-{timestamp} --profile test
# Expected: Matches Configuration.Versioning in inventory
```

##### Scenario 10: Event-Driven vs Scan-Based Evaluation
```bash
# 1. Create non-compliant resources (triggers events)
./qop.py --seed-resources --non-compliant --account 050261919630 --region us-east-1 --profile qop

# 2. Verify event-driven findings (within 1-2 minutes)
curl 'https://API-URL/findings?account=050261919630&state=ACTIVE'
# Expected: Findings created via event processing

# 3. Run bootstrap scan
./qop.py --scan-account --account-id 050261919630 --scan-type bootstrap --region us-east-1 --profile qop

# Expected: Scan re-evaluates all resources
# Expected: Findings remain (no duplicates created)
# Expected: LastEvaluated timestamp updated

# 4. Run anti-entropy scan (weekly)
./qop.py --scan-account --account-id 050261919630 --scan-type anti-entropy --region us-east-1 --profile qop

# Expected: Scan catches any drift not captured by events
# Expected: Findings consistent with event-driven evaluation
```

### Implementation Structure

```
tools/test/
├── seed_resources.py          # Main resource seeding script
├── resource_creators/
│   ├── __init__.py
│   ├── s3_creator.py          # S3 resource creation/modification
│   ├── ec2_creator.py         # EC2 resource creation/modification
│   ├── iam_creator.py         # IAM resource creation/modification
│   └── rds_creator.py         # RDS resource creation/modification
└── SEED_RESOURCES_GUIDE.md    # Comprehensive testing guide
```

### Key Implementation Details

#### 1. Account Registration
```python
def ensure_account_registered(account_id: str, region: str):
    """Ensure test account is in qrie_accounts table"""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    accounts_table = dynamodb.Table('qrie_accounts')
    
    # Upsert account
    accounts_table.put_item(Item={
        'AccountId': account_id,
        'AccountName': f'Test Account {account_id}',
        'Status': 'active',
        'OnboardedAt': datetime.now(timezone.utc).isoformat()
    })
```

#### 2. Default Scope for All Policies
```python
def ensure_policies_active_with_default_scope(region: str):
    """Ensure all policies are active with default (empty) scope"""
    from data_access.policy_manager import PolicyManager
    from policy_definition import ScopeConfig
    
    pm = PolicyManager()
    
    # Get all policy definitions
    policy_defs = pm.get_all_policy_definitions()
    
    for policy_def in policy_defs:
        # Check if already launched
        launched = pm.get_launched_policy(policy_def.policy_id)
        
        if not launched:
            # Launch with default scope (applies to all accounts)
            pm.launch_policy(
                policy_id=policy_def.policy_id,
                scope=ScopeConfig()  # Empty scope = all accounts
            )
            print(f"  ✅ Launched {policy_def.policy_id} with default scope")
        elif launched.status != 'active':
            # Update to active
            pm.update_launched_policy(policy_def.policy_id, status='active')
            print(f"  ✅ Activated {policy_def.policy_id}")
```

#### 3. Resource Upsert (Create or Update)
```python
def upsert_s3_bucket(bucket_name: str, compliant: bool, account_id: str):
    """Create or update S3 bucket to be compliant/non-compliant"""
    s3 = boto3.client('s3')
    
    try:
        # Check if bucket exists
        s3.head_bucket(Bucket=bucket_name)
        exists = True
    except:
        exists = False
    
    if not exists:
        # Create bucket
        s3.create_bucket(Bucket=bucket_name)
        print(f"  ✅ Created bucket: {bucket_name}")
    
    # Update configuration
    if compliant:
        # Enable all public access blocks
        s3.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }
        )
        # Enable versioning
        s3.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        # Enable encryption
        s3.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [{'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]
            }
        )
    else:
        # Disable all public access blocks
        s3.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        # Disable versioning
        s3.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Suspended'}
        )
        # Disable encryption (delete encryption configuration)
        try:
            s3.delete_bucket_encryption(Bucket=bucket_name)
        except:
            pass
    
    # Tag bucket
    s3.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={
            'TagSet': [
                {'Key': 'qrie-test', 'Value': 'true'},
                {'Key': 'qrie-test-account', 'Value': account_id},
                {'Key': 'qrie-test-timestamp', 'Value': datetime.now().isoformat()}
            ]
        }
    )
    
    print(f"  ✅ Updated {bucket_name} to be {'compliant' if compliant else 'non-compliant'}")
```

#### 4. Cleanup with Finding Purge
```python
def cleanup_resources_and_findings(account_id: str, region: str):
    """Delete all test resources and purge findings"""
    # 1. Delete AWS resources
    delete_test_resources(account_id, region)
    
    # 2. Purge findings from DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name=region)
    findings_table = dynamodb.Table('qrie_findings')
    
    # Scan for all findings for this account
    response = findings_table.scan(
        FilterExpression='begins_with(AccountService, :account)',
        ExpressionAttributeValues={':account': f'{account_id}_'}
    )
    
    # Delete findings
    with findings_table.batch_writer() as batch:
        for item in response['Items']:
            batch.delete_item(Key={
                'ARN': item['ARN'],
                'Policy': item['Policy']
            })
    
    print(f"  ✅ Purged {len(response['Items'])} findings for account {account_id}")
```

### Cost Considerations

**Estimated Cost per Test Run:**
- S3 buckets: $0.00 (empty buckets, deleted quickly)
- EC2 t3.micro (stopped): ~$0.01/hour storage
- RDS db.t3.micro (deleted immediately): ~$0.02
- IAM users/policies: $0.00
- **Total: < $0.05 per test run**

**Cost Mitigation:**
1. All resources tagged for easy identification
2. Cleanup script to remove all test resources
3. EC2 instances stopped immediately
4. RDS instances deleted immediately after creation
5. Optional: CloudWatch alarm if resources exist > 1 hour

### Integration with qop.py

```python
def seed_resources(self, account_id: str, mode: str):
    """Seed AWS resources for E2E testing
    
    Args:
        account_id: AWS account ID to seed resources in
        mode: One of 'non-compliant', 'compliant', 'remediate', 'cleanup'
    """
    mode_descriptions = {
        'non-compliant': "Create/update resources to be non-compliant",
        'compliant': "Create/update resources to be compliant",
        'remediate': "Update resources to be compliant (findings resolve)",
        'cleanup': "Delete all test resources and purge findings"
    }
    
    details = {
        "Operation": mode_descriptions[mode],
        "Target": f"AWS Account {account_id}",
        "Resources": "S3 buckets, EC2 instances, IAM users, RDS instances",
        "Cost": "~$0.05 per operation" if mode != 'cleanup' else "Free",
        "Prerequisites": "Account onboarded, policies active with default scope"
    }
    
    if mode == 'cleanup':
        details["Warning"] = "This will DELETE resources and PURGE findings"
    
    if not self._confirm_action(f"SEED RESOURCES ({mode.upper()})", details):
        return
    
    self._print_header(f"Seeding Resources ({mode})")
    
    # Run seed resources script
    seed_script = self.project_root / "tools" / "test" / "seed_resources.py"
    self._run_command([
        sys.executable, str(seed_script),
        f"--{mode}",
        "--account", account_id,
        "--region", self.region
    ])
    
    self._print_success(f"Resources seeded successfully ({mode})")

# In main() argument parsing:
commands.add_argument('--seed-resources', action='store_true', 
                     help='Seed AWS resources for E2E testing')

# Mode flags (mutually exclusive within seed-resources)
parser.add_argument('--non-compliant', action='store_true',
                   help='Create/update resources to be non-compliant')
parser.add_argument('--compliant', action='store_true',
                   help='Create/update resources to be compliant')
parser.add_argument('--remediate', action='store_true',
                   help='Remediate resources (make compliant)')
parser.add_argument('--cleanup', action='store_true',
                   help='Delete resources and purge findings')

# In execute command section:
elif args.seed_resources:
    # Determine mode
    if args.non_compliant:
        mode = 'non-compliant'
    elif args.compliant:
        mode = 'compliant'
    elif args.remediate:
        mode = 'remediate'
    elif args.cleanup:
        mode = 'cleanup'
    else:
        parser.error("--seed-resources requires one of: --non-compliant, --compliant, --remediate, --cleanup")
    
    orchestrator.seed_resources(account_id=args.account_id, mode=mode)
```

### Testing Workflow

```bash
# 1. Deploy infrastructure
./qop.py --deploy-core --region us-east-1 --profile qop

# 2. Create test resources
./qop.py --test-e2e --account 050261919630 --region us-east-1 --profile qop

# Output:
# ✅ Created S3 bucket: qrie-test-public-bucket-20251111-143022
# ✅ Created S3 bucket: qrie-test-no-versioning-20251111-143023
# ✅ Created EC2 instance: i-0123456789abcdef0 (stopped)
# ✅ Created IAM user: qrie-test-user-no-mfa-20251111-143024
# ✅ Created RDS instance: qrie-test-public-db-20251111-143025 (deleted)
#
# 📊 Expected Findings:
#   - S3BucketPublic: arn:aws:s3:::qrie-test-public-bucket-20251111-143022
#   - S3BucketVersioningDisabled: arn:aws:s3:::qrie-test-no-versioning-20251111-143023
#   - EC2UnencryptedEBS: arn:aws:ec2:us-east-1:050261919630:instance/i-0123456789abcdef0
#   - IAMUserMfaDisabled: arn:aws:iam::050261919630:user/qrie-test-user-no-mfa-20251111-143024
#
# ⏱️  Wait 1-2 minutes for CloudTrail events to trigger policy evaluation...

# 3. Verify event-driven evaluation
# Check UI or API for findings

# 4. Test inventory generation
./qop.py --generate-inventory --account 050261919630 --region us-east-1 --profile qop

# 5. Test policy scanning
./qop.py --scan-account --account 050261919630 --region us-east-1 --profile qop

# 6. Cleanup
./qop.py --test-e2e-cleanup --account 050261919630 --region us-east-1 --profile qop
```

## Benefits

### ✅ **Complete E2E Testing**
- Tests actual AWS API calls
- Tests CloudTrail event processing
- Tests inventory generation
- Tests policy evaluation with real configurations

### ✅ **Reproducible**
- Automated resource creation
- Consistent test scenarios
- Easy cleanup

### ✅ **Cost-Effective**
- < $0.05 per test run
- Resources deleted immediately
- No long-running resources

### ✅ **Safe**
- All resources tagged
- Isolated to test account
- Cleanup script included

### ✅ **Comprehensive Coverage**
- Tests 10 out of 11 implemented policies
- Covers S3, EC2, IAM, RDS services
- Tests both event-driven and scan-based evaluation

## Acceptance Criteria

- [ ] `--test-e2e` command creates non-compliant resources
- [ ] All resources tagged with `qrie-test=true`
- [ ] Resources created for 10/11 policies (skip IAMRootAccountActive)
- [ ] `--test-e2e-cleanup` deletes all test resources
- [ ] Cost < $0.05 per test run
- [ ] Documentation in `E2E_TESTING_GUIDE.md`
- [ ] Integration with qop.py orchestrator

## Future Enhancements

- [ ] Automated verification (check findings appear within timeout)
- [ ] Parallel resource creation for speed
- [ ] Support for multiple accounts
- [ ] CloudWatch alarm for orphaned resources
- [ ] Terraform/CDK for resource creation (more robust)
- [ ] Test resource remediation (fix non-compliant resources)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Orphaned resources | Tag all resources, cleanup script, CloudWatch alarm |
| Cost overruns | Stop/delete expensive resources immediately, cost estimate |
| Test account pollution | Unique timestamps, cleanup script |
| CloudTrail delay | Document expected delay (1-2 minutes) |
| Resource creation failures | Proper error handling, rollback on failure |

## Timeline

- **Phase 1** (2 hours): S3 resource creator
- **Phase 2** (2 hours): IAM resource creator
- **Phase 3** (1 hour): EC2 resource creator
- **Phase 4** (1 hour): RDS resource creator
- **Phase 5** (1 hour): Cleanup script
- **Phase 6** (1 hour): qop.py integration
- **Phase 7** (1 hour): Documentation

**Total: ~9 hours**
