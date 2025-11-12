# Generic Query Filtering Proposal

## Problem Statement

Currently, API endpoints handle filtering in an ad-hoc manner:
- **Policies API**: Filters in API layer (easy, works well)
- **Findings API**: Limited filtering, no generic query support
- **Resources API**: Limited filtering, no generic query support

We need a **generic, reusable query filtering system** that works across all endpoints and can push filters down to DynamoDB when possible.

---

## Proposed Solution: Query Filter Framework

### Design Principles

1. **Declarative**: Define filterable fields and operators per endpoint
2. **Type-safe**: Validate query parameters against schema
3. **DynamoDB-aware**: Push filters to DB when possible, fall back to in-memory
4. **Consistent**: Same query syntax across all endpoints
5. **Simple**: Easy to add new filterable fields

---

## API Design

### Query Parameter Syntax

```
GET /policies/active?severity=90
GET /policies/active?severity>90
GET /policies/active?severity>=90&category=encryption
GET /policies/active?status=active&open_findings>10
GET /policies/active?service=s3,ec2  # Multi-value (OR)
```

**Supported Operators:**
- `=` - Equals (default if no operator)
- `>` - Greater than
- `>=` - Greater than or equal
- `<` - Less than
- `<=` - Less than or equal
- `!=` - Not equals
- `~` - Contains (string match)

**Multi-value:**
- Comma-separated values treated as OR: `service=s3,ec2` → `service IN ['s3', 'ec2']`

---

## Implementation Architecture

### 1. Query Filter Parser

```python
# qrie-infra/lambda/query_filter.py

from dataclasses import dataclass
from typing import Any, List, Dict, Optional, Literal
from enum import Enum

class FilterOperator(Enum):
    EQ = "="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    NE = "!="
    CONTAINS = "~"
    IN = "in"  # For multi-value

@dataclass
class FilterCondition:
    field: str
    operator: FilterOperator
    value: Any
    
@dataclass
class QueryFilter:
    conditions: List[FilterCondition]
    
    @staticmethod
    def parse(query_params: Dict[str, str], schema: 'FilterSchema') -> 'QueryFilter':
        """Parse query parameters into filter conditions"""
        conditions = []
        
        for param, value in query_params.items():
            if param not in schema.fields:
                continue  # Ignore unknown fields
                
            field_def = schema.fields[param]
            
            # Parse operator from value
            operator = FilterOperator.EQ
            actual_value = value
            
            for op in [FilterOperator.GTE, FilterOperator.LTE, FilterOperator.GT, 
                       FilterOperator.LT, FilterOperator.NE, FilterOperator.CONTAINS]:
                if value.startswith(op.value):
                    operator = op
                    actual_value = value[len(op.value):]
                    break
            
            # Handle multi-value (comma-separated)
            if ',' in actual_value:
                operator = FilterOperator.IN
                actual_value = actual_value.split(',')
            
            # Type conversion
            typed_value = field_def.convert(actual_value)
            
            conditions.append(FilterCondition(
                field=param,
                operator=operator,
                value=typed_value
            ))
        
        return QueryFilter(conditions=conditions)
    
    def apply_in_memory(self, items: List[Dict]) -> List[Dict]:
        """Apply filters to in-memory list"""
        filtered = items
        
        for condition in self.conditions:
            filtered = [
                item for item in filtered
                if self._matches(item.get(condition.field), condition.operator, condition.value)
            ]
        
        return filtered
    
    def _matches(self, item_value: Any, operator: FilterOperator, filter_value: Any) -> bool:
        """Check if item value matches filter condition"""
        if item_value is None:
            return False
            
        if operator == FilterOperator.EQ:
            return item_value == filter_value
        elif operator == FilterOperator.GT:
            return item_value > filter_value
        elif operator == FilterOperator.GTE:
            return item_value >= filter_value
        elif operator == FilterOperator.LT:
            return item_value < filter_value
        elif operator == FilterOperator.LTE:
            return item_value <= filter_value
        elif operator == FilterOperator.NE:
            return item_value != filter_value
        elif operator == FilterOperator.CONTAINS:
            return str(filter_value).lower() in str(item_value).lower()
        elif operator == FilterOperator.IN:
            return item_value in filter_value
        
        return False
    
    def to_dynamodb_filter(self, schema: 'FilterSchema') -> Optional[Dict]:
        """
        Convert to DynamoDB FilterExpression if possible.
        Returns None if filters cannot be pushed to DynamoDB.
        """
        # Only simple equality filters can be pushed to DynamoDB easily
        # Complex filters (>, <, etc.) require FilterExpression which is more complex
        
        # For MVP, return None and do in-memory filtering
        # Future: Implement DynamoDB FilterExpression generation
        return None
```

