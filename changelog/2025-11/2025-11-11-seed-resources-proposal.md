# E2E Testing with Real AWS Resources - Revised Proposal

**Date:** 2025-11-11  
**Status:** Proposal (Revised)

## Summary

Current `--seed-data` populates DynamoDB tables with mock data for API/UI testing. This proposal adds `--seed-resources` commands to create **actual AWS resources** (compliant or non-compliant) in a test account, enabling comprehensive end-to-end testing.

## Command Interface

```bash
# Create/update resources to be non-compliant
./qop.py --seed-resources --non-compliant --account-id 050261919630 --region us-east-1 --profile qop

# Create/update resources to be compliant  
./qop.py --seed-resources --compliant --account-id 050261919630 --region us-east-1 --profile qop

# Remediate resources (make compliant, findings resolve automatically)
./qop.py --seed-resources --remediate --account-id 050261919630 --region us-east-1 --profile qop

# Cleanup/delete all test resources (findings purged)
./qop.py --seed-resources --cleanup --account-id 050261919630 --region us-east-1 --profile qop
```

### Naming Rationale
- `--seed-data`: Populates DynamoDB with mock data - **end result** (findings)
- `--seed-resources`: Creates/modifies actual AWS resources - **input** that triggers system
- Flags: `--non-compliant`, `--compliant`, `--remediate`, `--cleanup` - clear intent

## Key Requirements

### 1. Account Registration ✅
- Automatically add account to `qrie_accounts` table if not present
- Set status='active', include timestamp

### 2. Policy Activation with Default Scope ✅
- Ensure ALL 11 policies are active
- Use default (empty) scope = applies to all accounts
- Launch any policies not yet launched

### 3. Cleanup with Finding Purge ✅
- Delete all AWS resources tagged with `qrie-test=true`
- **Purge all findings** from `qrie_findings` table (both ACTIVE and RESOLVED)
- Remove resources from `qrie_resources` inventory

### 4. Remediation Support ✅
- `--remediate` makes resources compliant
- CloudTrail events trigger re-evaluation
- Findings automatically resolve (State=RESOLVED)

### 5. Manual Verification Scenarios ✅
- Launch available policy → verify scan triggered
- Update scope → verify findings excluded/included
- Delete policy → verify findings purged

## Comprehensive Test Scenarios

### Prerequisites
1. QOP account deployed (QrieCore + QrieWeb)
2. Test account onboarded with EventBridge rules
3. Account added to qrie_accounts (automatic)
4. All policies active with default scope (automatic)
5. Caching disabled for testing (TTL=0 environment variable)

### Scenario 1: Non-Compliant → Findings Created
```bash
./qop.py --seed-resources --non-compliant --account-id 050261919630 --region us-east-1 --profile qop
# Wait 1-2 minutes for CloudTrail events
curl 'https://API-URL/findings?account=050261919630&state=ACTIVE'
# Expected: Findings for all non-compliant resources
```

### Scenario 2: Policy Deletion → Findings Purged
```bash
curl -X DELETE 'https://API-URL/policies/S3BucketPublic'
# Expected: All S3BucketPublic findings → RESOLVED (reason: POLICY_SUSPENDED)
```

### Scenario 3: Scope Exclusion → Findings Gone
```bash
curl -X PUT 'https://API-URL/policies/S3BucketEncryptionDisabled' \
  -d '{"scope": {"ExcludeAccounts": ["050261919630"]}}'
# Expected: Findings for account 050261919630 → RESOLVED (reason: SCOPE_EXCLUDED)
```

### Scenario 4: Scope Re-inclusion → Findings Return
```bash
curl -X PUT 'https://API-URL/policies/S3BucketEncryptionDisabled' \
  -d '{"scope": {"ExcludeAccounts": []}}'
./qop.py --scan-account --account-id 050261919630 --scan-type anti-entropy --region us-east-1
# Expected: Findings reappear (resources still non-compliant)
```

### Scenario 5: Remediation → Findings Resolved
```bash
./qop.py --seed-resources --remediate --account-id 050261919630 --region us-east-1 --profile qop
# Wait 1-2 minutes
curl 'https://API-URL/findings?account=050261919630&state=ACTIVE'
# Expected: Empty (all findings resolved)
```

### Scenario 6: Compliant Resources → No Findings
```bash
./qop.py --seed-resources --compliant --account-id 050261919630 --region us-east-1 --profile qop
curl 'https://API-URL/findings?account=050261919630&state=ACTIVE'
# Expected: Empty (no findings created)
```

### Scenario 7: Cleanup → Resources & Findings Purged
```bash
./qop.py --seed-resources --cleanup --account-id 050261919630 --region us-east-1 --profile qop
curl 'https://API-URL/resources?account=050261919630'
curl 'https://API-URL/findings?account=050261919630'
# Expected: Both empty
```

### Scenario 8: Launch Policy → Scan Triggered
```bash
./qop.py --seed-resources --non-compliant --account-id 050261919630 --region us-east-1 --profile qop
curl -X POST 'https://API-URL/policies' -d '{"policy_id": "S3BucketMfaDeleteDisabled", "scope": {}}'
# Expected: Automatic scan, findings created within 1-2 minutes
```

### Scenario 9: Inventory Validation
```bash
./qop.py --generate-inventory --account-id 050261919630 --service s3 --region us-east-1 --profile qop
curl 'https://API-URL/resources?account=050261919630&service=s3'
# Verify: ARN, AccountService, Configuration (complete), LastSeenAt, DescribeTime
```

### Scenario 10: Event-Driven vs Scan-Based
```bash
./qop.py --seed-resources --non-compliant --account-id 050261919630 --region us-east-1 --profile qop
# Verify event-driven findings appear within 1-2 minutes
./qop.py --scan-account --account-id 050261919630 --scan-type bootstrap --region us-east-1 --profile qop
# Verify scan produces same findings (no duplicates, LastEvaluated updated)
```

