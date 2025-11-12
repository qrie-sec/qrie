# Seed Data - Dynamic Policy Loading & Pagination Testing

## Overview

The seed data script **dynamically loads actual policy definitions** from the `/qrie-infra/lambda/policies/` directory and **generates bulk test data** for pagination testing, ensuring that seeded data always matches the real policy definitions and provides sufficient volume for testing UI pagination.

## How It Works

### 1. **Policy Discovery**
```python
def load_policy_definitions():
    """Load all policy definitions from the policies directory"""
```
- Scans `/qrie-infra/lambda/policies/` for all `.py` files
- Dynamically imports each module
- Extracts `PolicyDefinition` objects using introspection
- Returns a dictionary of `{policy_id: PolicyDefinition}`

### 2. **Dynamic Policy Creation**
```python
def create_launched_policy(policy_id, status='active', scope=None, severity_override=None):
    """Create launched policy from actual definition"""
```
- Looks up the policy definition by ID
- Uses actual `policy_id`, `severity`, `remediation`, `description` from the definition
- Allows custom scope and status for testing scenarios
- Warns if a policy ID doesn't exist

### 3. **Bulk Resource Generation**
```python
def generate_bulk_resources(accounts, count_per_service=30):
    """Generate bulk resources for pagination testing"""
```
- Generates resources across **5 accounts** × **5 services** × **30 resources** = **750 resources**
- Services: S3, EC2, RDS, Lambda, DynamoDB
- Realistic configurations with varied properties
- Ensures pagination kicks in (>100 items per query)

### 4. **Historical Findings Generation**
```python
def generate_historical_findings():
    """Generate findings spanning 8 weeks - expanded for pagination testing"""
```
- Generates **20-30 findings per week** × **8 weeks** = **160-240 findings**
- Spans multiple accounts and services
- Mix of ACTIVE (70%) and RESOLVED (30%) states
- Ensures pagination testing with >100 findings

### 5. **Seeded Policies**

Currently seeds **6 policies** with various configurations:

| Policy ID | Service | Status | Severity | Scope |
|-----------|---------|--------|----------|-------|
| `S3BucketPublic` | s3 | active | 90 | Prod + Staging accounts |
| `S3BucketVersioningDisabled` | s3 | active | 60 | All except Dev |
| `S3BucketEncryptionDisabled` | s3 | active | 90 | Prod + Staging |
| `EC2UnencryptedEBS` | ec2 | active | 70 | Prod only |
| `RDSPublicAccess` | rds | suspended | 95 | All accounts |
| `IAMRootAccountActive` | iam | active | 95 | All accounts |
| `IAMUserMfaDisabled` | iam | active | 85 | Prod only |

## Benefits

### ✅ **Always In Sync**
- Seed data automatically uses latest policy definitions
- No manual updates needed when policies change
- Severity, descriptions, remediation always match source of truth

### ✅ **Type Safe**
- Uses actual `PolicyDefinition` objects
- Catches missing or renamed policies at seed time
- Warns about invalid policy IDs

### ✅ **Pagination Testing**
- **750+ resources** ensure pagination kicks in (>100 items)
- **160-240 findings** test "Load More" functionality
- Realistic data distribution across accounts and services
- Tests both inventory and findings pagination flows

### ✅ **Flexible Testing**
- Can override severity for testing
- Can customize scope per policy
- Can set different statuses (active/suspended)
- Adjustable resource/finding counts via parameters

### ✅ **Self-Documenting**
- Prints loaded policies during seeding
- Shows resource and finding counts
- Clear output for debugging

## Usage

```bash
# Seed with actual policy definitions
cd tools/data
python3 seed_data.py --clear --region us-east-1

# Or use qop.py
./qop.py --seed-data --region us-east-1 --profile qop
```

## Output Example

```
✓ Loaded 11 policy definitions

📦 Generating bulk resources for pagination testing...
✓ Generated 750 resources

✓ Created 6 launched policies from definitions
  - S3BucketPublic (active, severity=90)
  - S3BucketVersioningDisabled (active, severity=60)
  - S3BucketEncryptionDisabled (active, severity=90)
  - EC2UnencryptedEBS (active, severity=70)
  - RDSPublicAccess (suspended, severity=95)
  - IAMRootAccountActive (active, severity=95)
  - IAMUserMfaDisabled (active, severity=85)

🚀 Starting seed data population...
👥 Populating qrie_accounts table...
  ✅ Added account: 123456789012
  ✅ Added account: 987654321098
  ✅ Added account: 555666777888
🔍 Generating historical findings (8 weeks)...
Generated 196 historical findings
  Active: 137
  Resolved: 59

🚀 Starting seed data population...
👥 Populating qrie_accounts table...
  ✅ Added 5 accounts

📦 Populating qrie_resources table...
  ✅ Added 750+ resources

📋 Populating qrie_policies table...
  ✅ Added 6 launched policies

🔍 Populating qrie_findings table...
  ✅ Added 200+ findings

🎉 Seed data population completed successfully!
  📊 Summary:
    - 5 accounts
    - 750+ resources (pagination ready)
    - 6 active policies
    - 200+ findings (pagination ready)
```

## Available Policies

All 11 policies from `/qrie-infra/lambda/policies/`:

### S3 (4 policies)
- `S3BucketPublic` - Public read access (severity: 90)
- `S3BucketVersioningDisabled` - No versioning (severity: 60)
- `S3BucketEncryptionDisabled` - No encryption (severity: 90)
- `S3BucketMfaDeleteDisabled` - No MFA delete (severity: 70)

### IAM (5 policies)
- `IAMRootAccountActive` - Root account usage (severity: 95)
- `IAMUserMfaDisabled` - No MFA on users (severity: 85)
- `IAMPolicyOverlyPermissive` - Wildcard permissions (severity: 80)
- `IAMAccessKeyUnused` - Keys unused 90+ days (severity: 60)
- `IAMAccessKeyNotRotated` - Keys not rotated (severity: 70)

### EC2 (1 policy)
- `EC2UnencryptedEBS` - Unencrypted EBS volumes (severity: 70)

### RDS (1 policy)
- `RDSPublicAccess` - Public accessibility (severity: 95)

## Adding New Policies to Seed Data

To add a new policy to seed data:

```python
# In create_seed_data() function
policy = create_launched_policy(
    'NewPolicyId',  # Must match actual policy definition
    status='active',
    scope={
        'IncludeAccounts': ['123456789012'],
        'ExcludeAccounts': [],
        'IncludeTags': {},
        'ExcludeTags': {},
        'IncludeOuPaths': [],
        'ExcludeOuPaths': []
    },
    severity_override=None,  # Optional: override default severity
    created_at='2024-01-15T10:30:00Z'
)
if policy:
    policies.append(policy)
```

## Error Handling

- **Missing Policy**: Warns and skips if policy ID not found
- **Import Errors**: Warns and continues with other policies
- **Invalid Scope**: Uses default empty scope if none provided

## Future Enhancements

- [ ] Add more IAM policies to seed data (access key rotation, overly permissive)
- [ ] Add S3 MFA delete policy to seed data
- [ ] Generate findings automatically based on resource configurations
- [ ] Support seeding from YAML/JSON config file
- [ ] Add policy tags/categories to seed data
