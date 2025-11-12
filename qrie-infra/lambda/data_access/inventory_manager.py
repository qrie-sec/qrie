"""
InventoryManager - Centralized inventory data access with caching.
Handles all inventory CRUD operations and resource management.
"""
import os
import boto3
import datetime
import time
from typing import List, Dict, Optional
from functools import lru_cache
from decimal import Decimal
from botocore.exceptions import ClientError
import json
import base64
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import shared tables from common
from common_utils import get_resources_table, get_summary_table
from common.logger import debug, info, error

class InventoryManager:
    """Manages all inventory data access operations with caching"""
    
    def __init__(self):
        self.resource_table = get_resources_table()
        self.summary_table = get_summary_table()
    
    # ============================================================================
    # READ OPERATIONS
    # ============================================================================
    
    def get_resource_by_arn(self, arn: str) -> Optional[Dict]:
        """Get a specific resource by ARN"""
        try:
            from common_utils import get_account_from_arn, get_service_from_arn
            
            account_id = get_account_from_arn(arn)
            service = get_service_from_arn(arn)
            
            if not account_id or not service:
                return None
            
            account_service = f"{account_id}_{service}"
            response = self.resource_table.get_item(Key={
                'AccountService': account_service,
                'ARN': arn
            })
            return response.get('Item')
        except Exception as e:
            error(f"Error getting resource by ARN {arn}: {e}")
            return None
    
    # ============================================================================
    # WRITE OPERATIONS
    # ============================================================================
    
    def upsert_resource(self, account_id: str, service: str, arn: str, configuration: Dict, 
                       describe_time_ms: int) -> None:
        """
        Create or update a resource in inventory using conditional writes.
        One-shot update that handles both create and update cases atomically.
        
        Args:
            account_id: AWS account ID
            service: Service name (s3, ec2, iam, etc.)
            arn: Resource ARN
            configuration: Resource configuration dict
            describe_time_ms: Timestamp (milliseconds) when describe call was made (REQUIRED)
        """
        account_service = f"{account_id}_{service}"
        
        try:
            self.resource_table.update_item(
                Key={'AccountService': account_service, 'ARN': arn},
                UpdateExpression='SET #config = :config, #describeTime = :now, #lastSeen = :now',
                ConditionExpression=(
                    'attribute_not_exists(ARN) OR '
                    'attribute_not_exists(#describeTime) OR '
                    '#describeTime < :now'
                ),
                ExpressionAttributeNames={
                    '#config': 'Configuration',
                    '#describeTime': 'DescribeTime',
                    '#lastSeen': 'LastSeenAt'
                },
                ExpressionAttributeValues={
                    ':config': configuration,
                    ':now': describe_time_ms
                },
                ReturnValues='NONE'
            )
            debug(f"Updated resource {arn} with describe time {describe_time_ms}")
        except self.resource_table.meta.client.exceptions.ConditionalCheckFailedException:
            # Item exists and has more recent describe time - this is expected
            debug(f"Skipping update for {arn} - existing describe time is more recent than {describe_time_ms}")
        
        # Clear relevant caches
        self._clear_resource_cache(account_id, service)

    def delete_resource(self, arn: str, account_id: Optional[str] = None) -> None:
        """Delete a resource from inventory
        
        Args:
            arn: Resource ARN
            account_id: Optional account ID. Required for S3 resources since their ARNs don't contain account IDs.
        """
        if account_id:
            service = self._get_service_from_arn(arn)
        else:
            account_id, service = self._parse_arn(arn)
        
        account_service = f"{account_id}_{service}"
        self.resource_table.delete_item(Key={
            'AccountService': account_service,
            'ARN': arn
        })
        
        # Clear relevant caches
        self._clear_resource_cache(account_id, service)

    def bulk_upsert_resources(self, resources: List[Dict]) -> None:
        """Bulk upsert multiple resources for efficiency"""
        with self.resource_table.batch_writer() as batch:
            for resource in resources:
                batch.put_item(Item=resource)
        
        # Clear all caches since we don't know which accounts/services were affected
    
    # ============================================================================
    # READ OPERATIONS WITH CACHING
    # ============================================================================
    
    def get_resource(self, arn: str, account_id: Optional[str] = None) -> Optional[Dict]:
        """Get a specific resource by ARN
        
        Args:
            arn: Resource ARN
            account_id: Optional account ID. Required for S3 resources since their ARNs don't contain account IDs.
                       For other resources, will be parsed from ARN if not provided.
        """
        if account_id:
            service = self._get_service_from_arn(arn)
        else:
            # Parse account_id from ARN - will raise ValueError for S3 ARNs
            account_id, service = self._parse_arn(arn)
        
        response = self.resource_table.get_item(Key={
            'AccountService': f"{account_id}_{service}",
            'ARN': arn
        })
        return response.get('Item')
    
    def _get_service_from_arn(self, arn: str) -> str:
        """Extract service from ARN"""
        from common_utils import get_service_from_arn
        return get_service_from_arn(arn)
    
    def _parse_arn(self, arn: str) -> tuple:
        """Parse ARN to extract account_id and service
        
        Raises:
            ValueError: If ARN doesn't contain account ID (e.g., S3 bucket ARNs)
        """
        # ARN format: arn:aws:service:region:account-id:resource
        from common_utils import get_account_from_arn
        
        service = self._get_service_from_arn(arn)
        account_id = get_account_from_arn(arn)
        
        # S3 bucket ARNs don't contain account IDs - fail fast
        if not account_id:
            raise ValueError(f"ARN does not contain account ID: {arn}. For S3 resources, account_id must be provided.")
            
        return account_id, service

    @lru_cache(maxsize=64)
    def get_resources_by_account_service(self, account_service: str, limit: Optional[int] = None) -> List[Dict]:
        """Get all resources for a specific account and service (cached)"""
        query_params = {
            'KeyConditionExpression': 'AccountService = :account_service',
            'ExpressionAttributeValues': {':account_service': account_service}
        }
        
        if limit:
            query_params['Limit'] = limit
            
        response = self.resource_table.query(**query_params)
        return response.get('Items', [])

    def get_resources_paginated(self, account_id: Optional[str] = None, service: Optional[str] = None,
                              page_size: int = 50, next_token: Optional[str] = None) -> Dict:
        """Get paginated resources with optional filtering"""
        from common_utils import SUPPORTED_SERVICES
        
        # Validate service if provided
        if service and service not in SUPPORTED_SERVICES:
            error(f"Requested unsupported service type: {service}")
            error(f"Supported services: {SUPPORTED_SERVICES}")
            # Return empty result for unsupported services
            return {
                'resources': [],
                'count': 0
            }
        
        if account_id and service:
            # Use query for efficient account+service filtering
            account_service = f"{account_id}_{service}"
            query_params = {
                'KeyConditionExpression': 'AccountService = :account_service',
                'ExpressionAttributeValues': {':account_service': account_service},
                'Limit': page_size
            }
            
            if next_token:
                query_params['ExclusiveStartKey'] = json.loads(base64.b64decode(next_token).decode())
            
            response = self.resource_table.query(**query_params)
        
        elif account_id:
            # Scan with filter for account-only filtering
            scan_params = {
                'FilterExpression': 'begins_with(AccountService, :account_prefix)',
                'ExpressionAttributeValues': {':account_prefix': f"{account_id}_"},
                'Limit': page_size
            }
            
            if next_token:
                scan_params['ExclusiveStartKey'] = json.loads(base64.b64decode(next_token).decode())
            
            response = self.resource_table.scan(**scan_params)
        
        elif service:
            # Scan with filter for service-only filtering
            scan_params = {
                'FilterExpression': 'ends_with(AccountService, :service_suffix)',
                'ExpressionAttributeValues': {':service_suffix': f"_{service}"},
                'Limit': page_size
            }
            
            if next_token:
                scan_params['ExclusiveStartKey'] = json.loads(base64.b64decode(next_token).decode())
            
            response = self.resource_table.scan(**scan_params)
        
        else:
            # Full scan
            scan_params = {'Limit': page_size}
            
            if next_token:
                scan_params['ExclusiveStartKey'] = json.loads(base64.b64decode(next_token).decode())
            
            response = self.resource_table.scan(**scan_params)
        
        # Filter out unsupported services from results
        items = response.get('Items', [])
        filtered_items = []
        unsupported_found = set()
        
        for item in items:
            account_service = item.get('AccountService', '')
            if '_' in account_service:
                _, svc = account_service.split('_', 1)
                if svc not in SUPPORTED_SERVICES:
                    unsupported_found.add(svc)
                    continue
            filtered_items.append(item)
        
        # Log if we filtered out unsupported services
        if unsupported_found:
            error(f"Filtered out unsupported service types: {sorted(unsupported_found)}")
            error(f"Supported services: {SUPPORTED_SERVICES}")
        
        result = {
            'resources': filtered_items,
            'count': len(filtered_items)
        }
        
        if 'LastEvaluatedKey' in response:
            result['next_token'] = base64.b64encode(
                json.dumps(response['LastEvaluatedKey']).encode()
            ).decode()
        
        return result

    @lru_cache(maxsize=32)
    def get_inventory_summary(self, account_id: str) -> Dict:
        """Get inventory summary for an account (cached)"""
        # Scan for all resources in this account
        response = self.resource_table.scan(
            FilterExpression='begins_with(AccountService, :account_prefix)',
            ExpressionAttributeValues={':account_prefix': f"{account_id}_"}
        )
        
        resources = response.get('Items', [])
        
        # Group by service
        summary = {}
        for resource in resources:
            account_service = resource.get('AccountService', '')
            if '_' in account_service:
                service = account_service.split('_', 1)[1]
                summary[service] = summary.get(service, 0) + 1
        
        return summary

    @lru_cache(maxsize=16)
    def get_all_resources(self) -> List[Dict]:
        """Get all resources from inventory (cached, use sparingly)"""
        response = self.resource_table.scan()
        return response.get('Items', [])
    


    @lru_cache(maxsize=1)
    def _get_customer_accounts_cached(self) -> List[Dict]:
        """Cached version of get_customer_accounts"""
        from common_utils import get_customer_accounts
        return get_customer_accounts()
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def _clear_resource_cache(self, account_id: str, service: str) -> None:
        """Clear cached data for a specific account/service"""
        # Clear specific caches that might be affected
        self.get_resources_by_account_service.cache_clear()
        self.get_inventory_summary.cache_clear()
        self.get_all_resources.cache_clear()
    
    def _clear_all_caches(self) -> None:
        """Clear all cached data"""
        self.get_resources_by_account_service.cache_clear()
        self.get_inventory_summary.cache_clear()
        self.get_all_resources.cache_clear()

    def get_resources_summary(self, account_id: Optional[str] = None) -> Dict:
        """
        Get resources summary with 15-minute caching (same pattern as findings).
        Includes findings data and non-compliant resource counts.
        """
        # Build cache key
        cache_key = f"resources_summary_{account_id or 'all'}"
        
        # Try cache first
        cached = self._get_cached_summary(cache_key)
        if cached and self._is_fresh(cached, max_age_minutes=15):
            debug(f"Serving cached resources summary from {cached['updated_at']}")
            return cached['summary']
        
        debug("Cache miss or stale, computing fresh resources summary")
        
        # Try to acquire lock for refresh
        lock_key = f"{cache_key}_lock"
        lock_acquired = self._try_acquire_lock(lock_key, ttl_seconds=60)
        
        if not lock_acquired:
            debug("Another process is refreshing, serving stale data if available")
            if cached:
                debug(f"Serving stale data from {cached['updated_at']}")
                return cached['summary']
            # Wait briefly and retry cache
            time.sleep(0.5)
            cached = self._get_cached_summary(cache_key)
            if cached:
                return cached['summary']
            # Fall through to compute if still no cache
        
        debug("Acquired refresh lock" if lock_acquired else "Computing without lock")
        
        try:
            # Compute fresh summary
            summary = self._compute_resources_summary(account_id)
            
            # Save to cache
            self._save_summary(cache_key, summary)
            
            return summary
        finally:
            # Release lock if we acquired it
            if lock_acquired:
                self._release_lock(lock_key)

    def count_resources_by_type(self, account_id: Optional[str] = None) -> Dict[str, int]:
        """Get resource counts by service type"""
        summary = self.get_resources_summary(account_id)
        return {item['resource_type']: item['all_resources'] for item in summary['resource_types']}
    
    # ============================================================================
    # CACHE MANAGEMENT (15-minute TTL, same pattern as findings)
    # ============================================================================
    
    def _compute_resources_summary(self, account_id: Optional[str] = None) -> Dict:
        """
        Compute complete resources summary with findings data.
        This is the expensive operation that gets cached.
        """
        from common_utils import SUPPORTED_SERVICES
        
        info(f"Computing resources summary from live data (account={account_id or 'all'})...")
        
        # Build scan parameters
        filter_expressions = []
        expression_values = {}
        
        if account_id:
            filter_expressions.append('begins_with(AccountService, :account_prefix)')
            expression_values[':account_prefix'] = f"{account_id}_"
        
        scan_params = {
            'ProjectionExpression': 'AccountService, ARN'
        }
        
        if filter_expressions:
            scan_params['FilterExpression'] = ' AND '.join(filter_expressions)
            scan_params['ExpressionAttributeValues'] = expression_values
        
        # Scan resources table
        response = self.resource_table.scan(**scan_params)
        
        # Count by resource type and collect ARNs
        resource_counts = {}  # {service: count}
        resource_arns_by_type = {}  # {service: [arns]}
        total_resources = 0
        accounts = set()
        unsupported_services = set()
        
        for item in response.get('Items', []):
            account_service = item['AccountService']
            arn = item['ARN']
            account, service = account_service.split('_', 1)
            
            # Only include supported services
            if service not in SUPPORTED_SERVICES:
                unsupported_services.add(service)
                continue
            
            accounts.add(account)
            resource_counts[service] = resource_counts.get(service, 0) + 1
            total_resources += 1
            
            if service not in resource_arns_by_type:
                resource_arns_by_type[service] = []
            resource_arns_by_type[service].append(arn)
        
        # Log unsupported services if found
        if unsupported_services:
            error(f"Found unsupported service types in inventory: {sorted(unsupported_services)}")
            error(f"Supported services: {SUPPORTED_SERVICES}")
        
        # Get findings data from FindingsManager (uses its own 15-min cache)
        from data_access.findings_manager import FindingsManager
        findings_mgr = FindingsManager()
        findings_summary = findings_mgr.get_findings_summary(account_id)
        
        # Get unique ARNs with ACTIVE findings to calculate non-compliant counts
        # Scan findings table for ACTIVE findings
        findings_table = findings_mgr.table
        findings_scan_params = {
            'FilterExpression': '#state = :active',
            'ExpressionAttributeNames': {'#state': 'State'},
            'ExpressionAttributeValues': {':active': 'ACTIVE'},
            'ProjectionExpression': 'ARN'
        }
        
        # Add account filter if specified
        if account_id:
            findings_scan_params['FilterExpression'] += ' AND begins_with(AccountService, :account_prefix)'
            findings_scan_params['ExpressionAttributeValues'][':account_prefix'] = f"{account_id}_"
        
        findings_response = findings_table.scan(**findings_scan_params)
        
        # Get unique non-compliant ARNs
        non_compliant_arns = set(f['ARN'] for f in findings_response.get('Items', []))
        
        debug(f"Found {len(non_compliant_arns)} unique non-compliant resources")
        
        # Count non-compliant per resource type
        non_compliant_by_type = {}
        for service, arns in resource_arns_by_type.items():
            non_compliant_count = sum(1 for arn in arns if arn in non_compliant_arns)
            non_compliant_by_type[service] = non_compliant_count
        
        # Build response matching TypeScript interface
        summary = {
            'total_resources': total_resources,
            'total_accounts': len(accounts),
            'total_findings': findings_summary['total_findings'],
            'critical_findings': findings_summary['critical_findings'],
            'high_findings': findings_summary['high_findings'],
            'resource_types': [
                {
                    'resource_type': service,
                    'all_resources': count,
                    'non_compliant': non_compliant_by_type.get(service, 0)
                }
                for service, count in sorted(resource_counts.items())
            ]
        }
        
        info(f"Computed summary: {total_resources} resources, {len(non_compliant_arns)} non-compliant")
        
        return summary
    
    def _get_cached_summary(self, cache_key: str) -> Optional[Dict]:
        """Get cached summary from qrie_summary table"""
        try:
            response = self.summary_table.get_item(Key={'Type': cache_key})
            item = response.get('Item')
            if item:
                # Convert Decimals to native Python types
                item['summary'] = self._convert_decimals(item['summary'])
            return item
        except Exception as e:
            error(f"Error getting cached summary: {e}")
            return None
    
    def _is_fresh(self, cached: Dict, max_age_minutes: int) -> bool:
        """Check if cached data is fresh enough"""
        try:
            updated_at = datetime.datetime.fromisoformat(cached['updated_at'].replace('Z', '+00:00'))
            age = datetime.datetime.now(datetime.timezone.utc) - updated_at
            is_fresh = age.total_seconds() < (max_age_minutes * 60)
            if is_fresh:
                debug(f"Cache is fresh (age: {age.total_seconds():.0f}s < {max_age_minutes*60}s)")
            else:
                debug(f"Cache is stale (age: {age.total_seconds():.0f}s >= {max_age_minutes*60}s)")
            return is_fresh
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
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False
            error(f"Error acquiring lock: {e}")
            return False
    
    def _release_lock(self, lock_key: str) -> None:
        """Release refresh lock"""
        try:
            self.summary_table.delete_item(Key={'Type': lock_key})
            debug(f"Released lock: {lock_key}")
        except Exception as e:
            error(f"Error releasing lock: {e}")
    
    def _save_summary(self, cache_key: str, summary: Dict) -> None:
        """Save summary to qrie_summary table"""
        try:
            # Convert Decimals before saving
            clean_summary = self._convert_decimals(summary)
            self.summary_table.put_item(Item={
                'Type': cache_key,
                'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'summary': clean_summary
            })
            debug(f"Saved {cache_key} to cache")
        except Exception as e:
            error(f"Error saving summary: {e}")
    
    def _convert_decimals(self, obj):
        """Recursively convert Decimal objects to int/float for JSON serialization"""
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        return obj