### 2. Filter Schema Definition

```python
# qrie-infra/lambda/query_filter.py (continued)

from typing import Callable

@dataclass
class FieldDefinition:
    name: str
    type: type
    db_field: Optional[str] = None  # DynamoDB field name if different
    
    def convert(self, value: Any) -> Any:
        """Convert string value to proper type"""
        if isinstance(value, list):
            return [self.type(v) for v in value]
        return self.type(value)

@dataclass
class FilterSchema:
    fields: Dict[str, FieldDefinition]
    
    @staticmethod
    def for_policies() -> 'FilterSchema':
        """Schema for policy filtering"""
        return FilterSchema(fields={
            'policy_id': FieldDefinition('policy_id', str),
            'status': FieldDefinition('status', str),
            'severity': FieldDefinition('severity', int),
            'category': FieldDefinition('category', str),
            'service': FieldDefinition('service', str),
            'open_findings': FieldDefinition('open_findings', int),
        })
    
    @staticmethod
    def for_findings() -> 'FilterSchema':
        """Schema for findings filtering"""
        return FilterSchema(fields={
            'account': FieldDefinition('account', str),
            'service': FieldDefinition('service', str),
            'policy': FieldDefinition('policy', str),
            'state': FieldDefinition('state', str),
            'severity': FieldDefinition('severity', int),
        })
    
    @staticmethod
    def for_resources() -> 'FilterSchema':
        """Schema for resources filtering"""
        return FilterSchema(fields={
            'account': FieldDefinition('account', str),
            'service': FieldDefinition('service', str),
        })
```

### 3. Usage in API Handlers

```python
# qrie-infra/lambda/api/policies_api.py

from query_filter import QueryFilter, FilterSchema

def handle_list_active_policies(query_params, headers):
    """Handle GET /policies/active with generic filtering"""
    try:
        from data_access.findings_manager import FindingsManager
        findings_manager = FindingsManager()
        
        # Get all active policies
        policies = get_policy_manager().list_launched_policies(status_filter='active')
        
        # Build policy data with findings count
        policies_data = []
        for policy in policies:
            open_findings_count = findings_manager.count_findings(
                policy_id=policy.policy_id,
                state_filter='ACTIVE'
            )
            
            policies_data.append({
                'policy_id': policy.policy_id,
                'description': policy.description,
                'service': policy.service,
                'category': policy.category,
                'scope': asdict(policy.scope),
                'severity': policy.severity,
                'remediation': policy.remediation,
                'open_findings': open_findings_count,
                'created_at': policy.created_at.split('T')[0] if policy.created_at else None,
                'updated_at': policy.updated_at.split('T')[0] if policy.updated_at else None,
                'status': policy.status
            })
        
        # Apply generic filters
        schema = FilterSchema.for_policies()
        query_filter = QueryFilter.parse(query_params, schema)
        filtered_data = query_filter.apply_in_memory(policies_data)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(filtered_data)
        }
    
    except Exception as error:
        print(f"Error getting active policies: {error}")
        traceback.format_exc()
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to get active policies'})
        }
```

---

## DynamoDB Query Optimization (Future)

For endpoints that query DynamoDB directly (findings, resources), we can optimize:

### Phase 1: In-Memory Filtering (MVP)
- Fetch all items from DynamoDB
- Apply filters in Python
- Simple, works for small datasets

### Phase 2: DynamoDB FilterExpression
- Convert simple filters to DynamoDB FilterExpression
- Reduces data transfer from DynamoDB
- Still scans all items

```python
def to_dynamodb_filter_expression(self) -> Dict:
    """Generate DynamoDB FilterExpression"""
    expressions = []
    values = {}
    names = {}
    
    for i, condition in enumerate(self.conditions):
        attr_name = f"#attr{i}"
        attr_value = f":val{i}"
        
        names[attr_name] = condition.field
        values[attr_value] = condition.value
        
        if condition.operator == FilterOperator.EQ:
            expressions.append(f"{attr_name} = {attr_value}")
        elif condition.operator == FilterOperator.GT:
            expressions.append(f"{attr_name} > {attr_value}")
        # ... etc
    
    return {
        'FilterExpression': ' AND '.join(expressions),
        'ExpressionAttributeNames': names,
        'ExpressionAttributeValues': values
    }
```

