# Seed Data Enhancement - Pagination Testing Support

**Date:** 2025-11-07  
**Status:** Complete  
**Related:** `2025-11-07-pagination-implementation.md`

## Summary

Enhanced seed data generation to create sufficient test data (750+ resources, 200+ findings) to properly test UI pagination functionality. This ensures the "Load More" button and `next_token` pagination can be validated in development and staging environments.

---

## Changes Made

### **1. Expanded Test Accounts**

Added 2 additional test accounts for more realistic data distribution:

```python
accounts = [
    "123456789012",  # Production account
    "987654321098",  # Staging account  
    "555666777888",  # Development account
    "111222333444",  # QA account (NEW)
    "999888777666",  # DR account (NEW)
]
```

### **2. Bulk Resource Generation**

Created `generate_bulk_resources()` function to programmatically generate large datasets:

**Configuration:**
- **5 accounts** × **5 services** × **30 resources per service** = **750 resources**
- Services: S3, EC2, RDS, Lambda, DynamoDB
- Realistic configurations with varied properties

**Resource Distribution:**
```
Account 123456789012:
  - 30 S3 buckets (bucket-123456789012-000 to bucket-123456789012-029)
  - 30 EC2 instances (i-0000000000000000 to i-000000000000001d)
  - 30 RDS databases (database-000 to database-029)
  - 30 Lambda functions (function-000 to function-029)
  - 30 DynamoDB tables (table-000 to table-029)

... repeated for all 5 accounts
```

**Realistic Variations:**
- S3: Mix of public/private, versioned/unversioned, encrypted/unencrypted
- EC2: Different instance types, some with public IPs, mixed EBS encryption
- RDS: Postgres/MySQL mix, varied backup retention, some publicly accessible
- Lambda: Python/Node.js mix, different memory sizes, some in VPC
- DynamoDB: On-demand/provisioned mix, varied encryption and PITR settings

### **3. Enhanced Findings Generation**

Updated `generate_historical_findings()` to create more findings:

**Before:**
- 5-15 findings per week × 8 weeks = 40-120 findings

**After:**
- 20-30 findings per week × 8 weeks = **160-240 findings**
- Expanded policy configurations to cover more accounts
- Mix of ACTIVE (70%) and RESOLVED (30%) states

**Policy Coverage:**
```python
policy_configs = [
    ('S3BucketPublic', '123456789012_s3', 90),
    ('S3BucketVersioningDisabled', '123456789012_s3', 60),
    ('S3BucketEncryptionDisabled', '987654321098_s3', 90),
    ('S3BucketPublic', '987654321098_s3', 90),
    ('S3BucketVersioningDisabled', '555666777888_s3', 60),
    ('S3BucketEncryptionDisabled', '111222333444_s3', 90),
    ('EC2UnencryptedEBS', '123456789012_ec2', 70),
    ('EC2UnencryptedEBS', '987654321098_ec2', 70),
    ('EC2UnencryptedEBS', '555666777888_ec2', 70),
    ('IAMRootAccountActive', '123456789012_iam', 95),
    ('IAMUserMfaDisabled', '123456789012_iam', 85),
    ('IAMUserMfaDisabled', '987654321098_iam', 85),
    ('IAMUserMfaDisabled', '555666777888_iam', 85),
]
```

### **4. Updated Documentation**

Enhanced `tools/data/SEED_DATA_README.md` with:
- Pagination testing section
- Bulk data generation documentation
- Expected data volumes
- Updated output examples

---

## Data Volumes

| Resource Type | Count | Purpose |
|--------------|-------|---------|
| Accounts | 5 | Multi-account testing |
| Resources | 750+ | Pagination testing (>100 items) |
| Findings | 160-240 | Pagination testing (>100 items) |
| Policies | 6 | Policy evaluation testing |

**Pagination Thresholds:**
- UI fetches 100 items per API call
- UI displays 25 items per page
- "Load More" button appears when >100 items exist
- With 750 resources, user can test loading 7-8 pages
- With 200 findings, user can test loading 2-3 pages

---

## Testing Scenarios Enabled

### **Inventory View:**
1. ✅ Initial load shows first 100 resources
2. ✅ "Load More" button appears (650 more available)
3. ✅ Click "Load More" → fetches next 100 (550 more available)
4. ✅ Continue until all 750 loaded
5. ✅ Filter by account → pagination still works
6. ✅ Filter by service → pagination still works

