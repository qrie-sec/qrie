"""Policies API - Handles launched policy listing for the UI."""
import json
import os
import sys
import traceback
import boto3
from dataclasses import asdict
from data_access.findings_manager import FindingsManager
from data_access.policy_manager import PolicyManager
from policy_definition import ScopeConfig
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.logger import info, error
from common.exceptions import ValidationError, NotFoundError


policy_manager = None


def get_policy_manager() -> PolicyManager:
    """Return a cached PolicyManager instance."""
    global policy_manager
    if policy_manager is None:
        policy_manager = PolicyManager()
    return policy_manager


# ==================================
#     HANDLER FUNCTIONS
# ==================================
# These functions are called by the API handler


def handle_get_policies(query_params, headers):
    """
    Unified handler for GET /policies with flexible filtering.
    
    Query params:
    - status: 'active' | 'available' | 'all' (default: 'all')
    - policy_id: specific policy ID (returns array with 1 item)
    - services: comma-separated service filter
    """
    status = query_params.get('status', 'all')
    policy_id = query_params.get('policy_id')
    services_filter = query_params.get('services', '').split(',') if query_params.get('services') else []
    
    # Single policy lookup
    if policy_id:
        return _get_single_policy(policy_id, headers)
    
    # List policies based on status
    policies_data = []
    
    if status in ['active', 'all']:
        active_policies = _get_active_policies_data(services_filter)
        policies_data.extend(active_policies)
    
    if status in ['available', 'all']:
        available_policies = _get_available_policies_data(services_filter)
        policies_data.extend(available_policies)
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(policies_data)
    }


def _get_single_policy(policy_id, headers):
    """Get a single policy by ID (returns array with 1 item for consistency)"""
    # Get policy definition (always available)
    policy_def = get_policy_manager().get_policy_definition(policy_id)
    if not policy_def:
        raise NotFoundError(f'Policy {policy_id} not found')
    
    # Check if policy is launched
    launched_policy = get_policy_manager().get_launched_policy(policy_id)
    
    if launched_policy:
        # Policy is active - return full launched policy data
        findings_manager = FindingsManager()
        findings_summary = findings_manager.get_findings_summary()
        
        # Lookup from cache
        open_findings_count = 0
        for p in findings_summary['policies']:
            if p['policy'] == policy_id:
                open_findings_count = p['open_findings']
                break
        
        policy_data = {
            'policy_id': policy_def.policy_id,
            'description': policy_def.description,
            'service': policy_def.service,
            'category': policy_def.category,
            'severity': launched_policy.severity,
            'remediation': launched_policy.remediation,
            'scope': asdict(launched_policy.scope),
            'status': 'active',
            'open_findings': open_findings_count,
            'created_at': launched_policy.created_at.split('T')[0] if launched_policy.created_at else None,
            'updated_at': launched_policy.updated_at.split('T')[0] if launched_policy.updated_at else None
        }
    else:
        # Policy is available - return definition
        policy_data = {
            'policy_id': policy_def.policy_id,
            'description': policy_def.description,
            'service': policy_def.service,
            'category': policy_def.category,
            'severity': policy_def.severity,
            'remediation': policy_def.remediation,
            'scope': None,
            'status': 'available',
            'open_findings': 0,
            'created_at': None,
            'updated_at': None
        }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps([policy_data])  # Return as array for consistency
    }


def _get_active_policies_data(services_filter):
    """Get active policies with full operational data"""
    findings_manager = FindingsManager()
    
    # Get cached findings summary (15-min TTL)
    findings_summary = findings_manager.get_findings_summary()
    policy_findings_map = {
        p['policy']: p['open_findings'] 
        for p in findings_summary['policies']
    }
    
    policies = get_policy_manager().list_launched_policies(status_filter='active')
    
    policies_data = []
    for policy in policies:
        # Filter by services if specified  
        if services_filter and policy.service not in services_filter:
            continue
            
        # Lookup from cached summary
        open_findings_count = policy_findings_map.get(policy.policy_id, 0)
        
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
            'status': 'active'
        })
    
    return policies_data


def _get_available_policies_data(services_filter):
    """Get available (unlaunched) policies"""
    available_policies = get_policy_manager().get_available_policies()
    launched_policy_ids = {p.policy_id for p in get_policy_manager().list_launched_policies()}
    
    policies_data = []
    for policy_def in available_policies:
        # Skip if already launched
        if policy_def.policy_id in launched_policy_ids:
            continue
            
        # Filter by services if specified
        if services_filter and policy_def.service not in services_filter:
            continue
        
        policies_data.append({
            'policy_id': policy_def.policy_id,
            'description': policy_def.description,
            'service': policy_def.service,
            'category': policy_def.category,
            'severity': policy_def.severity,
            'remediation': policy_def.remediation,
            'scope': None,
            'status': 'available',
            'open_findings': 0,
            'created_at': None,
            'updated_at': None
        })
    
    return policies_data


