"""Findings API - Handles security findings queries for the UI."""
import os
import json
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.exceptions import ValidationError
from data_access.findings_manager import FindingsManager

# Initialize manager lazily to avoid import-time dependencies
findings_manager = None

def get_findings_manager():
    global findings_manager
    if findings_manager is None:
        findings_manager = FindingsManager()
    return findings_manager

# ==================================
#     HANDLER FUNCTIONS
# ==================================
# These functions are called by the API handler

def handle_list_findings_paginated(query_params, headers):
    """Handle GET /findings with optional filtering and pagination"""
    
    # Optional parameters
    account = query_params.get('account')
    policy = query_params.get('policy')
    state = query_params.get('state')  # 'ACTIVE' or 'RESOLVED'
    severity = query_params.get('severity')
    page_size = int(query_params.get('page_size', 50))
    next_token = query_params.get('next_token')
    
    # Validate page size
    if page_size > 100:
        raise ValidationError('page_size cannot be greater than 100')
    
    # Validate state filter
    if state and state not in ['ACTIVE', 'RESOLVED']:
        raise ValidationError('state must be ACTIVE or RESOLVED')
    
    # Get paginated findings based on filters
    result = get_findings_manager().get_findings_paginated(
        account_id=account,
        policy_id=policy,
        state_filter=state,
        severity_filter=severity,
        page_size=page_size,
        next_token=next_token
    )
    
    # Convert Finding objects to dicts for JSON serialization
    findings_data = []
    for finding in result['findings']:
        findings_data.append({
            'arn': finding.arn,
            'policy': finding.policy,
            'account_service': finding.account_service,
            'severity': finding.severity,
            'state': finding.state,
            'first_seen': finding.first_seen,
            'last_evaluated': finding.last_evaluated,
            'evidence': finding.evidence
        })
    
    response_data = {
        'findings': findings_data
    }
    
    if 'next_token' in result:
        response_data['next_token'] = result['next_token']
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response_data)
    }

def handle_get_findings_summary(query_params, headers):
    """Handle GET /summary/findings?account=<account_id>"""
    account_id = query_params.get('account')
    
    summary = get_findings_manager().get_findings_summary(account_id)
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(summary)
    }
