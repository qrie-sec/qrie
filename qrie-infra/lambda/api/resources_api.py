"""Resources API - Handles resource inventory queries.
Supports UI endpoints: /resources, /accounts, /services.
"""
import os
import json
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_access.inventory_manager import InventoryManager
from common_utils import get_customer_accounts, SUPPORTED_SERVICES

# Initialize manager lazily to avoid import-time dependencies
inventory_manager = None

def get_inventory_manager():
    global inventory_manager
    if inventory_manager is None:
        inventory_manager = InventoryManager()
    return inventory_manager


# ==================================
#     HANDLER FUNCTIONS
# ==================================
# These functions are called by the unified API handler


def handle_list_resources_paginated(query_params, headers):
    """Handle GET /resources with optional filtering and pagination"""
    
    # Optional parameters
    account = query_params.get('account')
    resource_type = query_params.get('type')
    page_size = int(query_params.get('page_size', 50))
    next_token = query_params.get('next_token')
    
    # Validate page size
    if page_size > 100:
        page_size = 100
    
    # Use inventory_manager for paginated query
    result = get_inventory_manager().get_resources_paginated(
        account_id=account,
        service=resource_type,
        page_size=page_size,
        next_token=next_token
    )
    
    # Format resources to match UI expectations
    resources_data = []
    for resource in result['resources']:
        # Configuration might contain Decimal types from DynamoDB - convert to JSON-safe format
        config = resource.get('Configuration', {})
        if config:
            config = json.loads(json.dumps(config, default=str))
        
        resources_data.append({
            'arn': resource.get('ARN'),
            'account_service': resource.get('AccountService'),
            'last_seen_at': resource.get('LastSeenAt'),
            'configuration': config
        })
    
    response_data = {
        'resources': resources_data
    }
    
    if 'next_token' in result:
        response_data['next_token'] = result['next_token']
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response_data)
    }


def handle_list_accounts(headers):
    """Handle GET /accounts"""
    accounts = get_customer_accounts()
    
    # Format accounts for UI
    accounts_data = []
    for account in accounts:
        accounts_data.append({
            'account_id': account.get('AccountId'),
            'ou': account.get('ou', '')
        })
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(accounts_data)
    }

def handle_list_services(query_params, headers):
    """Handle GET /services?supported=true"""
    supported_only = query_params.get('supported') == 'true'
    
    if supported_only:
        services = SUPPORTED_SERVICES
    else:
        # For now, we only have supported services
        services = SUPPORTED_SERVICES
    
    # Format services for UI
    services_data = []
    for service in services:
        services_data.append({
            'service_name': service,
            'display_name': service.upper()  # Simple display name for now
        })
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(services_data)
    }

def handle_get_resources_summary(query_params, headers):
    """Handle GET /summary/resources?account=<account_id>"""
    account_id = query_params.get('account')
    
    summary = get_inventory_manager().get_resources_summary(account_id)
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(summary)
    }


# Note: Inventory generation functionality moved to separate internal tooling
# This API now only handles UI read operations
