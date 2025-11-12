# Service Registry Refactoring & Developer Documentation

**Date**: 2025-11-05  
**Status**: ✅ Implemented

## Overview
Major refactoring to introduce service registry pattern, improve code organization, and create comprehensive developer documentation. This addresses code review feedback about service-specific operations and testing practices.

## Code Review Issues Addressed

### **1. ARN Utility Functions**
**Problem**: Test-specific code in production (`inventory_manager.py` had hardcoded account ID for tests)

**Solution**:
- Moved ARN utilities to `common_utils.py`
- Renamed functions: `extract_account_from_arn()` → `get_account_from_arn()`
- Renamed functions: `extract_service_from_arn()` → `get_service_from_arn()`
- Added proper documentation about S3 bucket ARN limitations
- Removed test-specific code from production modules
- Added backward compatibility aliases

### **2. Service-Specific Operations**
**Problem**: Service-specific logic scattered across multiple files with if/elif chains

**Solution**: Created service registry pattern with dedicated support modules

**Before**:
```python
# event_handler.py
if event_source == 's3.amazonaws.com':
    bucket_name = request_params.get('bucketName')
    return f"arn:aws:s3:::{bucket_name}"
elif event_source == 'ec2.amazonaws.com':
    # TODO
    pass
elif event_source == 'iam.amazonaws.com':
    # TODO
    pass
```

**After**:
```python
# event_handler.py
from services import extract_arn_from_event
arn = extract_arn_from_event(service, detail)
```

### **3. Developer Documentation**
**Problem**: No consolidated developer guide covering architecture, setup, testing, and operations

**Solution**: Created comprehensive `README_DEV.md` with sections:
- Architecture overview with diagrams
- Code layout and design patterns
- Local development and unit testing
- QOP account setup (core + UI stacks)
- Test/subject account setup (EventBridge + IAM)
- E2E testing procedures
- Service onboarding guide
- Customer operations (onboarding, monitoring)

## Implementation Details

### **Service Registry Pattern**

Created `lambda/services/` directory with:

**1. Service Support Modules**:
- `s3_support.py` - Fully implemented
- `ec2_support.py` - Placeholder with TODOs
- `iam_support.py` - Placeholder with TODOs

Each module provides three functions:
```python
def extract_arn_from_event(detail: dict) -> Optional[str]:
    """Extract resource ARN from CloudTrail event detail"""
    
def describe_resource(arn: str, account_id: str, client=None) -> dict:
    """Describe resource configuration"""
    
def list_resources(account_id: str, client=None) -> List[Dict]:
    """List all resources for the service"""
```

**2. Service Registry** (`services/__init__.py`):
```python
class ServiceRegistry:
    """Dynamic service loading with importlib"""
    
    @classmethod
    def extract_arn_from_event(cls, service: str, detail: dict) -> Optional[str]:
        module = cls._get_module(service)
        return module.extract_arn_from_event(detail)
    
    # Similar for describe_resource() and list_resources()
```

**3. Convenience Functions**:
```python
from services import extract_arn_from_event, describe_resource, list_resources
```

### **Refactored Modules**

**1. `event_processor/event_handler.py`**:
- `_extract_arn_from_event()` now uses service registry
- `_describe_resource()` delegates to service-specific describe
- Removed `_describe_s3_bucket()` (moved to `s3_support.py`)

**2. `inventory_generator/inventory_handler.py`**:
- `generate_inventory_for_account_service()` uses service registry
- Removed if/elif chain for service routing
- Generic implementation that works for all services

