"""
Common utilities shared across the QRIE system.
"""
import os
import time
import boto3
from typing import List, Dict, Optional
from functools import lru_cache

# Global variables for lazy initialization
_ddb = None
_accounts_table = None
_resources_table = None
_findings_table = None
_policies_table = None
_summary_table = None

def get_dynamodb_resource():
    """Get DynamoDB resource with lazy initialization"""
    global _ddb
    if _ddb is None:
        _ddb = boto3.resource('dynamodb')
    return _ddb

def get_table(table_name_env_var, default_name=None):
    """Get DynamoDB table with lazy initialization"""
    table_name = os.environ.get(table_name_env_var, default_name)
    if not table_name:
        raise ValueError(f"Environment variable {table_name_env_var} not set")
    return get_dynamodb_resource().Table(table_name)

# Convenience functions for specific tables
def get_accounts_table():
    """Get accounts table with lazy initialization"""
    return get_table('ACCOUNTS_TABLE')

def get_resources_table():
    """Get resources table with lazy initialization"""
    return get_table('RESOURCES_TABLE')

def get_findings_table():
    """Get findings table with lazy initialization"""
    return get_table('FINDINGS_TABLE')

def get_policies_table():
    """Get policies table with lazy initialization"""
    return get_table('POLICIES_TABLE', 'qrie_policies')

def get_summary_table():
    """Get summary table with lazy initialization (for caching dashboard, findings summaries, etc.)"""
    return get_table('SUMMARY_TABLE', 'qrie_summary')

# Import SUPPORTED_SERVICES from services module
# This is here for backward compatibility - prefer importing from services directly
try:
    from services import SUPPORTED_SERVICES
except ImportError:
    # Fallback if services module not available (e.g., during testing)
    SUPPORTED_SERVICES = ["s3", "ec2", "iam"]

# ============================================================================
# ARN UTILITIES
# ============================================================================

def get_account_from_arn(arn: str) -> str:
    """Extract account ID from ARN. Returns empty string for S3 bucket ARNs."""
    parts = arn.split(':')
    if len(parts) < 5:
        raise ValueError(f"Invalid ARN format: {arn}")
    return parts[4]

def get_service_from_arn(arn: str) -> str:
    """Extract service name from ARN (e.g., 's3', 'ec2', 'iam')."""
    parts = arn.split(':')
    if len(parts) < 3:
        raise ValueError(f"Invalid ARN format: {arn}")
    return parts[2]

def get_customer_accounts() -> List[Dict]:
    """
    Get all customer accounts from accounts table with auto-pagination.
    
    Returns:
        List of account dicts with account_id and metadata
    """
    table = get_accounts_table()
    accounts = []
    last_key = None
    
    while True:
        if last_key:
            response = table.scan(ExclusiveStartKey=last_key)
        else:
            response = table.scan()
        
        accounts.extend(response.get('Items', []))
        
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
    
    return accounts

def get_customer_account_ids() -> List[str]:
    """Get list of customer account IDs only"""
    accounts = get_customer_accounts()
    return [account.get('account_id') for account in accounts if account.get('account_id')]
