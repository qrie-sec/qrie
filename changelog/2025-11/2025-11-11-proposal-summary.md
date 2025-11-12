# Seed Resources Proposal - Summary of Changes

**Date:** 2025-11-11

## Key Changes from Original Proposal

### 1. ✅ Naming Convention
**Before:** `--test-e2e`, `--test-e2e-cleanup`  
**After:** `--seed-resources` with flags `--non-compliant`, `--compliant`, `--remediate`, `--cleanup`

**Rationale:**
- `--seed-data` = populates DynamoDB with **end result** (findings)
- `--seed-resources` = creates AWS resources as **input** that triggers system
- Clear, consistent naming that reflects purpose

### 2. ✅ Account Registration (Automatic)
- Script automatically adds account to `qrie_accounts` table
- No manual DynamoDB put-item needed
- Sets Status='active', includes OnboardedAt timestamp

### 3. ✅ Policy Activation with Default Scope (Automatic)
- Script ensures ALL 11 policies are active
- Uses default (empty) scope = applies to all accounts
- Launches any policies not yet launched
- No manual policy configuration needed

### 4. ✅ Cleanup with Finding Purge
- `--cleanup` deletes AWS resources AND purges findings
- Removes from both AWS and qrie_findings table
- Purges ACTIVE and RESOLVED findings
- Clean slate for next test run

### 5. ✅ Remediation Support
- `--remediate` flag makes resources compliant
- Triggers CloudTrail events → findings resolve automatically
- Tests the full compliance lifecycle

### 6. ✅ Manual Verification Scenarios
Added comprehensive test scenarios:
- Launch available policy → verify scan triggered
- Update scope to exclude account → findings gone
- Re-include account → findings return (after scan)
- Delete policy → findings purged
- Event-driven vs scan-based evaluation

### 7. ✅ Comprehensive Test Flow Documentation
10 detailed scenarios covering:
1. Non-compliant → findings created
2. Policy deletion → findings purged
3. Scope exclusion → findings gone
4. Scope re-inclusion → findings return
5. Remediation → findings resolved
6. Compliant resources → no findings
7. Cleanup → resources & findings purged
8. Launch policy → scan triggered
9. Inventory validation (detailed field checks)
10. Event-driven vs scan-based comparison

### 8. ✅ Documentation Updates
- README.md: Add E2E testing section
- README_DEV.md: Reference comprehensive guide
- tools/test/SEED_RESOURCES_GUIDE.md: Complete testing guide
- qop.py --help: Updated help text

## Command Examples

```bash
# Create non-compliant resources (automatic account registration + policy activation)
./qop.py --seed-resources --non-compliant --account-id 050261919630 --region us-east-1 --profile qop

# Make resources compliant (findings resolve automatically)
./qop.py --seed-resources --remediate --account-id 050261919630 --region us-east-1 --profile qop

# Delete resources and purge ALL findings
./qop.py --seed-resources --cleanup --account-id 050261919630 --region us-east-1 --profile qop
```

## Implementation Notes

### Upsert Logic
Resources are created if they don't exist, updated if they do:
```python
try:
    s3.head_bucket(Bucket=bucket_name)
    exists = True
except:
    exists = False

if not exists:
    s3.create_bucket(Bucket=bucket_name)

# Update configuration regardless
s3.put_public_access_block(...)
s3.put_bucket_versioning(...)
```

### Finding Purge
Cleanup purges ALL findings (not just ACTIVE):
```python
response = findings_table.scan(
    FilterExpression='begins_with(AccountService, :account)',
    ExpressionAttributeValues={':account': f'{account_id}_'}
)

with findings_table.batch_writer() as batch:
    for item in response['Items']:
        batch.delete_item(Key={'ARN': item['ARN'], 'Policy': item['Policy']})
```

### Caching Strategy
For E2E testing, set TTL=0 via environment variable:
- UI: TTL-cache all data pulls (findings, accounts, policies)
- Backend: No caching (hard refresh always gets fresh data)
- Account metadata fetch: Cached but environment variable driven
- Policy scope fetch: Cached but environment variable driven

## Next Steps

1. Review and approve proposal
2. Implement in phases (11 hours total)
3. Test all 10 scenarios
4. Update documentation
5. Add to CI/CD pipeline (optional)

## Questions Addressed

✅ Account registration automatic?  
✅ Policies active with default scope?  
✅ Cleanup purges findings?  
✅ Remediation support?  
✅ Manual verification scenarios?  
✅ Naming convention clear?  
✅ Test flow comprehensive?  
✅ Documentation complete?  

All requirements addressed in revised proposal!