def handle_launch_policy(body, headers):
    """Handle POST /policies - launch a new policy"""
    data = json.loads(body) if isinstance(body, str) else body
    
    policy_id = data.get('policy_id')
    info(f"Launch policy request: policy_id={policy_id}")
    
    if not policy_id:
        raise ValidationError('policy_id is required')
    
    # Parse scope configuration
    scope_data = data.get('scope', {})
    scope = ScopeConfig(
        include_accounts=scope_data.get('include_accounts') or [],
        exclude_accounts=scope_data.get('exclude_accounts') or [],
        include_tags=scope_data.get('include_tags') or {},
        exclude_tags=scope_data.get('exclude_tags') or {},
        include_ou_paths=scope_data.get('include_ou_paths') or [],
        exclude_ou_paths=scope_data.get('exclude_ou_paths') or []
    )
    
    severity = data.get('severity')
    remediation = data.get('remediation')
    
    # Launch the policy
    info(f"Launching policy {policy_id} with severity={severity}, scope={len(scope.include_accounts or [])} accounts")
    get_policy_manager().launch_policy(
        policy_id=policy_id,
        scope=scope,
        severity=severity,
        remediation=remediation
    )
    info(f"Successfully launched policy {policy_id}")
    
    # Trigger bootstrap scan for the newly launched policy
    try:
        lambda_client = boto3.client('lambda')
        scan_payload = {
            'policy_id': policy_id,
            'scan_type': 'bootstrap'  # Bootstrap scan, not anti-entropy
        }
        info(f"Triggering bootstrap scan for policy {policy_id}")
        lambda_client.invoke(
            FunctionName='qrie_policy_scanner',
            InvocationType='Event',  # Async invocation
            Payload=json.dumps(scan_payload)
        )
        info(f"Bootstrap scan triggered for policy {policy_id}")
    except Exception as scan_err:
        # Log error but don't fail the policy launch
        error(f"Failed to trigger bootstrap scan for policy {policy_id}: {scan_err}\n{traceback.format_exc()}")
    
    return {
        'statusCode': 201,
        'headers': headers,
        'body': json.dumps({
            'message': f'Policy {policy_id} launched successfully',
            'bootstrap_scan_triggered': True
        })
    }


def handle_update_policy(policy_id, body, headers):
    """Handle PUT /policies/{policy_id} - update policy metadata (scope, severity, remediation)"""
    data = json.loads(body) if isinstance(body, str) else body
    
    info(f"Update policy request: policy_id={policy_id}")
    
    # Build update kwargs (no status updates - use DELETE to remove policy)
    update_kwargs = {}
    
    if 'severity' in data:
        update_kwargs['severity'] = data['severity']
    
    if 'remediation' in data:
        update_kwargs['remediation'] = data['remediation']
    
    if 'scope' in data:
        scope_data = data['scope']
        update_kwargs['scope'] = ScopeConfig(
            include_accounts=scope_data.get('include_accounts') or [],
            exclude_accounts=scope_data.get('exclude_accounts') or [],
            include_tags=scope_data.get('include_tags') or {},
            exclude_tags=scope_data.get('exclude_tags') or {},
            include_ou_paths=scope_data.get('include_ou_paths') or [],
            exclude_ou_paths=scope_data.get('exclude_ou_paths') or []
        )
    
    if not update_kwargs:
        raise ValidationError('At least one field (scope, severity, remediation) must be provided')
    
    # Update the policy
    info(f"Updating policy {policy_id} with {len(update_kwargs)} changes")
    success = get_policy_manager().update_launched_policy(policy_id, **update_kwargs)
    
    if not success:
        raise NotFoundError(f'Policy {policy_id} not found or not launched')
    
    # If scope or severity changed, trigger re-scan
    if 'scope' in update_kwargs or 'severity' in update_kwargs:
        try:
            lambda_client = boto3.client('lambda')
            scan_payload = {
                'policy_id': policy_id,
                'scan_type': 'bootstrap'  # Re-scan with new configuration
            }
            info(f"Triggering re-scan for updated policy {policy_id}")
            lambda_client.invoke(
                FunctionName='qrie_policy_scanner',
                InvocationType='Event',
                Payload=json.dumps(scan_payload)
            )
            info(f"Re-scan triggered for policy {policy_id}")
        except Exception as scan_err:
            error(f"Failed to trigger re-scan for policy {policy_id}: {scan_err}\n{traceback.format_exc()}")
    
    info(f"Successfully updated policy {policy_id}")
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': f'Policy {policy_id} updated successfully'})
    }


def handle_delete_policy(policy_id, headers):
    """Handle DELETE /policies/{policy_id} - delete policy and purge all findings"""
    info(f"Delete policy request: policy_id={policy_id}")
    
    # Verify policy exists and is launched
    launched_policy = get_policy_manager().get_launched_policy(policy_id)
    if not launched_policy:
        raise NotFoundError(f'Policy {policy_id} not found or not launched')
    
    # Purge all findings for this policy
    purged_count = 0
    try:
        info(f"Deleting policy {policy_id}, purging findings")
        findings_manager = FindingsManager()
        purged_count = findings_manager.purge_findings_for_policy(policy_id)
        info(f"Purged {purged_count} findings for policy {policy_id}")
    except Exception as purge_err:
        error(f"Failed to purge findings for policy {policy_id}: {purge_err}\n{traceback.format_exc()}")
        raise
    
    # Delete the policy from qrie_policies table
    try:
        get_policy_manager().delete_launched_policy(policy_id)
        info(f"Successfully deleted policy {policy_id}")
    except Exception as delete_err:
        error(f"Failed to delete policy {policy_id}: {delete_err}\n{traceback.format_exc()}")
        raise
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'message': f'Policy {policy_id} deleted successfully',
            'findings_deleted': purged_count
        })
    }
