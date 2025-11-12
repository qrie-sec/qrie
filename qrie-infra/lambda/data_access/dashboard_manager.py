"""Dashboard Manager - Aggregates data from other managers for dashboard summaries with lazy refresh caching."""
import os
import sys
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from botocore.exceptions import ClientError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common_utils import get_summary_table
from common.logger import debug, info, error
from data_access.policy_manager import PolicyManager
from data_access.findings_manager import FindingsManager
from data_access.inventory_manager import InventoryManager


class DashboardManager:
    """Manages dashboard summary data aggregation with lazy refresh caching"""
    
    def __init__(self):
        self.table = get_summary_table()
        self.policy_manager = PolicyManager()
        self.findings_manager = FindingsManager()
        self.inventory_manager = InventoryManager()
    
    def get_dashboard_summary(self, date: str) -> Dict:
        """
        Get dashboard summary - lazy refresh if stale.
        Uses 1-hour cache with distributed locking to prevent thundering herd.
        """
        # Try to get cached summary
        cached = self._get_cached_summary()
        
        if cached and self._is_fresh(cached, max_age_hours=1):
            debug(f"Serving cached dashboard summary from {cached['updated_at']}")
            return cached['summary']
        
        debug("Cache miss or stale, computing fresh dashboard summary")
        
        # Simple lock to prevent thundering herd
        lock_acquired = self._try_acquire_lock(ttl_seconds=60)
        
        if not lock_acquired:
            # Another process is refreshing, serve stale data if available
            if cached:
                debug("Serving stale data while refresh in progress")
                return cached['summary']
            # Wait and retry
            debug("Waiting for concurrent refresh to complete...")
            time.sleep(2)
            cached = self._get_cached_summary()
            if cached:
                return cached['summary']
            # Still no data, proceed anyway (lock may have expired)
        
        # Compute fresh summary
        summary = self._compute_summary(date)
        
        # Cache it
        self._save_summary(summary)
        
        # Release lock
        if lock_acquired:
            self._release_lock()
        
        return summary
    
    def _get_cached_summary(self) -> Optional[Dict]:
        """Get cached dashboard summary from DynamoDB"""
        try:
            response = self.table.get_item(Key={'Type': 'dashboard'})
            item = response.get('Item')
            if item:
                # Convert Decimals from DynamoDB to native Python types
                item['summary'] = self._convert_decimals(item['summary'])
            return item
        except Exception as e:
            error(f"Error getting cached summary: {e}")
            return None
    
    def _is_fresh(self, cached: Dict, max_age_hours: int) -> bool:
        """Check if cached data is fresh enough"""
        try:
            updated_at = datetime.fromisoformat(cached['updated_at'].replace('Z', '+00:00'))
            age = datetime.now(timezone.utc) - updated_at
            return age.total_seconds() < (max_age_hours * 3600)
        except Exception as e:
            error(f"Error checking cache freshness: {e}")
            return False
    
    def _try_acquire_lock(self, ttl_seconds: int) -> bool:
        """Try to acquire refresh lock using DynamoDB conditional write"""
        try:
            self.table.put_item(
                Item={
                    'Type': 'dashboard_refresh_lock',
                    'expires_at': int(time.time()) + ttl_seconds
                },
                ConditionExpression='attribute_not_exists(#type) OR #expires < :now',
                ExpressionAttributeNames={'#type': 'Type', '#expires': 'expires_at'},
                ExpressionAttributeValues={':now': int(time.time())}
            )
            debug("Acquired refresh lock")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                debug("Failed to acquire lock - another process is refreshing")
                return False
            error(f"Error acquiring lock: {e}")
            return False
    
    def _release_lock(self) -> None:
        """Release refresh lock"""
        try:
            self.table.delete_item(Key={'Type': 'dashboard_refresh_lock'})
            debug("Released refresh lock")
        except Exception as e:
            error(f"Error releasing lock: {e}")
    
    def _save_summary(self, summary: Dict) -> None:
        """Save dashboard summary to DynamoDB"""
        try:
            # Convert to ensure no Decimals before saving
            clean_summary = self._convert_decimals(summary)
            self.table.put_item(Item={
                'Type': 'dashboard',
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'summary': clean_summary
            })
            debug("Saved dashboard summary to cache")
        except Exception as e:
            error(f"Error saving summary: {e}")
    
    def _compute_summary(self, date: str) -> Dict:
        """
        Compute dashboard summary from live data using table scans.
        No GSI required - table scans are cost-effective for MVP scale.
        """
        info("Computing dashboard summary from live data...")
        
        # Get basic counts
        active_policies = len(self.policy_manager.list_launched_policies(status_filter='active'))
        
        resources_summary = self.inventory_manager.get_resources_summary()
        total_resources = resources_summary['total_resources']
        total_accounts = resources_summary['total_accounts']
        
        findings_summary = self.findings_manager.get_findings_summary()
        total_open_findings = findings_summary['open_findings']
        critical_open_findings = findings_summary['critical_findings']
        high_open_findings = findings_summary['high_findings']
        
        # Get weekly metrics using table scans with date filters
        findings_weekly = self._compute_weekly_findings()
        
        # Get resolved findings this month
        resolved_this_month = self._count_resolved_this_month()
        
        # Get top policies by open findings
        top_policies = self._compute_top_policies(findings_summary)
        
        # Get policies launched this month
        policies_launched_this_month = self._count_policies_launched_this_month()
        
        # Get anti-entropy metrics (last scan times and drift detection)
        anti_entropy_metrics = self._get_anti_entropy_metrics()
        
        info(f"Computed summary: {total_open_findings} open, {critical_open_findings} critical, "
              f"{high_open_findings} high, {resolved_this_month} resolved this month, {active_policies} active policies")
        
        return {
            # Current counts
            'total_open_findings': total_open_findings,
            'critical_open_findings': critical_open_findings,
            'high_open_findings': high_open_findings,
            'resolved_this_month': resolved_this_month,
            'active_policies': active_policies,
            'resources': total_resources,
            'accounts': total_accounts,
            
            # Weekly trends
            'findings_weekly': findings_weekly,
            
            # Top policies
            'top_policies': top_policies,
            
            # Anti-entropy metrics
            'anti_entropy': anti_entropy_metrics,
            
            # Month metrics
            'policies_launched_this_month': policies_launched_this_month
        }
    
    def _compute_weekly_findings(self) -> List[Dict]:
        """
        Compute weekly findings metrics for last 8 weeks using table scans.
        Scans findings table with date filters - no GSI needed for MVP.
        """
        weekly_data = []
        now = datetime.now(timezone.utc)
        
        # Get all findings with timestamps for analysis
        all_findings = self._scan_all_findings_with_dates()
        
        # Compute metrics for each of the last 8 weeks
        for week_offset in range(8):
            week_start = now - timedelta(weeks=week_offset)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start -= timedelta(days=week_start.weekday())  # Start of week (Monday)
            week_end = week_start + timedelta(days=7)
            
            # Count findings for this week
            new_findings = 0
            closed_findings = 0
            critical_new = 0
            open_findings_snapshot = 0
            
            for finding in all_findings:
                first_seen = finding.get('first_seen_dt')
                last_evaluated = finding.get('last_evaluated_dt')
                state = finding.get('state')
                severity = finding.get('severity', 0)
                
                # New findings this week
                if first_seen and week_start <= first_seen < week_end:
                    new_findings += 1
                    if severity >= 90:
                        critical_new += 1
                
                # Closed findings this week
                if state == 'RESOLVED' and last_evaluated and week_start <= last_evaluated < week_end:
                    closed_findings += 1
                
                # Open findings at end of week (snapshot)
                if state == 'ACTIVE' and first_seen and first_seen < week_end:
                    # Was created before week end and still active
                    if not last_evaluated or last_evaluated < week_end or state == 'ACTIVE':
                        open_findings_snapshot += 1
            
            weekly_data.insert(0, {  # Insert at beginning for chronological order
                'week_start': week_start.strftime('%Y-%m-%d'),
                'total_findings': len([f for f in all_findings if f.get('first_seen_dt') and f['first_seen_dt'] < week_end]),
                'open_findings': open_findings_snapshot,
                'new_findings': new_findings,
                'closed_findings': closed_findings,
                'critical_new': critical_new,
                'is_current': week_offset == 0
            })
        
        return weekly_data
    
    def _scan_all_findings_with_dates(self) -> List[Dict]:
        """Scan all findings and parse dates for analysis"""
        findings = []
        
        try:
            response = self.findings_manager.table.scan(
                ProjectionExpression='FirstSeen, LastEvaluated, #state, Severity',
                ExpressionAttributeNames={'#state': 'State'}
            )
            
            for item in response.get('Items', []):
                try:
                    finding_data = {
                        'state': item.get('State'),
                        'severity': int(item.get('Severity', 0)) if item.get('Severity') is not None else 0
                    }
                    
                    # Parse dates
                    if item.get('FirstSeen'):
                        finding_data['first_seen_dt'] = datetime.fromisoformat(
                            item['FirstSeen'].replace('Z', '+00:00')
                        )
                    
                    if item.get('LastEvaluated'):
                        finding_data['last_evaluated_dt'] = datetime.fromisoformat(
                            item['LastEvaluated'].replace('Z', '+00:00')
                        )
                    
                    findings.append(finding_data)
                except Exception as e:
                    error(f"Error parsing finding dates: {e}")
                    continue
            
        except Exception as e:
            error(f"Error scanning findings: {e}")
        
        return findings
    
    def _compute_top_policies(self, findings_summary: Dict) -> List[Dict]:
        """Get top 10 policies by open findings count"""
        policies = findings_summary.get('policies', [])
        
        # Sort by open findings and take top 10
        top_policies = sorted(
            [p for p in policies if p.get('open_findings', 0) > 0],
            key=lambda x: x.get('open_findings', 0),
            reverse=True
        )[:10]
        
        # Get severity for each policy
        result = []
        for policy_data in top_policies:
            policy_id = policy_data['policy']
            policy_def = self.policy_manager.get_policy_definition(policy_id)
            
            result.append({
                'policy_id': policy_id,
                'open_findings': policy_data['open_findings'],
                'severity': policy_def.severity if policy_def else 50
            })
        
        return result
    
    def _count_resolved_this_month(self) -> int:
        """Count findings resolved in the current month"""
        try:
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Scan findings table for resolved findings
            findings = self._scan_all_findings_with_dates()
            
            count = 0
            for finding in findings:
                if finding.get('state') == 'RESOLVED':
                    last_evaluated = finding.get('last_evaluated_dt')
                    if last_evaluated and last_evaluated >= month_start:
                        count += 1
            
            return count
        except Exception as e:
            error(f"Error counting resolved findings this month: {e}")
            return 0
    
    def _count_policies_launched_this_month(self) -> int:
        """Count policies launched in the current month"""
        try:
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_start_str = month_start.strftime('%Y-%m-%d')
            
            all_policies = self.policy_manager.list_launched_policies(status_filter='active')
            
            count = 0
            for policy in all_policies:
                if policy.created_at and policy.created_at >= month_start_str:
                    count += 1
            
            return count
        except Exception as e:
            error(f"Error counting policies launched this month: {e}")
            return 0
    
    def _get_anti_entropy_metrics(self) -> Dict:
        """
        Get anti-entropy metrics from summary table.
        Includes last inventory scan, last policy scan, and drift detection.
        """
        try:
            # Get last inventory scan metrics
            inventory_scan = self.table.get_item(Key={'Type': 'last_inventory_scan'}).get('Item', {})
            
            # Get last policy scan metrics
            policy_scan = self.table.get_item(Key={'Type': 'last_policy_scan'}).get('Item', {})
            
            # Calculate drift (time since last scans)
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            
            inventory_age_hours = None
            policy_age_hours = None
            drift_detected = False
            
            if inventory_scan.get('timestamp_ms'):
                inventory_age_ms = now_ms - int(inventory_scan['timestamp_ms'])
                inventory_age_hours = inventory_age_ms / (1000 * 60 * 60)
                # Drift if inventory scan is > 8 days old (weekly + 1 day buffer)
                if inventory_age_hours > 24 * 8:
                    drift_detected = True
            
            if policy_scan.get('timestamp_ms'):
                policy_age_ms = now_ms - int(policy_scan['timestamp_ms'])
                policy_age_hours = policy_age_ms / (1000 * 60 * 60)
                # Drift if policy scan is > 26 hours old (daily + 2 hour buffer)
                if policy_age_hours > 26:
                    drift_detected = True
            
            return {
                'last_inventory_scan': {
                    'scan_id': inventory_scan.get('scan_id'),
                    'timestamp_ms': inventory_scan.get('timestamp_ms'),
                    'age_hours': round(inventory_age_hours, 1) if inventory_age_hours else None,
                    'duration_ms': inventory_scan.get('duration_ms'),
                    'resources_found': inventory_scan.get('resources_found', 0)
                },
                'last_policy_scan': {
                    'scan_id': policy_scan.get('scan_id'),
                    'timestamp_ms': policy_scan.get('timestamp_ms'),
                    'age_hours': round(policy_age_hours, 1) if policy_age_hours else None,
                    'duration_ms': policy_scan.get('duration_ms'),
                    'processed_resources': policy_scan.get('processed_resources', 0),
                    'findings_created': policy_scan.get('findings_created', 0),
                    'findings_closed': policy_scan.get('findings_closed', 0)
                },
                'drift_detected': drift_detected
            }
        except Exception as e:
            error(f"Error getting anti-entropy metrics: {e}\n{traceback.format_exc()}")
            return {
                'last_inventory_scan': {},
                'last_policy_scan': {},
                'drift_detected': False
            }
    
    def _convert_decimals(self, obj):
        """Recursively convert Decimal objects to int/float for JSON serialization"""
        if isinstance(obj, Decimal):
            # Convert Decimal to int if it's a whole number, otherwise float
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        else:
            return obj