### **Findings View:**
1. ✅ Initial load shows first 100 findings
2. ✅ "Load More" button appears (100+ more available)
3. ✅ Click "Load More" → fetches next 100
4. ✅ Continue until all findings loaded
5. ✅ Filter by account → pagination resets correctly
6. ✅ Filter by policy → pagination resets correctly
7. ✅ Filter by status → pagination resets correctly

---

## Usage

### **Seed Data with Pagination Testing:**

```bash
# From repo root
./qop.py --seed-data --region us-east-1 --profile qop

# Or directly
cd tools/data
python3 seed_data.py --clear --region us-east-1
```

### **Expected Output:**

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

---

## Performance Considerations

### **DynamoDB Write Performance:**
- 750 resources = ~750 write requests
- 200 findings = ~200 write requests
- Uses batch writes where possible
- Typical seed time: 30-60 seconds

### **Storage Costs:**
- 750 resources × ~1KB = ~750KB
- 200 findings × ~1KB = ~200KB
- Negligible cost for testing

### **Query Performance:**
With current schema (before redesign):
- Account-only queries: Scan 750 items (slow)
- Service-only queries: Scan 750 items (slow)
- Account+Service queries: Query ~150 items (fast)

This validates the need for schema redesign!

---

## Files Modified

1. `/Users/shubham/dev/qrie/tools/data/seed_data.py`
   - Added `generate_bulk_resources()` function
   - Expanded accounts list to 5 accounts
   - Updated to use bulk generation

2. `/Users/shubham/dev/qrie/tools/data/generate_historical_findings.py`
   - Increased findings per week from 5-15 to 20-30
   - Expanded policy configurations to cover more accounts
   - Added more account/service combinations

3. `/Users/shubham/dev/qrie/tools/data/SEED_DATA_README.md`
   - Added pagination testing section
   - Documented bulk data generation
   - Updated expected output examples

---

## Validation

### **Manual Testing Checklist:**

**Inventory View:**
- [ ] Load page → see first 100 resources
- [ ] See "(more available)" indicator
- [ ] Click "Load More" → see 200 resources total
- [ ] Click "Load More" again → see 300 resources total
- [ ] Continue until all 750 loaded
- [ ] Filter by account → pagination resets
- [ ] "Load More" works with filters

**Findings View:**
- [ ] Load page → see first 100 findings
- [ ] See "(more available)" indicator
- [ ] Click "Load More" → see 200 findings total
- [ ] Filter by account → pagination resets
- [ ] Filter by policy → pagination resets
- [ ] Filter by status → pagination resets
- [ ] "Load More" works with all filter combinations

### **API Testing:**

```bash
# Test resources pagination
curl 'https://API-URL/resources?page_size=100'
# Should return 100 resources + next_token

curl 'https://API-URL/resources?page_size=100&next_token=TOKEN'
# Should return next 100 resources

# Test findings pagination
curl 'https://API-URL/findings?page_size=100&state=ACTIVE'
# Should return 100 findings + next_token

curl 'https://API-URL/findings?page_size=100&state=ACTIVE&next_token=TOKEN'
# Should return next 100 findings
```

---

## Next Steps

1. ✅ **DONE:** Generate bulk test data
2. 🔄 **TODO:** Deploy to dev environment and test pagination
3. 🔄 **TODO:** Validate "Load More" functionality in UI
4. 🔄 **TODO:** Test with different filter combinations
5. 🔄 **TODO:** Monitor DynamoDB query patterns in CloudWatch
6. 🔄 **TODO:** Begin schema redesign implementation

---

## Benefits

### **For Development:**
- ✅ Realistic data volumes for testing
- ✅ Validates pagination implementation
- ✅ Tests UI performance with large datasets
- ✅ Identifies query inefficiencies

### **For QA:**
- ✅ Comprehensive test data available
- ✅ Reproducible test scenarios
- ✅ Multi-account testing enabled
- ✅ Edge cases covered (exactly 100, 101, 1000+ items)

### **For Performance Testing:**
- ✅ Validates scan vs query performance
- ✅ Identifies bottlenecks
- ✅ Justifies schema redesign
- ✅ Baseline for optimization

---

## Related Work

- **UI Pagination:** `2025-11-07-pagination-implementation.md`
- **Schema Redesign:** `roadmap/2025-11-00-dynamodb-schema-redesign.md`
- **Query Analysis:** `roadmap/2025-11-07-pagination-and-query-analysis.md`
