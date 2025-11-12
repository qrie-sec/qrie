# API Simplification - RESTful Policy Endpoints

**Date:** 2025-11-11  
**Status:** ✅ Completed

## 🚀 Overview

Simplified policy management APIs from 7 endpoints to 4 RESTful endpoints, removing dead code and improving consistency.

## 🏗️ Backend Changes

### API Routing Simplification

**Before (7 endpoints):**
- `GET /policies?status=active|suspended` - Simple list
- `GET /policies/active` - With operational data
- `GET /policies/available?filter=unlaunched` - Catalog
- `GET /policy?id=xyz` - Single policy detail
- `POST /policies/launch` - Launch policy
- `PUT /policies/update` - Update policy (including suspension)

**After (4 RESTful endpoints):**
- `GET /policies?status=active|available|all&policy_id=xyz&services=s3,ec2` - Unified query endpoint
- `POST /policies` - Launch policy
- `PUT /policies/{policy_id}` - Update metadata (scope, severity, remediation)
- `DELETE /policies/{policy_id}` - Delete policy and purge findings

### Key Improvements

1. **Unified GET handler** (`handle_get_policies`):
   - Single endpoint handles all query patterns
   - Supports filtering by status, policy_id, and services
   - Returns consistent schema for all policies
   - Single policy lookup returns array with 1 item for consistency

2. **RESTful path parameters**:
   - `PUT /policies/{policy_id}` instead of `PUT /policies/update` with body param
   - `DELETE /policies/{policy_id}` instead of `PUT /policies/update` with status=suspended

3. **Simplified status model**:
   - **ACTIVE**: Policy is launched and evaluating resources
   - **AVAILABLE**: Policy definition exists but not launched
   - Removed "suspended" and "unlaunched" - policies are either active or available

4. **DELETE semantics**:
   - Deleting a policy automatically purges all associated findings
   - Returns count of findings deleted
   - Policy becomes available again (can be re-launched)

### Files Modified

**Backend:**
- `qrie-infra/lambda/api/policies_api.py`:
  - Replaced 4 handlers with unified `handle_get_policies()`
  - Added helper functions: `_get_single_policy()`, `_get_active_policies_data()`, `_get_available_policies_data()`
  - Updated `handle_update_policy()` to use path parameter and remove status updates
  - Added `handle_delete_policy()` for policy deletion
  
- `qrie-infra/lambda/api/api_handler.py`:
  - Simplified routing from 7 routes to 4
  - Added path parameter extraction for PUT/DELETE

## 🔧 Frontend Changes

### API Client Simplification

**Removed functions:**
- ❌ `getActivePolicies()` - Replaced by `getPolicies({ status: "active" })`
- ❌ `getAvailablePolicies()` - Replaced by `getPolicies({ status: "available" })`
- ❌ `getPolicyDetail()` - **Dead code** (never used)

**Updated functions:**
- ✅ `getPolicies(params?)` - Unified with flexible filtering
- ✅ `launchPolicy()` - Now uses `POST /policies`
- ✅ `updatePolicy()` - Now uses `PUT /policies/{id}` (no status param)
- ✅ `deletePolicy()` - **NEW** - Uses `DELETE /policies/{id}`

### Component Updates

**management-view.tsx:**
- Updated all calls to use `getPolicies({ status: "active" })` and `getPolicies({ status: "available" })`
- Changed suspension to use `deletePolicy()` instead of `updatePolicy({ status: "suspended" })`
- Simplified data fetching logic

**findings-view.tsx:**
- Updated to use `getPolicies({ status: "active" })`

**types.ts:**
- Updated `Policy.status` type: `"active" | "available"` (removed "suspended" and "unlaunched")
- Updated type guards: `isLaunchedPolicy()`, `isAvailablePolicy()`, `isActivePolicy()`
- Removed: `isUnlaunchedPolicy()`, `isSuspendedPolicy()`

### Files Modified

