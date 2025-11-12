# DynamoDB Schema Redesign Proposal

**Date:** 2025-11-07  
**Status:** Proposal  
**Priority:** High  
**Effort:** Medium (requires data migration)

## Executive Summary

Redesign DynamoDB table schemas to eliminate table scans and enable efficient Query operations for all common access patterns. Current schema forces expensive scans for account-only and service-only queries.

---

## Current Schema Problems

### **qrie_resources Table**

```python
# Current Schema
PK: AccountService (e.g., "123456789012_s3")
SK: ARN
GSI: None
```

**Problems:**
- ❌ Account-only queries require full table scan (can't use `begins_with` on PK in Query)
- ❌ Service-only queries require full table scan
- ✅ Account+Service queries are efficient (direct PK access)

**Query Patterns:**
| Pattern | Current Operation | RCUs (400K items) |
|---------|------------------|-------------------|
| Account only | Scan + filter | ~400,000 |
| Service only | Scan + filter | ~400,000 |
| Account + Service | Query | ~1-10 |

### **qrie_findings Table**

```python
# Current Schema
PK: ARN
SK: Policy
GSI: AccountService-State-index
  - PK: AccountService
  - SK: State
```

**Problems:**
- ❌ Account-only queries (across services) require scan
- ❌ Policy-only queries require scan
- ❌ Service-only queries require scan
- ✅ Account+Service queries use GSI (efficient)
- ✅ Resource-specific queries use main table (efficient)

---

## Proposed Schema Redesign

### **qrie_resources Table - New Schema**

```python
# Main Table
PK: AccountId (e.g., "123456789012")
SK: ARN (e.g., "arn:aws:s3:::my-bucket")

# GSI-1: Service Index
GSI-1:
  PK: Service (e.g., "s3")
  SK: ARN
  Projection: ALL

# Attributes
- AccountId: string
- ARN: string (SK)
- Service: string (extracted from ARN, e.g., "s3", "ec2", "iam")
- AccountService: string (e.g., "123456789012_s3") - kept for compatibility
- Configuration: map
- LastSeenAt: number (timestamp)
```

**Query Patterns:**
| Pattern | Operation | Efficiency |
|---------|-----------|------------|
| Account only | Query main table (PK=AccountId) | ✅ **Efficient** |
| Service only | Query GSI-1 (PK=Service) | ✅ **Efficient** |
| Account + Service | Query main table + filter on Service | ✅ **Efficient** |
| Specific ARN | Query main table (PK=AccountId, SK=ARN) | ✅ **Efficient** |

**Why No GSI-2 for AccountService?**

You correctly identified that we don't need a separate GSI for account+service queries because:

```python
# Can query main table with begins_with on SK
query_params = {
    'KeyConditionExpression': 'AccountId = :account AND begins_with(SK, :service_prefix)',
    'ExpressionAttributeValues': {
        ':account': '123456789012',
        ':service_prefix': 'arn:aws:s3:'  # Service-specific ARN prefix
    }
}
```

This works because ARN format is: `arn:aws:<service>:<region>:<account>:<resource>`

### **qrie_findings Table - New Schema**

```python
# Main Table (unchanged - already optimal for resource lookups)
PK: ARN
SK: Policy

# GSI-1: AccountService Index (existing - keep as-is)
GSI-1: AccountService-State-index
  PK: AccountService
  SK: State
  Projection: ALL

# GSI-2: Policy Index (NEW)
GSI-2: Policy-State-index
  PK: Policy
  SK: State
  Projection: ALL

# GSI-3: Account Index (NEW)
GSI-3: Account-State-index
  PK: AccountId (extracted from AccountService)
  SK: State
  Projection: ALL

# Attributes
- ARN: string (PK)
- Policy: string (SK)
- AccountService: string (e.g., "123456789012_s3")
- AccountId: string (extracted, e.g., "123456789012")
- Service: string (extracted, e.g., "s3")
- State: string ("ACTIVE" or "RESOLVED")
- Severity: number
- FirstSeen: number
- LastEvaluated: number
- Evidence: map
```

**Query Patterns:**
| Pattern | Operation | Efficiency |
|---------|-----------|------------|
| Resource findings | Query main table (PK=ARN) | ✅ **Efficient** |
| Account + Service | Query GSI-1 (PK=AccountService) | ✅ **Efficient** |
| Account only | Query GSI-3 (PK=AccountId) | ✅ **Efficient** |
| Policy only | Query GSI-2 (PK=Policy) | ✅ **Efficient** |
| Service only | Scan + filter (rare use case) | ⚠️ **Acceptable** |

---

## Migration Strategy

### **Phase 1: Add New Attributes (No Downtime)**

1. Update write paths to include new attributes:
   - `inventory_manager.py`: Add `Service` attribute when writing resources
   - `findings_manager.py`: Add `AccountId` attribute when writing findings

2. Backfill existing data:
   ```python
   # Migration script
   for item in scan_table():
       if 'Service' not in item:
           # Extract from AccountService or ARN
           service = extract_service(item)
           update_item(item['ARN'], Service=service)
   ```

### **Phase 2: Add GSIs (No Downtime)**

1. Add GSIs via CDK:
   ```python
   # qrie_resources
   resources.add_global_secondary_index(
       index_name="Service-ARN-index",
       partition_key=ddb.Attribute(name="Service", type=ddb.AttributeType.STRING),
       sort_key=ddb.Attribute(name="ARN", type=ddb.AttributeType.STRING),
       projection_type=ddb.ProjectionType.ALL
   )
   
   # qrie_findings
   findings.add_global_secondary_index(
       index_name="Policy-State-index",
       partition_key=ddb.Attribute(name="Policy", type=ddb.AttributeType.STRING),
       sort_key=ddb.Attribute(name="State", type=ddb.AttributeType.STRING),
       projection_type=ddb.ProjectionType.ALL
   )
   
   findings.add_global_secondary_index(
       index_name="Account-State-index",
       partition_key=ddb.Attribute(name="AccountId", type=ddb.AttributeType.STRING),
       sort_key=ddb.Attribute(name="State", type=ddb.AttributeType.STRING),
       projection_type=ddb.ProjectionType.ALL
   )
   ```

2. Wait for GSI backfill to complete (~hours for large tables)

### **Phase 3: Update Read Paths (No Downtime)**

1. Update data access layer to use GSIs:
   ```python
   # inventory_manager.py
   def get_resources_paginated(account_id, service, ...):
       if account_id and service:
           # Use main table with begins_with
           return query_account_with_service_filter(account_id, service)
       elif account_id:
           # Use main table (after PK change)
           return query_by_account(account_id)
       elif service:
           # Use GSI-1
           return query_gsi_by_service(service)
   ```

2. Test thoroughly in dev/staging

### **Phase 4: Schema Migration (Requires Downtime)**

**Only for qrie_resources** - change PK from AccountService to AccountId

1. Create new table with new schema
2. Copy data from old table to new table
3. Update stack to point to new table
4. Delete old table

**Alternative: Blue-Green Deployment**
- Deploy new stack with new table
- Run dual-write to both tables temporarily
- Switch reads to new table
- Verify and delete old table

---

## Code Changes Required

### **1. Update Write Paths**

```python
# inventory_manager.py
def put_resource(self, arn: str, configuration: Dict, last_seen_ms: int):
    account_id = get_account_from_arn(arn)
    service = get_service_from_arn(arn)
    account_service = f"{account_id}_{service}"
    
    self.table.put_item(Item={
        'AccountId': account_id,        # NEW
        'ARN': arn,
        'Service': service,             # NEW
        'AccountService': account_service,  # Keep for compatibility
        'Configuration': configuration,
        'LastSeenAt': last_seen_ms
    })
```

```python
# findings_manager.py
def put_finding(self, resource_arn: str, policy_id: str, ...):
    account_service = ...
    account_id = account_service.split('_')[0]  # Extract
    
    self.table.update_item(
        Key={'ARN': resource_arn, 'Policy': policy_id},
        UpdateExpression='SET ... #accountId = :accountId',
        ExpressionAttributeNames={'#accountId': 'AccountId'},
        ExpressionAttributeValues={':accountId': account_id, ...}
    )
```

### **2. Update Read Paths**

```python
# inventory_manager.py
def get_resources_paginated(self, account_id, service, page_size, next_token):
    if account_id and service:
        # Query main table with service filter
        return self._query_account_with_service(account_id, service, page_size, next_token)
    elif account_id:
        # Query main table by account
        return self._query_by_account(account_id, page_size, next_token)
    elif service:
        # Query GSI-1 by service
        return self._query_gsi_by_service(service, page_size, next_token)
    else:
        # Full scan (rare)
        return self._scan_all(page_size, next_token)

def _query_account_with_service(self, account_id, service, page_size, next_token):
    """Query main table with service filter using begins_with on SK"""
    query_params = {
        'KeyConditionExpression': 'AccountId = :account AND begins_with(ARN, :service_prefix)',
        'ExpressionAttributeValues': {
            ':account': account_id,
            ':service_prefix': f'arn:aws:{service}:'
        },
        'Limit': page_size
    }
    if next_token:
        query_params['ExclusiveStartKey'] = decode_token(next_token)
    
    response = self.table.query(**query_params)
    return self._format_response(response)
```

```python
# findings_manager.py
def get_findings_paginated(self, account_id, policy_id, state_filter, ...):
    # Choose optimal query path
    if account_id and policy_id:
        # Scan with filters (rare combination)
        return self._scan_with_filters(...)
    elif account_id:
        # Query GSI-3 (Account-State-index)
        return self._query_gsi_by_account(account_id, state_filter, ...)
    elif policy_id:
        # Query GSI-2 (Policy-State-index)
        return self._query_gsi_by_policy(policy_id, state_filter, ...)
    else:
        # Scan all
        return self._scan_all(...)
```

### **3. Update API Layer**

```python
# findings_api.py
def handle_list_findings_paginated(query_params, headers):
    account = query_params.get('account')
    policy = query_params.get('policy')
    state = query_params.get('state')
    
    # Use efficient GSI queries instead of scans
    result = get_findings_manager().get_findings_paginated(
        account_id=account,
        policy_id=policy,
        state_filter=state,
        page_size=page_size,
        next_token=next_token
    )
    # Now uses GSIs internally - no more scans!
```

---

## Performance Impact

### **Before (Current Schema)**

| Query Type | Operation | RCUs (400K items) | Cost/Request |
|------------|-----------|-------------------|--------------|
| Account only | Scan | 400,000 | $0.50 |
| Service only | Scan | 400,000 | $0.50 |
| Account+Service | Query | 10 | $0.000125 |

### **After (New Schema)**

| Query Type | Operation | RCUs (400K items) | Cost/Request |
|------------|-----------|-------------------|--------------|
| Account only | Query | 1-100 | $0.000125 |
| Service only | Query GSI | 1-100 | $0.000125 |
| Account+Service | Query + filter | 1-10 | $0.000125 |

**Cost Savings:** 4,000x reduction for account-only and service-only queries!

---

## Risks & Mitigation

### **Risk 1: Migration Downtime**

**Mitigation:**
- Phase migration (add attributes → add GSIs → update code)
- Only qrie_resources PK change requires downtime
- Use blue-green deployment for zero-downtime migration

### **Risk 2: GSI Costs**

**Impact:**
- 2 new GSIs for qrie_resources: +100% storage cost
- 2 new GSIs for qrie_findings: +100% storage cost
- Still cheaper than continuous scans!

**Mitigation:**
- Use on-demand billing (already using)
- Monitor costs with CloudWatch alarms

### **Risk 3: Data Inconsistency During Migration**

**Mitigation:**
- Dual-write during transition period
- Comprehensive testing in staging
- Rollback plan ready

---

## Timeline

| Phase | Duration | Effort |
|-------|----------|--------|
| 1. Add new attributes | 1 day | Low |
| 2. Backfill existing data | 2-4 hours | Low |
| 3. Add GSIs via CDK | 1 day + backfill time | Low |
| 4. Update read paths | 2-3 days | Medium |
| 5. Testing | 2-3 days | Medium |
| 6. Schema migration (qrie_resources) | 1 day | High |
| **Total** | **~2 weeks** | **Medium** |

---

## Success Metrics

1. **Query Performance:**
   - Account-only queries: < 100ms (from ~5-10s)
   - Service-only queries: < 100ms (from ~5-10s)
   - No table scans in CloudWatch metrics

2. **Cost Reduction:**
   - 90%+ reduction in read costs for filtered queries
   - Acceptable increase in storage costs for GSIs

3. **Scalability:**
   - Support 1M+ resources without performance degradation
   - Support 100+ concurrent users without throttling

---

## Next Steps

1. ✅ Get approval for schema redesign
2. Create detailed migration script
3. Test migration in dev environment
4. Implement Phase 1 (add attributes)
5. Monitor and validate before proceeding to Phase 2

---

## References

- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [GSI Design Patterns](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-indexes-general.html)
- Analysis Document: `changelog/2025-11/2025-11-07-pagination-and-query-analysis.md`
