"""
Dedicated Inventory Generation Lambda
Handles inventory generation for all services across customer accounts.
Tracks inventory scan metrics for anti-entropy monitoring.
"""
import os
import sys
import json
import traceback
import datetime
import boto3
import uuid
from common.logger import info, error

# Add lambda directory to path for shared modules
lambda_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if lambda_dir not in sys.path:
    sys.path.append(lambda_dir)

from typing import Dict, List
from data_access.inventory_manager import InventoryManager
from inventory_generator.s3_inventory import generate_s3_inventory
from inventory_generator.ec2_inventory import generate_ec2_inventory
from inventory_generator.iam_inventory import generate_iam_inventory
from common_utils import get_customer_accounts, SUPPORTED_SERVICES, get_summary_table


def lambda_handler(event, context):
    """
    Lambda handler for inventory generation.
    
    Event format:
    {
        "service": "s3|ec2|iam|all",
        "account_id": "optional - specific account",
        "cached": false,
        "scan_type": "bootstrap|anti-entropy"  # bootstrap=initial/manual, anti-entropy=scheduled
    }
    """
    # Generate unique scan ID for traceability
    scan_id = str(uuid.uuid4())
    
    # Capture scan start time (milliseconds)
    scan_start_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    
    try:
        service = event.get('service', 'all')
        account_id = event.get('account_id')
        cached = event.get('cached', False)
        scan_type = event.get('scan_type', 'bootstrap')  # Default to bootstrap for safety
        
        info(f"[{scan_id}] Starting inventory generation: service={service}, account={account_id or 'all'}, scan_type={scan_type}")
        
        if account_id:
            # Generate for specific account
            if service == 'all':
                results = generate_inventory_for_account(account_id, cached)
            else:
                results = [generate_inventory_for_account_service(account_id, service, cached)]
        else:
            # Generate for all accounts
            if service == 'all':
                results = generate_inventory_all_services(cached)
            else:
                results = generate_inventory_for_service(service, cached)
        
        # Calculate scan duration and save metrics
        scan_end_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
        scan_duration_ms = scan_end_ms - scan_start_ms
        
        # Count total resources found
        total_resources = 0
        if isinstance(results, list):
            for result in results:
                if isinstance(result, dict):
                    total_resources += result.get('resources_found', 0)
        elif isinstance(results, dict):
            for service_results in results.values():
                if isinstance(service_results, list):
                    for result in service_results:
                        if isinstance(result, dict):
                            total_resources += result.get('resources_found', 0)
        
        # Only save drift metrics for anti-entropy scans (not bootstrap/manual)
        if scan_type == 'anti-entropy':
            try:
                summary_table = get_summary_table()
                summary_table.put_item(Item={
                    'Type': 'last_inventory_scan',
                    'scan_id': scan_id,
                    'timestamp_ms': scan_end_ms,
                    'duration_ms': scan_duration_ms,
                    'service': service,
                    'account_id': account_id or 'all',
                    'resources_found': total_resources,
                    'scan_type': scan_type
                })
                info(f"[{scan_id}] Saved inventory scan metrics (anti-entropy): {total_resources} resources found in {scan_duration_ms}ms")
            except Exception as e:
                error(f"Error saving inventory scan metrics: {str(e)}\n{traceback.format_exc()}")
        else:
            info(f"[{scan_id}] Skipping drift metrics for {scan_type} scan: {total_resources} resources found in {scan_duration_ms}ms")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Inventory generation completed',
                'scan_id': scan_id,
                'results': results,
                'scan_duration_ms': scan_duration_ms,
                'total_resources': total_resources
            })
        }
        
    except Exception as e:
        error(f"[{scan_id}] Error in inventory generation: {str(e)}\n{traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'scan_id': scan_id
            })
        }


def generate_inventory_for_account(account_id: str, cached: bool = False) -> List[Dict]:
    """Generate inventory for all services in a specific account"""
    # Validate account exists in our list
    customer_accounts = get_customer_accounts()
    valid_account_ids = [acc.get('AccountId') for acc in customer_accounts if acc.get('AccountId')]
    
    if account_id not in valid_account_ids:
        raise ValueError(f"Account {account_id} not found in customer accounts list. Valid accounts: {valid_account_ids}")
    
    inventory_manager = InventoryManager()
    results = []
    
    for service in SUPPORTED_SERVICES:
        try:
            result = generate_inventory_for_account_service(account_id, service, cached)
            results.append(result)
        except Exception as e:
            error(f"Error generating inventory for {service} in account {account_id}: {str(e)}\n{traceback.format_exc()}")
            results.append({
                'service': service,
                'account_id': account_id,
                'resources_found': 0,
                'status': 'error',
                'error': str(e)
            })
    
    return results


def generate_inventory_for_account_service(account_id: str, service: str, cached: bool = False) -> Dict:
    """
    Generate inventory for a specific service in a specific account using service registry.
    
    Args:
        account_id: AWS account ID
        service: Service name (s3, ec2, iam)
        cached: Whether to use cached inventory (for testing)
        
    Returns:
        Dict with resource_count and resources list
    """
    if service not in SUPPORTED_SERVICES:
        raise ValueError(f"Unsupported service: {service}")
    
    inventory_manager = InventoryManager()
    
    # Use service registry to list resources
    from services import list_resources
    
    info(f"Generating {service} inventory for account {account_id} (cached={cached})")
    
    failed_count = 0
    
    if cached:
        # For cached mode, retrieve from inventory table
        resources = inventory_manager.get_resources_by_account_service(f"{account_id}_{service}")
    else:
        # Fresh scan - use service-specific list_resources
        result = list_resources(service, account_id)
        resources = result['resources']
        failed_count = result.get('failed_count', 0)
        
        # Store in inventory
        describe_time_ms = int(time.time() * 1000)
        for resource in resources:
            arn = resource['ARN']  # Required field from service list_resources
            inventory_manager.upsert_resource(
                account_id=account_id,
                service=service,
                arn=arn,
                configuration=resource,
                describe_time_ms=describe_time_ms
            )
    
    return {
        'resource_count': len(resources),
        'failed_count': failed_count,
        'resources': resources
    }


def generate_inventory_for_service(service: str, cached: bool = False) -> List[Dict]:
    """Generate inventory for a specific service across all customer accounts"""
    if service not in SUPPORTED_SERVICES:
        raise ValueError(f"Unsupported service: {service}")
    
    customer_accounts = get_customer_accounts()
    results = []
    
    for account in customer_accounts:
        account_id = account.get('account_id')
        if not account_id:
            continue
            
        try:
            result = generate_inventory_for_account_service(account_id, service, cached)
            results.append({
                'account_id': account_id,
                'service': service,
                'status': 'success',
                'resources_found': result.get('resources_found', 0)
            })
        except Exception as e:
            error(f"Error generating inventory for {service} in account {account_id}: {str(e)}\n{traceback.format_exc()}")
            results.append({
                'account_id': account_id,
                'service': service,
                'status': 'error',
                'error': str(e)
            })
    
    return results


def generate_inventory_all_services(cached: bool = False) -> Dict:
    """Generate inventory for all services across all customer accounts"""
    results = {}
    
    for service in SUPPORTED_SERVICES:
        try:
            results[service] = generate_inventory_for_service(service, cached)
        except Exception as e:
            error(f"Error generating inventory for service {service}: {str(e)}\n{traceback.format_exc()}")
            results[service] = {
                'status': 'error',
                'error': str(e)
            }
    
    return results