## Implementation

### File Structure
```
tools/test/
├── seed_resources.py          # Main script
├── resource_creators/
│   ├── __init__.py
│   ├── s3_creator.py
│   ├── ec2_creator.py
│   ├── iam_creator.py
│   └── rds_creator.py
└── SEED_RESOURCES_GUIDE.md    # Comprehensive guide
```

### Key Functions

#### Account Registration
```python
def ensure_account_registered(account_id: str, region: str):
    """Add account to qrie_accounts if not present"""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    accounts_table = dynamodb.Table('qrie_accounts')
    accounts_table.put_item(Item={
        'AccountId': account_id,
        'AccountName': f'Test Account {account_id}',
        'Status': 'active',
        'OnboardedAt': datetime.now(timezone.utc).isoformat()
    })
```

#### Policy Activation
```python
def ensure_policies_active_with_default_scope(region: str):
    """Launch all policies with default scope if not already active"""
    from data_access.policy_manager import PolicyManager
    from policy_definition import ScopeConfig
    
    pm = PolicyManager()
    for policy_def in pm.get_all_policy_definitions():
        launched = pm.get_launched_policy(policy_def.policy_id)
        if not launched:
            pm.launch_policy(policy_def.policy_id, scope=ScopeConfig())
```

#### Resource Upsert
```python
def upsert_s3_bucket(bucket_name: str, compliant: bool, account_id: str):
    """Create or update S3 bucket configuration"""
    s3 = boto3.client('s3')
    
    # Create if doesn't exist
    try:
        s3.head_bucket(Bucket=bucket_name)
    except:
        s3.create_bucket(Bucket=bucket_name)
    
    # Configure based on compliance mode
    if compliant:
        s3.put_public_access_block(Bucket=bucket_name, PublicAccessBlockConfiguration={...})
        s3.put_bucket_versioning(Bucket=bucket_name, VersioningConfiguration={'Status': 'Enabled'})
        s3.put_bucket_encryption(Bucket=bucket_name, ServerSideEncryptionConfiguration={...})
    else:
        s3.put_public_access_block(Bucket=bucket_name, PublicAccessBlockConfiguration={
            'BlockPublicAcls': False, 'IgnorePublicAcls': False,
            'BlockPublicPolicy': False, 'RestrictPublicBuckets': False
        })
        s3.put_bucket_versioning(Bucket=bucket_name, VersioningConfiguration={'Status': 'Suspended'})
        try:
            s3.delete_bucket_encryption(Bucket=bucket_name)
        except:
            pass
    
    # Tag for cleanup
    s3.put_bucket_tagging(Bucket=bucket_name, Tagging={'TagSet': [
        {'Key': 'qrie-test', 'Value': 'true'},
        {'Key': 'qrie-test-account', 'Value': account_id}
    ]})
```

#### Cleanup with Finding Purge
```python
def cleanup_resources_and_findings(account_id: str, region: str):
    """Delete resources and purge ALL findings"""
    # Delete AWS resources
    delete_test_resources(account_id, region)
    
    # Purge findings
    dynamodb = boto3.resource('dynamodb', region_name=region)
    findings_table = dynamodb.Table('qrie_findings')
    
    response = findings_table.scan(
        FilterExpression='begins_with(AccountService, :account)',
        ExpressionAttributeValues={':account': f'{account_id}_'}
    )
    
    with findings_table.batch_writer() as batch:
        for item in response['Items']:
            batch.delete_item(Key={'ARN': item['ARN'], 'Policy': item['Policy']})
    
    print(f"  ✅ Purged {len(response['Items'])} findings")
```

## Documentation Updates

### 1. README.md
Add to "Testing" section:
```markdown
### E2E Testing with Real Resources
./qop.py --seed-resources --non-compliant --account-id ACCOUNT --region us-east-1 --profile qop
./qop.py --seed-resources --remediate --account-id ACCOUNT --region us-east-1 --profile qop
./qop.py --seed-resources --cleanup --account-id ACCOUNT --region us-east-1 --profile qop
```

### 2. README_DEV.md
Add comprehensive section:
```markdown
## E2E Testing with Seed Resources

See tools/test/SEED_RESOURCES_GUIDE.md for complete testing scenarios.
```

### 3. tools/test/SEED_RESOURCES_GUIDE.md
Create comprehensive guide with all 10 test scenarios, expected outcomes, verification steps.

### 4. qop.py --help
Update help text to include --seed-resources commands.

## Acceptance Criteria

- [ ] `--seed-resources --non-compliant` creates non-compliant resources
- [ ] `--seed-resources --compliant` creates compliant resources
- [ ] `--seed-resources --remediate` updates to compliant (findings resolve)
- [ ] `--seed-resources --cleanup` deletes resources AND purges findings
- [ ] Account automatically registered in qrie_accounts
- [ ] All policies active with default scope (automatic)
- [ ] Resources tagged with `qrie-test=true`
- [ ] Upsert logic (create or update existing)
- [ ] Cost < $0.05 per operation
- [ ] Documentation in SEED_RESOURCES_GUIDE.md
- [ ] README.md and README_DEV.md updated
- [ ] All 10 test scenarios documented

## Timeline

- **Phase 1** (3 hours): Core infrastructure + S3 creator
- **Phase 2** (2 hours): IAM creator
- **Phase 3** (1 hour): EC2 creator  
- **Phase 4** (1 hour): RDS creator
- **Phase 5** (1 hour): Cleanup + finding purge
- **Phase 6** (1 hour): qop.py integration
- **Phase 7** (2 hours): Comprehensive documentation

**Total: ~11 hours**