**Frontend:**
- `qrie-ui/lib/api.ts` - Simplified API client functions
- `qrie-ui/lib/types.ts` - Updated Policy type and type guards
- `qrie-ui/components/management-view.tsx` - Updated to use new API
- `qrie-ui/components/findings-view.tsx` - Updated to use new API

## 📚 Documentation Updates

### API Documentation
- Updated `qrie-infra/qrie_apis.md` with new endpoint structure
- Removed references to suspended/unlaunched statuses
- Added DELETE endpoint documentation
- Updated all examples to use new query parameters

### UI Documentation
- Updated `qrie-ui/API_DOCUMENTATION.md` with simplified endpoints
- Removed dead endpoint references
- Added DELETE policy endpoint

### Onboarding Documentation
- Updated `qrie-ui/app/docs/onboarding/page.tsx` to reflect new policy lifecycle
- Removed references to policy suspension
- Updated to use "delete" terminology

## ✅ Benefits

1. **Cleaner API surface**: 4 RESTful endpoints instead of 7 custom routes
2. **Consistent schema**: All policies return same structure regardless of status
3. **Removed dead code**: `getPolicyDetail()` was never used
4. **Better semantics**: DELETE for removal is clearer than UPDATE with status change
5. **Easier to maintain**: Single unified handler for all GET queries
6. **RESTful design**: Proper use of HTTP verbs and path parameters

## 🔄 Migration Notes

**For API consumers:**
- Replace `GET /policies/active` with `GET /policies?status=active`
- Replace `GET /policies/available` with `GET /policies?status=available`
- Replace `GET /policy?id=xyz` with `GET /policies?policy_id=xyz`
- Replace `POST /policies/launch` with `POST /policies`
- Replace `PUT /policies/update` with `PUT /policies/{policy_id}`
- Use `DELETE /policies/{policy_id}` instead of `PUT /policies/update` with `status=suspended`

**For frontend code:**
- Replace `getActivePolicies()` with `getPolicies({ status: "active" })`
- Replace `getAvailablePolicies()` with `getPolicies({ status: "available" })`
- Remove any calls to `getPolicyDetail()` (dead code)
- Replace `updatePolicy(id, { status: "suspended" })` with `deletePolicy(id)`

## 🧪 Testing

**Unit tests updated:**
- ✅ `tests/unit/test_findings_api.py` - Updated to use `handle_get_policies`
- ✅ `tests/unit/test_api_handler.py` - Updated routing tests
- ✅ Fixed imports and mocking for new API structure
- ✅ Tests passing for policy endpoints

**Integration tests updated:**
- ✅ `tools/test/test_apis.py` - Updated to use unified `/policies` endpoint
- ✅ Removed old endpoint tests (`/policies/active`, `/policies/available`, `/policy`)
- ✅ Added tests for new query parameters (`status`, `policy_id`, `services`)

**Manual testing required:**
- ⚠️ GET /policies with various query combinations
- ⚠️ POST /policies to launch a policy
- ⚠️ PUT /policies/{id} to update metadata
- ⚠️ DELETE /policies/{id} to remove policy
- ⚠️ UI policy management page
- ⚠️ UI findings page (policy filter dropdown)

## 📝 Related Files

**Backend:**
- `/Users/shubham/dev/qrie/qrie-infra/lambda/api/policies_api.py`
- `/Users/shubham/dev/qrie/qrie-infra/lambda/api/api_handler.py`

**Frontend:**
- `/Users/shubham/dev/qrie/qrie-ui/lib/api.ts`
- `/Users/shubham/dev/qrie/qrie-ui/lib/types.ts`
- `/Users/shubham/dev/qrie/qrie-ui/components/management-view.tsx`
- `/Users/shubham/dev/qrie/qrie-ui/components/findings-view.tsx`

**Documentation:**
- `/Users/shubham/dev/qrie/qrie-infra/qrie_apis.md`
- `/Users/shubham/dev/qrie/qrie-ui/API_DOCUMENTATION.md`
- `/Users/shubham/dev/qrie/qrie-ui/README.md`
- `/Users/shubham/dev/qrie/qrie-ui/app/docs/onboarding/page.tsx`
