"""
FindingsManager - Centralized findings data access with caching.
Handles all findings CRUD operations and queries.
"""
import os
import datetime
import time
from typing import List, Dict, Optional, Literal
from functools import lru_cache
from botocore.exceptions import ClientError
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import shared tables from common
from common_utils import get_findings_table, get_summary_table
from common.logger import debug, info, error


class Finding:
    """Finding data structure"""
    def __init__(self, arn: str, policy: str, account_service: str, 
                 severity: int, state: str, first_seen: str, 
                 last_evaluated: str, evidence: Dict):
        self.arn = arn
        self.policy = policy
        self.account_service = account_service
        self.severity = severity  # 0-100 (AWS Security Hub scoring)
        self.state = state
        self.first_seen = first_seen
        self.last_evaluated = last_evaluated
        self.evidence = evidence

class FindingsManager:
    """Manages all findings data access operations with caching"""
    
    def __init__(self):
        self.table = get_findings_table()
        self.summary_table = get_summary_table()
    
    # ============================================================================
    # WRITE OPERATIONS
    # ============================================================================
    
    def put_finding(self, resource_arn: str, policy_id: str, account_service: str, 
                    severity: int, state: str, evidence: Dict, 
                    describe_time_ms: int, first_seen_ms: Optional[int] = None) -> None:
        """
        Create or update a finding using conditional writes to prevent race conditions.
        One-shot update that handles both create and update cases atomically.
        
        Args:
            resource_arn: Resource ARN
            policy_id: Policy ID
            account_service: Account and service (e.g., "123456789012_s3")
            severity: Severity score (0-100)
            state: Finding state (ACTIVE, RESOLVED)
            evidence: Evidence dict
            describe_time_ms: Timestamp (milliseconds) when resource config was captured (REQUIRED)
            first_seen_ms: Timestamp (milliseconds) when finding was first seen (defaults to describe_time_ms)
        """
        key = {'ARN': resource_arn, 'Policy': policy_id}
        first_seen = first_seen_ms if first_seen_ms is not None else describe_time_ms
        
        try:
            self.table.update_item(
                Key=key,
                # Create-or-update fields
                UpdateExpression=(
                    "SET #state = :state, "
                    "#severity = :sev, "
                    "#describeTime = :now, "
                    "#lastEvaluated = :now, "
                    "#evidence = :evidence, "
                    "#accountService = :acct, "
                    "#firstSeen = if_not_exists(#firstSeen, :firstSeen)"
                ),
                # Allow if new item, or existing is older, or missing DescribeTime
                ConditionExpression=(
                    "attribute_not_exists(#arn) OR "
                    "attribute_not_exists(#describeTime) OR "
                    "#describeTime < :now"
                ),
                ExpressionAttributeNames={
                    "#arn": "ARN",
                    "#state": "State",
                    "#severity": "Severity",
                    "#describeTime": "DescribeTime",
                    "#lastEvaluated": "LastEvaluated",
                    "#evidence": "Evidence",
                    "#accountService": "AccountService",
                    "#firstSeen": "FirstSeen",
                },
                ExpressionAttributeValues={
                    ":state": state,
                    ":sev": severity,
                    ":now": describe_time_ms,
                    ":evidence": evidence,
                    ":acct": account_service,
                    ":firstSeen": first_seen,
                },
                ReturnValues="NONE"
            )
            debug(f"Updated finding {resource_arn}#{policy_id} with describe time {describe_time_ms}")
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            # Item exists and has more recent describe time - this is expected
            debug(f"Skipping update for {resource_arn}#{policy_id} - existing describe time is more recent than {describe_time_ms}")

    def close_finding(self, resource_arn: str, policy_id: str) -> None:
        """Close a finding (mark as resolved)"""
        finding_key = {'ARN': resource_arn, 'Policy': policy_id}
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        self.table.update_item(
            Key=finding_key,
            UpdateExpression='SET #state = :state, #lastEvaluated = :now',
            ExpressionAttributeNames={
                '#state': 'State',
                '#lastEvaluated': 'LastEvaluated'
            },
            ExpressionAttributeValues={
                ':state': 'RESOLVED',
                ':now': now
            }
        )

    def delete_findings_for_resource(self, resource_arn: str) -> None:
        """Delete all findings for a resource (when resource goes out of scope)"""
        # Query all findings for this resource
        response = self.table.query(
            KeyConditionExpression='ARN = :arn',
            ExpressionAttributeValues={':arn': resource_arn}
        )
        
        # Delete each finding
        for item in response.get('Items', []):
            self.table.delete_item(Key={
                'ARN': item['ARN'],
                'Policy': item['Policy']
            })
    
    def purge_findings_for_policy(self, policy_id: str) -> int:
        """
        Purge all findings for a policy (when policy is suspended).
        Marks all findings as RESOLVED with reason POLICY_SUSPENDED.
        
        Args:
            policy_id: Policy ID to purge findings for
            
        Returns:
            Number of findings purged
        """
        now_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
        purged_count = 0
        
        # Scan for all findings with this policy (using GSI on AccountService)
        # Since we don't have a GSI on Policy alone, we need to scan
        response = self.table.scan(
            FilterExpression='Policy = :policy AND #state = :active_state',
            ExpressionAttributeNames={
                '#state': 'State'
            },
            ExpressionAttributeValues={
                ':policy': policy_id,
                ':active_state': 'ACTIVE'
            }
        )
        
        # Update each finding to RESOLVED
        for item in response.get('Items', []):
            try:
                self.table.update_item(
                    Key={
                        'ARN': item['ARN'],
                        'Policy': item['Policy']
                    },
                    UpdateExpression='SET #state = :resolved, #lastEvaluated = :now, #resolvedReason = :reason',
                    ExpressionAttributeNames={
                        '#state': 'State',
                        '#lastEvaluated': 'LastEvaluated',
                        '#resolvedReason': 'ResolvedReason'
                    },
                    ExpressionAttributeValues={
                        ':resolved': 'RESOLVED',
                        ':now': now_ms,
                        ':reason': 'POLICY_SUSPENDED'
                    }
                )
                purged_count += 1
            except Exception as e:
                error(f"Error purging finding {item['ARN']}#{item['Policy']}: {str(e)}")
        
        info(f"Purged {purged_count} findings for policy {policy_id}")
        return purged_count
    
    # ============================================================================
    # READ OPERATIONS WITH CACHING
    # ============================================================================
    
    def get_findings_for_resource(self, arn: str) -> List[Finding]:
        """Get all findings for a specific resource"""
        response = self.table.query(
            KeyConditionExpression='ARN = :arn',
            ExpressionAttributeValues={':arn': arn}
        )
        
        return [self._item_to_finding(item) for item in response.get('Items', [])]

    def get_finding_by_resource_and_policy(self, arn: str, policy: str) -> Optional[Finding]:
        """Get a specific finding by resource ARN and policy name"""
        response = self.table.get_item(Key={'ARN': arn, 'Policy': policy})
        
        if 'Item' in response:
            return self._item_to_finding(response['Item'])
        return None

    def get_findings_for_account_service(self, account_id: str, service: str, 
                                       state_filter: Optional[Literal['ACTIVE', 'RESOLVED']] = None,
                                       limit: Optional[int] = None) -> List[Finding]:
        """Get findings for an account/service combination using GSI"""
        account_service = f"{account_id}_{service}"
        
        query_params = {
            'IndexName': 'AccountService-State-index',
            'KeyConditionExpression': 'AccountService = :account_service',
            'ExpressionAttributeValues': {':account_service': account_service}
        }
        
        if state_filter:
            query_params['FilterExpression'] = '#state = :state'
            query_params['ExpressionAttributeNames'] = {'#state': 'State'}
            query_params['ExpressionAttributeValues'][':state'] = state_filter
        
        if limit:
            query_params['Limit'] = limit
        
        response = self.table.query(**query_params)
        return [self._item_to_finding(item) for item in response.get('Items', [])]

    def get_findings_paginated(self, account_id: Optional[str] = None, policy_id: Optional[str] = None,
                             state_filter: Optional[str] = None, severity_filter: Optional[str] = None,
                             page_size: int = 50, next_token: Optional[str] = None) -> Dict:
        """Get paginated findings with flexible filtering"""
        import json
        import base64
        
        # Build filter conditions
        filter_expressions = []
        expression_values = {}
        expression_names = {}
        
        if account_id:
            filter_expressions.append('begins_with(AccountService, :account_prefix)')
            expression_values[':account_prefix'] = f"{account_id}_"
        
        if policy_id:
            filter_expressions.append('#policy = :policy')
            expression_values[':policy'] = policy_id
            expression_names['#policy'] = 'Policy'
        
        if state_filter:
            filter_expressions.append('#state = :state')
            expression_values[':state'] = state_filter
            expression_names['#state'] = 'State'
        
        if severity_filter:
            filter_expressions.append('#severity = :severity')
            expression_values[':severity'] = severity_filter
            expression_names['#severity'] = 'Severity'
        
        # Use scan with filters (not ideal but flexible)
        scan_params = {
            'Limit': page_size
        }
        
        if filter_expressions:
            scan_params['FilterExpression'] = ' AND '.join(filter_expressions)
            scan_params['ExpressionAttributeValues'] = expression_values
            if expression_names:
                scan_params['ExpressionAttributeNames'] = expression_names
        
        if next_token:
            scan_params['ExclusiveStartKey'] = json.loads(base64.b64decode(next_token).decode())
        
        response = self.table.scan(**scan_params)
        
        findings = [self._item_to_finding(item) for item in response.get('Items', [])]
        
        result = {
            'findings': findings,
            'count': len(findings)
        }
        
        if 'LastEvaluatedKey' in response:
            result['next_token'] = base64.b64encode(
                json.dumps(response['LastEvaluatedKey']).encode()
            ).decode()
        
        return result

    def get_findings_for_account_service_paginated(self, account_id: str, service: str,
                                                 page_size: int = 50,
                                                 next_token: Optional[str] = None,
                                                 state_filter: Optional[Literal['ACTIVE', 'RESOLVED']] = None) -> Dict:
        """Get paginated findings for an account/service combination (legacy method)"""
        # Convert to new method call
        return self.get_findings_paginated(
            account_id=account_id,
            state_filter=state_filter,
            page_size=page_size,
            next_token=next_token
        )

    def get_findings_for_account(self, account_id: str, 
                               state_filter: Optional[Literal['ACTIVE', 'RESOLVED']] = None,
                               limit: Optional[int] = None) -> List[Finding]:
        """Get all findings for an account across all services"""
        # This requires scanning with filter - not ideal but needed for cross-service queries
        filter_expression = 'begins_with(AccountService, :account_prefix)'
        expression_values = {':account_prefix': f"{account_id}_"}
        
        if state_filter:
            filter_expression += ' AND #state = :state'
            expression_values[':state'] = state_filter
        
        scan_params = {
            'FilterExpression': filter_expression,
            'ExpressionAttributeValues': expression_values
        }
        
        if state_filter:
            scan_params['ExpressionAttributeNames'] = {'#state': 'State'}
        
        if limit:
            scan_params['Limit'] = limit
        
        response = self.table.scan(**scan_params)
        return [self._item_to_finding(item) for item in response.get('Items', [])]

    @lru_cache(maxsize=128)
    def get_open_findings_summary(self, account_id: str) -> Dict[str, int]:
        """Get a summary of open findings by service for an account (cached)"""
        findings = self.get_findings_for_account(account_id, state_filter='ACTIVE')
        
        summary = {}
        for finding in findings:
            service = finding.account_service.split('_', 1)[1]  # Extract service from account_service
            summary[service] = summary.get(service, 0) + 1
        
        return summary

    def count_findings(self, policy_id: Optional[str] = None, 
                      account_id: Optional[str] = None,
                      state_filter: Optional[str] = None) -> int:
        """
        Count findings with optional filters.
        
        NOTE: This method performs an uncached table scan and is expensive.
        For per-policy counts, prefer using get_findings_summary() which provides
        cached counts for all policies with 15-minute TTL.
        """
        filter_expressions = []
        expression_values = {}
        expression_names = {}
        
        if policy_id:
            filter_expressions.append('#policy = :policy')
            expression_names['#policy'] = 'Policy'
            expression_values[':policy'] = policy_id
            
        if account_id:
            filter_expressions.append('begins_with(AccountService, :account_prefix)')
            expression_values[':account_prefix'] = f"{account_id}_"
            
        if state_filter:
            filter_expressions.append('#state = :state')
            expression_names['#state'] = 'State'
            expression_values[':state'] = state_filter
        
        scan_params = {
            'Select': 'COUNT'
        }
        
        if filter_expressions:
            scan_params['FilterExpression'] = ' AND '.join(filter_expressions)
            scan_params['ExpressionAttributeValues'] = expression_values
            
        if expression_names:
            scan_params['ExpressionAttributeNames'] = expression_names
        
        response = self.table.scan(**scan_params)
        return response.get('Count', 0)

    def get_findings_summary(self, account_id: Optional[str] = None) -> Dict:
        """
        Get findings summary with lazy refresh caching (15-minute TTL).
        Returns comprehensive summary with severity breakdowns and per-policy counts.
        """
        # Determine cache key
        cache_key = f"findings_summary_{account_id}" if account_id else "findings_summary_all"
        
        # Try cached data
        cached = self._get_cached_findings_summary(cache_key)
        if cached and self._is_fresh(cached, max_age_minutes=15):
            debug(f"Serving cached findings summary from {cached['updated_at']}")
            return cached['summary']
        
        # Cache miss/stale - acquire lock and refresh
        lock_key = f"{cache_key}_lock"
        lock_acquired = self._try_acquire_lock(lock_key, ttl_seconds=30)
        
        if not lock_acquired:
            # Serve stale data while refresh in progress
            if cached:
                debug("Serving stale findings summary while refresh in progress")
                return cached['summary']
            # No cached data and can't acquire lock - wait and retry once
            debug("Waiting for concurrent refresh to complete...")
            time.sleep(1)
            cached = self._get_cached_findings_summary(cache_key)
            if cached:
                return cached['summary']
        
        # Compute fresh summary
        info(f"Computing fresh findings summary for cache_key={cache_key}")
        summary = self._compute_findings_summary(account_id)
        
        # Cache it
        self._save_findings_summary(cache_key, summary)
        
        # Release lock
        if lock_acquired:
            self._release_lock(lock_key)
        
        return summary

    def get_findings_by_policy_breakdown(self, account_id: Optional[str] = None) -> List[Dict]:
        """Get findings breakdown by policy"""
        summary = self.get_findings_summary(account_id)
        return summary['policies']
    
    # ============================================================================
    # CACHING HELPER METHODS
    # ============================================================================
    
    def _get_cached_findings_summary(self, cache_key: str) -> Optional[Dict]:
        """Get cached findings summary from DynamoDB"""
        try:
            response = self.summary_table.get_item(Key={'Type': cache_key})
            item = response.get('Item')
            if item:
                # Convert Decimals from DynamoDB to native Python types
                item['summary'] = self._convert_decimals_to_int(item['summary'])
            return item
        except Exception as e:
            error(f"Error getting cached findings summary: {e}")
            return None
    
    def _is_fresh(self, cached: Dict, max_age_minutes: int) -> bool:
        """Check if cached data is fresh enough"""
        try:
            updated_at = datetime.datetime.fromisoformat(cached['updated_at'].replace('Z', '+00:00'))
            age = datetime.datetime.now(datetime.timezone.utc) - updated_at
            return age.total_seconds() < (max_age_minutes * 60)
        except Exception as e:
            error(f"Error checking cache freshness: {e}")
            return False
    
    def _try_acquire_lock(self, lock_key: str, ttl_seconds: int) -> bool:
        """Try to acquire refresh lock using DynamoDB conditional write"""
        try:
            self.summary_table.put_item(
                Item={
                    'Type': lock_key,
                    'expires_at': int(time.time()) + ttl_seconds
                },
                ConditionExpression='attribute_not_exists(#type) OR #expires < :now',
                ExpressionAttributeNames={'#type': 'Type', '#expires': 'expires_at'},
                ExpressionAttributeValues={':now': int(time.time())}
            )
            debug(f"Acquired refresh lock: {lock_key}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                debug(f"Failed to acquire lock {lock_key} - another process is refreshing")
                return False
            error(f"Error acquiring lock {lock_key}: {e}")
            return False
    
    def _release_lock(self, lock_key: str) -> None:
        """Release refresh lock"""
        try:
            self.summary_table.delete_item(Key={'Type': lock_key})
            debug(f"Released refresh lock: {lock_key}")
        except Exception as e:
            error(f"Error releasing lock {lock_key}: {e}")
    
    def _save_findings_summary(self, cache_key: str, summary: Dict) -> None:
        """Save findings summary to DynamoDB"""
        try:
            # Convert to ensure no Decimals before saving
            clean_summary = self._convert_decimals_to_int(summary)
            self.summary_table.put_item(Item={
                'Type': cache_key,
                'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'summary': clean_summary
            })
            debug(f"Saved findings summary to cache: {cache_key}")
        except Exception as e:
            error(f"Error saving findings summary: {e}")
    
    def _compute_findings_summary(self, account_id: Optional[str] = None) -> Dict:
        """
        Compute findings summary from live data using table scans.
        Returns comprehensive summary with severity breakdowns and per-policy counts.
        """
        info(f"Computing findings summary from live data (account_id={account_id})")
        
        # Build scan parameters
        scan_params = {
            'ProjectionExpression': '#policy, Severity, #state',
            'ExpressionAttributeNames': {
                '#policy': 'Policy',
                '#state': 'State'
            }
        }
        
        if account_id:
            scan_params['FilterExpression'] = 'begins_with(AccountService, :account_prefix)'
            scan_params['ExpressionAttributeValues'] = {':account_prefix': f"{account_id}_"}
        
        response = self.table.scan(**scan_params)
        
        # Aggregate counts
        total_findings = 0
        open_findings = 0
        resolved_findings = 0
        critical_findings = 0  # ACTIVE with severity >= 90
        high_findings = 0      # ACTIVE with severity 50-89
        medium_findings = 0    # ACTIVE with severity 25-49
        low_findings = 0       # ACTIVE with severity 0-24
        policy_counts = {}
        
        for item in response.get('Items', []):
            policy = item.get('Policy', '')
            severity = int(item.get('Severity', 0)) if item.get('Severity') is not None else 0
            state = item.get('State', '')
            
            total_findings += 1
            
            if state == 'ACTIVE':
                open_findings += 1
                # Severity breakdowns (ACTIVE only)
                if severity >= 90:
                    critical_findings += 1
                elif severity >= 50:
                    high_findings += 1
                elif severity >= 25:
                    medium_findings += 1
                else:
                    low_findings += 1
            else:
                resolved_findings += 1
            
            # Per-policy counts
            if policy not in policy_counts:
                policy_counts[policy] = {
                    'total': 0,
                    'open': 0,
                    'resolved': 0,
                    'severity': severity  # Store severity from first occurrence
                }
            policy_counts[policy]['total'] += 1
            if state == 'ACTIVE':
                policy_counts[policy]['open'] += 1
            else:
                policy_counts[policy]['resolved'] += 1
        
        # Get policy definitions for accurate severity (override from definition if available)
        from data_access.policy_manager import PolicyManager
        policy_manager = PolicyManager()
        
        for policy_id in policy_counts.keys():
            policy_def = policy_manager.get_policy_definition(policy_id)
            if policy_def:
                policy_counts[policy_id]['severity'] = policy_def.severity
        
        # Build sorted policies array
        policies = [
            {
                'policy': policy,
                'severity': counts['severity'],
                'total_findings': counts['total'],
                'open_findings': counts['open'],
                'resolved_findings': counts['resolved']
            }
            for policy, counts in policy_counts.items()
        ]
        
        # Sort by severity descending, then by open findings descending
        policies.sort(key=lambda x: (-x['severity'], -x['open_findings']))
        
        info(f"Computed summary: {total_findings} total, {open_findings} open, "
              f"{critical_findings} critical, {high_findings} high, "
              f"{medium_findings} medium, {low_findings} low")
        
        return {
            'total_findings': total_findings,
            'open_findings': open_findings,
            'resolved_findings': resolved_findings,
            'critical_findings': critical_findings,
            'high_findings': high_findings,
            'medium_findings': medium_findings,
            'low_findings': low_findings,
            'policies': policies
        }
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def _item_to_finding(self, item: Dict) -> Finding:
        """Convert DynamoDB item to Finding object"""
        return Finding(
            arn=item.get('ARN', ''),
            policy=item.get('Policy', ''),
            account_service=item.get('AccountService', ''),
            severity=int(item.get('Severity', 0)) if item.get('Severity') is not None else 0,
            state=item.get('State', ''),
            first_seen=item.get('FirstSeen', ''),
            last_evaluated=item.get('LastEvaluated', ''),
            evidence=self._convert_decimals_to_int(item.get('Evidence', {}))
        )
    
    def _convert_decimals_to_int(self, obj):
        """Recursively convert Decimal objects to int/float for JSON serialization"""
        from decimal import Decimal
        
        if isinstance(obj, Decimal):
            # Convert Decimal to int if it's a whole number, otherwise float
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_decimals_to_int(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals_to_int(item) for item in obj]
        else:
            return obj
