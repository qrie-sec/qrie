# Unified Policy Model & Naming Convention

**Date:** October 15, 2025  
**Type:** Breaking Change  
**Version:** 3.0

## Summary

Implemented a unified policy data model across all layers (API, database, UI, documentation) with consistent snake_case field naming and standardized policy naming convention following non-compliant state pattern.

## Breaking Changes

### 1. API Response Field Names (snake_case)

All API endpoints now return consistent snake_case field names:

**Changed Fields:**
- `id` → `policy_id`
- `name` → removed (redundant with `policy_id`)
- `openFindings` → `open_findings`
- `enforcedSince` → `created_at`
- `lastUpdated` → `updated_at`

**New Fields in Active Policy Response:**
- `description` - Policy description
- `service` - AWS service (e.g., "s3", "ec2")
- `category` - Policy category (e.g., "encryption", "access_control")

### 2. Policy Naming Convention

All policies now follow **non-compliant state naming**:
- Policy names describe the BAD state being detected
- Format: `{Service}{NonCompliantCondition}`
- Example: `S3BucketVersioningDisabled` (not `S3BucketVersioning`)

**Renamed Policies:**
- `S3BucketVersioning` → `S3BucketVersioningDisabled`

**Removed Policies:**
- `s3_public_bucket.py` (duplicate, kept `s3_bucket_public.py`)

### 3. Scope Tag Structure

Tag values are now arrays instead of strings:
- **Before:** `{"Environment": "prod"}`
- **After:** `{"Environment": ["prod", "staging"]}`

## Files Changed

### Backend
- `/qrie-infra/lambda/api/policies_api.py` - Updated all response serialization
- `/qrie-infra/lambda/data_access/policy_manager.py` - Changed `id` to `policy_id`
- `/qrie-infra/lambda/policies/s3_bucket_versioning.py` - Renamed policy
- `/qrie-infra/lambda/policies/s3_public_bucket.py` - Deleted (duplicate)

### Data & Tests
- `/tools/data/seed_data.py` - Updated policy names, removed Service field, fixed tag structure
- `/qrie-ui/lib/api.ts` - Updated test data to match new model

### Documentation
- `/qrie-infra/POLICY_NAMING.md` - New policy naming convention guide
- `/qrie-infra/qrie_apis.md` - Updated all API examples and TypeScript interfaces

### Frontend
- `/qrie-ui/lib/types.ts` - Updated all policy interfaces
- `/qrie-ui/lib/api.ts` - Updated test data and API client

## Migration Guide

### For API Consumers

Update field names in your code:

```typescript
// Before
const policyId = policy.id
const findings = policy.openFindings
const since = policy.enforcedSince

// After
const policyId = policy.policy_id
const findings = policy.open_findings
const since = policy.created_at
```

### For Policy Definitions

Follow the new naming convention:

```python
# Good - Describes non-compliant state
PolicyDefinition(
    policy_id="S3BucketVersioningDisabled",
    description="Detects S3 buckets without versioning enabled",
    ...
)

# Bad - Unclear or describes compliant state
PolicyDefinition(
    policy_id="S3BucketVersioning",  # Unclear
    policy_id="S3BucketVersioningEnabled",  # Compliant state
    ...
)
```

### For Scope Configuration

Use arrays for tag values:

```python
# Before
'IncludeTags': {'Environment': 'prod'}

# After
'IncludeTags': {'Environment': ['prod', 'staging']}
```

## Benefits

1. **Consistency:** Single naming convention across all layers
2. **Clarity:** Policy names clearly indicate what's wrong
3. **Maintainability:** Easier for new developers to understand
4. **Industry Standard:** Matches AWS Config Rules, Security Hub patterns
5. **Type Safety:** Better TypeScript type checking with consistent fields

## Policy Naming Examples

### ✅ Good Names
- `S3BucketPublic` - Bucket IS public (bad)
- `EC2UnencryptedEBS` - Volume IS unencrypted (bad)
- `RDSPublicAccess` - Database HAS public access (bad)
- `IAMPasswordPolicyWeak` - Policy IS weak (bad)
- `CloudTrailDisabled` - CloudTrail IS disabled (bad)

### ❌ Bad Names
- `S3BucketVersioning` - Unclear (enabled or disabled?)
- `S3BucketPrivate` - Describes compliant state
- `CheckS3Encryption` - Redundant "Check" prefix

## Testing

- ✅ Backend API responses validated
- ✅ Frontend TypeScript types updated
- ✅ Seed data updated
- ✅ API documentation updated
- ⚠️ UI components need testing with real API

## Next Steps

1. Test UI with updated API responses
2. Update any hardcoded policy names in UI components
3. Run end-to-end tests
4. Update any external integrations using the API

## References

- Policy Naming Convention: `/qrie-infra/POLICY_NAMING.md`
- API Documentation: `/qrie-infra/qrie_apis.md`
- TypeScript Types: `/qrie-ui/lib/types.ts`