**3. `data_access/inventory_manager.py`**:
- Removed test-specific hardcoded account ID
- Uses `get_account_from_arn()` and `get_service_from_arn()`
- Proper error message for S3 buckets (ARN doesn't contain account)

**4. `common_utils.py`**:
- Added `get_account_from_arn()` with documentation
- Added `get_service_from_arn()` with documentation
- Backward compatibility aliases for old function names
- Clear note about S3 bucket ARN limitations

### **S3 Support Implementation**

**`services/s3_support.py`** provides complete S3 support:

**ARN Extraction**:
- Method 1: Check `resources[]` array (most events)
- Method 2: Construct from `requestParameters.bucketName` (CreateBucket)

**Resource Description**:
- Cross-account role assumption
- Fetches: location, public access block, versioning, encryption, logging
- Graceful error handling (missing configs don't fail evaluation)

**Inventory Generation**:
- Lists all buckets in account
- Describes each bucket
- Returns list of configurations

### **Service Onboarding Process**

Documented in `README_DEV.md`:

1. Add service to `SUPPORTED_SERVICES` in `common_utils.py`
2. Create `services/<service>_support.py` with required functions
3. Add EventBridge rules in `tools/onboarding/eventbridge-rules.yaml`
4. Create policy evaluators in `lambda/policies/`
5. Add unit tests in `tests/unit/`
6. Add E2E tests in `tests/e2e/`
7. Update documentation

## Files Created

1. **`lambda/services/__init__.py`** - Service registry
2. **`lambda/services/s3_support.py`** - S3 implementation
3. **`lambda/services/ec2_support.py`** - EC2 placeholder
4. **`lambda/services/iam_support.py`** - IAM placeholder
5. **`README_DEV.md`** - Comprehensive developer guide

## Files Modified

1. **`lambda/common_utils.py`**:
   - Added `get_account_from_arn()` and `get_service_from_arn()`
   - Added backward compatibility aliases
   - Improved documentation

2. **`lambda/event_processor/event_handler.py`**:
   - Refactored `_extract_arn_from_event()` to use service registry
   - Refactored `_describe_resource()` to use service registry
   - Removed `_describe_s3_bucket()` (moved to s3_support.py)

3. **`lambda/inventory_generator/inventory_handler.py`**:
   - Refactored `generate_inventory_for_account_service()` to use service registry
   - Removed if/elif chain
   - Generic implementation

4. **`lambda/data_access/inventory_manager.py`**:
   - Removed test-specific hardcoded account ID
   - Uses common_utils ARN functions
   - Proper error handling for S3 buckets

## Benefits

### **Code Organization**
- Service-specific logic isolated in dedicated modules
- No more if/elif chains scattered across codebase
- Clear separation of concerns

### **Maintainability**
- Adding new service requires only creating one new file
- Service implementations are self-contained
- Easy to find and update service-specific code

### **Testability**
- Service modules can be tested in isolation
- Mock AWS clients passed as parameters
- No test-specific code in production modules

### **Extensibility**
- Dynamic service loading via importlib
- No code changes needed in registry when adding services
- Just add to SUPPORTED_SERVICES and create support module

### **Documentation**
- Comprehensive developer guide
- Clear onboarding process for new services
- Architecture diagrams and data flow
- Operational procedures documented

## Testing

### **Unit Tests**
- Existing tests continue to work (backward compatibility)
- Service modules can be tested independently
- Mock clients for AWS API calls

### **E2E Tests**
- Service registry pattern doesn't affect E2E tests
- Tests still trigger real events and verify results

### **Manual Testing**
```bash
# Deploy changes
cd qrie-infra
source .venv/bin/activate
cdk deploy QrieCore --region us-east-1 --profile qop

# Trigger S3 events
BUCKET=qrie-test-$(date +%s)
aws s3 mb s3://$BUCKET
aws s3api put-public-access-block --bucket $BUCKET \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Monitor logs
./tools/debug/monitor-logs.sh event us-east-1 qop

# Verify inventory
aws dynamodb scan --table-name qrie_resources --region us-east-1 --profile qop
```

## Migration Notes

### **Backward Compatibility**
- Old function names (`extract_account_from_arn`, `extract_service_from_arn`) still work
- Existing code doesn't need immediate updates
- Gradual migration recommended

### **Deprecation Plan**
1. **Phase 1** (Current): Both old and new functions available
2. **Phase 2** (Next release): Add deprecation warnings to old functions
3. **Phase 3** (Future): Remove old functions

### **Breaking Changes**
- None! All changes are backward compatible
- Tests may need updates if they relied on test-specific code

## Future Enhancements

### **EC2 Support**
- Implement `ec2_support.py` functions
- Add EventBridge rules for EC2 events
- Create EC2 policy evaluators
- Add E2E tests

### **IAM Support**
- Implement `iam_support.py` functions
- Add EventBridge rules for IAM events
- Create IAM policy evaluators
- Add E2E tests

### **Credential Caching**
- Cache assumed role credentials per account
- Reduce STS API calls
- Implement TTL-based cache (15 minutes)

### **Service Discovery**
- Auto-detect available service modules
- Dynamic SUPPORTED_SERVICES list
- Plugin-style architecture

## Documentation Updates

### **README_DEV.md Sections**
1. **Architecture**: System overview, components, data flow
2. **Code Layout**: Directory structure, design patterns
3. **Local Development**: Setup, unit testing, UI development
4. **QOP Account Setup**: Core stack, UI stack, custom domain
5. **Test Account Setup**: EventBridge rules, IAM role, initial scan
6. **E2E Testing**: Prerequisites, running tests, test flow
7. **Service Onboarding**: Step-by-step guide with examples
8. **Customer Operations**: Onboarding, monitoring, troubleshooting

### **Key Diagrams**
- System architecture with data flow
- Directory structure tree
- Service registry pattern

### **Operational Procedures**
- QOP account deployment
- Customer account onboarding
- Manual scans and monitoring
- Troubleshooting common issues

## Impact

### **Developer Experience**
- Clear guide for new developers
- Easy to onboard new services
- Self-documenting code structure

### **Code Quality**
- No test-specific code in production
- Proper separation of concerns
- Consistent patterns across services

### **Operational Excellence**
- Documented procedures for all operations
- Clear troubleshooting steps
- Monitoring and logging guidance

## Next Steps

1. **Implement EC2 Support**:
   - Create `ec2_support.py` with full implementation
   - Add EventBridge rules
   - Create policy evaluators
   - Add tests

2. **Implement IAM Support**:
   - Create `iam_support.py` with full implementation
   - Add EventBridge rules
   - Create policy evaluators
   - Add tests

3. **Deprecate Legacy Inventory Modules**:
   - Mark `s3_inventory.py`, `ec2_inventory.py`, `iam_inventory.py` as deprecated
   - Migrate remaining code to service support modules
   - Remove legacy modules in future release

4. **Create Service Onboarding Template**:
   - Template files for new services
   - Checklist for onboarding steps
   - Example implementations

## Notes

- Service registry pattern is composition-based (no inheritance)
- All AWS clients accept optional pre-configured client for testing
- Cross-account access uses `QrieInventoryRole` in customer accounts
- Service modules are lazy-loaded (only imported when needed)
- README_DEV.md is the single source of truth for developers