### Phase 3: GSI-based Queries (Optimal)
- Create GSIs for common query patterns
- Use Query instead of Scan
- Much faster for large datasets

**Example GSIs:**
```python
# Findings by severity
GSI: severity-state-index
  PK: Severity
  SK: State

# Findings by account
GSI: account-service-index  (already exists)
  PK: AccountService
  SK: ARN
```

---

## Migration Plan

### Step 1: Implement Query Filter Framework ✅
- Create `query_filter.py` with parser and schema
- Add unit tests
- Document usage

### Step 2: Update Policies API ✅
- Replace manual filtering with QueryFilter
- Add support for all operators
- Test with UI

### Step 3: Update Findings API
- Add FilterSchema for findings
- Support filtering by severity, state, policy, account
- Maintain backward compatibility

### Step 4: Update Resources API
- Add FilterSchema for resources
- Support filtering by account, service
- Maintain backward compatibility

### Step 5: DynamoDB Optimization (Future)
- Implement FilterExpression generation
- Add GSIs for common queries
- Benchmark performance improvements

---

## Example API Calls

```bash
# Policies
GET /policies/active?severity>=80
GET /policies/active?category=encryption&service=s3
GET /policies/active?open_findings>10
GET /policies/active?status=active&severity>=90

# Findings
GET /findings?severity>=80
GET /findings?state=ACTIVE&severity>70
GET /findings?policy=S3BucketPublic&account=123456789012
GET /findings?service=s3&state=ACTIVE

# Resources
GET /resources?account=123456789012&service=s3,ec2
GET /resources?service=s3
```

---

## Benefits

1. **Consistency**: Same query syntax across all endpoints
2. **Flexibility**: Easy to add new filters without code changes
3. **Type Safety**: Automatic type conversion and validation
4. **Performance**: Can optimize with DynamoDB filters later
5. **Maintainability**: Centralized filtering logic
6. **Extensibility**: Easy to add new operators or field types

---

## Trade-offs

### In-Memory Filtering (MVP)
**Pros:**
- Simple to implement
- Works immediately
- No DB schema changes

**Cons:**
- Fetches all data from DB
- Slower for large datasets
- Higher memory usage

### DynamoDB FilterExpression (Phase 2)
**Pros:**
- Reduces data transfer
- Better performance
- No schema changes

**Cons:**
- Still scans all items
- Complex expression building
- Limited operator support

### GSI-based Queries (Phase 3)
**Pros:**
- Optimal performance
- Scales to large datasets
- True query (not scan)

**Cons:**
- Requires GSI creation
- Additional storage cost
- Schema changes needed

---

## Recommendation

**For MVP:** Implement in-memory filtering with QueryFilter framework
- Quick to implement
- Works for current dataset sizes
- Provides consistent API
- Easy to optimize later

**For V1:** Add DynamoDB FilterExpression support
- Better performance
- No breaking changes
- Incremental improvement

**For V2:** Add GSIs for high-traffic queries
- Optimal performance
- Based on actual usage patterns
- Data-driven optimization

---

## Implementation Checklist

- [ ] Create `query_filter.py` with QueryFilter class
- [ ] Add FilterSchema definitions for each endpoint
- [ ] Update `handle_list_active_policies()` to use QueryFilter
- [ ] Update `handle_list_available_policies()` to use QueryFilter
- [ ] Update findings API handlers
- [ ] Update resources API handlers
- [ ] Add unit tests for QueryFilter
- [ ] Add integration tests for filtered endpoints
- [ ] Update API documentation
- [ ] Update UI to use new query parameters

---

## Questions to Consider

1. **Pagination**: How do filters interact with pagination?
   - Apply filters before or after pagination?
   - Count total before or after filtering?

2. **Sorting**: Should we support `?sort=severity&order=desc`?
   - Add to QueryFilter framework?
   - Separate concern?

3. **Field Aliases**: Should we support UI-friendly names?
   - `open_findings` vs `openFindings`
   - Convert in API layer?

4. **Validation**: How strict should validation be?
   - Ignore unknown fields?
   - Return 400 error?
   - Log warnings?

5. **Performance**: When to switch from in-memory to DB filtering?
   - Based on dataset size?
   - Based on query complexity?
   - Configurable threshold?
