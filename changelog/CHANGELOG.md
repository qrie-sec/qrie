# Changelog

All notable changes to the qrie project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

See dated changelog files for detailed changes:
- [2025-10-30: Inventory Summary Caching](2025-10-30-inventory-caching.md)
- [2025-10-16: Dashboard Charts & Policy Management](2025-10-16.md)
- [2025-10-15: Unified Policy Model](2025-10-15-unified-policy-model.md)
- [2025-10-14: Architecture & Core Features](2025-10-14.md)

### Added
- **Enhanced Dashboard with Weekly Trends**
  - Added `qrie_summary` DynamoDB table for caching dashboard and other summaries
  - Implemented lazy refresh strategy with 1-hour cache and distributed locking
  - Added 8-week historical trends for findings (new, closed, open, critical)
  - Added top 10 policies by open findings count with severity
  - Added policies launched this month metric
  - Dashboard now shows Open/Critical/High/Resolved metrics

- **Findings Summary with Caching**
  - Added 15-minute caching for findings summary (lazy refresh pattern)
  - Backend calculates severity breakdowns: critical (>=90), high (50-89), medium (25-49), low (0-24)
  - Per-policy breakdown includes severity and resolved_findings from backend
  - Findings view shows High/Critical/Open/Resolved in grid layout

- **Inventory Summary with Caching and Findings Integration**
  - Added 15-minute caching for inventory summary (same pattern as findings)
  - Integrated findings data: now returns `total_findings`, `critical_findings`, `high_findings`
  - Calculates `non_compliant` count per resource type (resources with ACTIVE findings)
  - Fixed field names: returns `resource_type` and `all_resources` (matches TypeScript interface)
  - Supports per-account filtering with separate cache keys
  - Uses distributed locking to prevent concurrent refreshes
  
- **Cost-Optimized Architecture**
  - Uses table scans instead of GSI for dashboard metrics (cost-effective for MVP scale)
  - Lazy refresh on first read after cache expiry (no scheduled Lambda overhead)
  - Distributed lock using DynamoDB conditional writes prevents thundering herd
  - Estimated cost: ~$0.00005/month for 3 scans/day at 10K findings scale

### Changed
- **Dashboard API Response Structure**
  - `GET /summary/dashboard` now returns comprehensive weekly trends and top policies
  - Replaced `total_findings` with `total_open_findings`, `high_open_findings`, and `resolved_this_month`
  - Added `findings_weekly` array with 8 weeks of historical data
  - Added `top_policies` array with top 10 policies by open findings
  - Added `policies_launched_this_month` count
  - Removed deprecated fields: `opened_this_week`, `closed_this_week`, `opened_last_week`, `closed_last_week`, `risk_score`, `risk_score_trend`

- **Dashboard UI Improvements**
  - Replaced "Total Findings" card with "Resolved This Month" card
  - Added "High Open" card showing findings with severity 50-89
  - "Open Findings" card shows current open with new this week
  - "Critical Open" card shows critical count with new critical this week
  - Findings trend chart now uses real weekly data instead of simulated data
  - Top policies chart now uses data from dashboard summary (single API call)

- **Findings View UI Improvements**
  - Risk Summary now shows High/Critical/Open/Resolved in 2x2 grid layout
  - Removed "Total" metric (clarified that "Open" means total open findings)
  - Added "Updates every 15 min" footnote for cache transparency
  - Both all-accounts and per-account views use consistent grid layout

- **TypeScript Type Updates**
  - Added `WeeklyFindings` interface for weekly trend data
  - Added `TopPolicy` interface for top policies data
  - Updated `DashboardSummary` interface: replaced `total_findings` with `high_open_findings` and `resolved_this_month`
  - Updated `FindingsSummary` interface: added `high_findings`, `medium_findings`, `low_findings`, `resolved_findings`
  - Added `severity` and `resolved_findings` to policy breakdown in findings summary
  - `ResourcesSummary` interface now correctly matches backend response (no changes needed - was already correct)
  - Removed duplicate `Policy` interface definition

### Technical Details
- **Infrastructure**: Added `qrie_summary` table to `core_stack.py` with read/write permissions for API Lambda (generic table for caching dashboard, findings summaries, etc.)
- **Backend**: 
  - Completely rewrote `dashboard_manager.py` with lazy refresh, caching, and weekly metrics computation
  - Added `_count_resolved_this_month()` method to count findings resolved in current month
  - Enhanced `findings_manager.py` with 15-minute caching and severity breakdown calculations
  - Added `_compute_findings_summary()` with proper severity ranges and resolved counts
  - Enhanced `inventory_manager.py` with 15-minute caching and findings integration
  - Added `_compute_resources_summary()` that queries both resources and findings tables
  - Added cache helper methods: `_get_cached_summary()`, `_is_fresh()`, `_try_acquire_lock()`, `_release_lock()`, `_save_summary()`, `_convert_decimals()`
  - Fixed `count_resources_by_type()` to use correct field names from cached summary
- **Frontend**: 
  - Updated `dashboard-view.tsx` to show Open/Critical/High/Resolved cards
  - Updated `findings-view.tsx` to show High/Critical/Open/Resolved in grid layout
  - Updated `findings-trend-chart.tsx`, `top-policies-chart.tsx` to use new data structure
  - Updated `inventory-view.tsx` to add "Updates every 15 min" footnote (consistency with findings)
- **Documentation**: Updated `qrie_apis.md` with comprehensive dashboard API documentation including caching strategy and implementation notes
- **Testing**:
  - Added comprehensive test suite for inventory caching: `test_inventory_manager_caching.py`
  - Tests cover: cache hit/miss, findings integration, non-compliant counts, per-account filtering, cache expiry
  - All tests passing with 100% coverage of new caching code

### Performance
- Dashboard loads from 1-hour cache (instant response)
- Findings summary loads from 15-minute cache (instant response)
- Inventory summary loads from 15-minute cache (instant response)
- First request after cache expiry triggers refresh (~2-3 seconds)
- Concurrent requests during refresh serve stale data (no blocking)
- Table scans complete in <1 second for typical MVP scale (10K findings, 10K resources)
- **Inventory improvement**: 96% reduction in DynamoDB scans (from ~2,400/day to ~96/day)

### Migration Notes
- Requires `cdk deploy QrieCore` to create new `qrie_summary` table
- UI automatically adapts to new API response structure
- No data migration required - cache builds on first request
- Backward compatible - old dashboard data is not used

---

## [Previous Releases]

_Previous changes will be documented here as releases are tagged._
