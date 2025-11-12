import os, boto3
import sys
import traceback
import datetime
import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.logger import info, error
from data_access.policy_manager import PolicyManager
from data_access.inventory_manager import InventoryManager
from common_utils import get_customer_accounts, get_summary_table

def scan_policy(event, context):
    """
    Simplified policy scanner using new architecture.
    For each account, evaluates all launched policies.
    Tracks scan metrics for anti-entropy monitoring.
    
    Event format:
    {
        "policy_id": "optional - scan specific policy",
        "service": "optional - scan specific service",
        "scan_type": "bootstrap|anti-entropy"  # bootstrap=initial/manual, anti-entropy=scheduled
    }
    """
    # Generate unique scan ID for traceability
    scan_id = str(uuid.uuid4())
    
    # Capture scan start time (milliseconds)
    scan_start_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    
    # Get scan parameters
    policy_id = event.get('policy_id')  # Optional: scan specific policy
    service_filter = event.get('service')  # Optional: scan specific service
    scan_type = event.get('scan_type', 'bootstrap')  # Default to bootstrap for safety
    
    info(f"[{scan_id}] Starting policy scan: policy_id={policy_id or 'all'}, service={service_filter or 'all'}, scan_type={scan_type}")
    
    # Get all launched policies
    policy_manager = PolicyManager()
    inventory_manager = InventoryManager()
    launched_policies = policy_manager.list_launched_policies()
    
    # Filter by policy_id if specified
    if policy_id:
        launched_policies = [p for p in launched_policies if p.policy_id == policy_id]
    
    # Filter by service if specified
    if service_filter:
        filtered_policies = []
        for p in launched_policies:
            policy_def = policy_manager.get_policy_definition(p.policy_id)
            if policy_def and policy_def.service == service_filter:
                filtered_policies.append(p)
        launched_policies = filtered_policies
    
    # Only process active policies
    launched_policies = [p for p in launched_policies if p.status == 'active']
    
    if not launched_policies:
        info(f"[{scan_id}] No active policies found")
        return {'statusCode': 200, 'body': "No active policies found", 'scan_id': scan_id}
    
    # Get customer accounts
    accounts = get_customer_accounts()
    
    processed_count = 0
    skipped_count = 0
    findings_created = 0
    findings_closed = 0
    
    # For each account, evaluate all launched policies
    for account in accounts:
        account_id = account.get('account_id')
        if not account_id:
            continue
        
        for launched_policy in launched_policies:
            try:
                # Create policy evaluator with launched configuration
                evaluator = policy_manager.create_policy_evaluator(launched_policy.policy_id, launched_policy)
                
                # Get policy definition to determine service
                policy_def = policy_manager.get_policy_definition(launched_policy.policy_id)
                if not policy_def:
                    continue
                
                # Get resources for this account and service
                account_service = f"{account_id}_{policy_def.service}"
                resources = inventory_manager.get_resources_by_account_service(account_service)
                
                # Evaluate each resource
                for resource in resources:
                    resource_arn = resource['ARN']
                    config = resource['Configuration']
                    # DescribeTime should always be present, but use scan_start_ms as acceptable recovery
                    describe_time_ms = resource.get('DescribeTime', scan_start_ms)
                    
                    try:
                        # Evaluate resource with config and describe time (includes scoping and finding persistence)
                        result = evaluator.evaluate(resource_arn, config, describe_time_ms)
                        
                        if result.get('scoped', True):  # Only count if resource was in scope
                            if result['compliant']:
                                findings_closed += 1
                            else:
                                findings_created += 1
                            processed_count += 1
                        
                    except Exception as e:
                        error(f"[{scan_id}] Error evaluating {resource_arn} with policy {launched_policy.policy_id}: {str(e)}\n{traceback.format_exc()}")
                        skipped_count += 1
                        
            except Exception as e:
                error(f"[{scan_id}] Error creating evaluator for policy {launched_policy.policy_id}: {str(e)}\n{traceback.format_exc()}")
                skipped_count += 1
    
    # Calculate scan duration
    scan_end_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    scan_duration_ms = scan_end_ms - scan_start_ms
    
    # Only save drift metrics for anti-entropy scans (not bootstrap/manual)
    if scan_type == 'anti-entropy':
        try:
            summary_table = get_summary_table()
            summary_table.put_item(Item={
                'Type': 'last_policy_scan',
                'scan_id': scan_id,
                'timestamp_ms': scan_end_ms,
                'duration_ms': scan_duration_ms,
                'processed_resources': processed_count,
                'skipped_resources': skipped_count,
                'findings_created': findings_created,
                'findings_closed': findings_closed,
                'policies_evaluated': len(launched_policies),
                'accounts_processed': len(accounts),
                'scan_type': scan_type
            })
            info(f"[{scan_id}] Saved policy scan metrics (anti-entropy): {processed_count} resources processed in {scan_duration_ms}ms")
        except Exception as e:
            error(f"[{scan_id}] Error saving scan metrics: {str(e)}\n{traceback.format_exc()}")
    else:
        info(f"[{scan_id}] Skipping drift metrics for {scan_type} scan: {processed_count} resources processed in {scan_duration_ms}ms")
    
    return {
        'statusCode': 200,
        'body': {
            'scan_id': scan_id,
            'processed_resources': processed_count,
            'skipped_resources': skipped_count,
            'findings_created': findings_created,
            'findings_closed': findings_closed,
            'policies_evaluated': len(launched_policies),
            'accounts_processed': len(accounts),
            'scan_duration_ms': scan_duration_ms
        }
    }
