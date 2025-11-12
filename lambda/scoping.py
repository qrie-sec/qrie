"""
Shared scoping logic for policy evaluation.
Handles account metadata caching and scope evaluation.
"""
import os
import boto3
from typing import Dict, Optional
from functools import lru_cache
from policy_definition import ScopeConfig

# Cache for account metadata to avoid repeated API calls
_account_metadata_cache: Dict[str, Dict] = {}

def should_evaluate_resource(account_id: str, resource_arn: str, scope: ScopeConfig) -> bool:
    """
    Determine if a resource should be evaluated based on scope configuration.
    
    Args:
        account_id: AWS account ID
        resource_arn: Resource ARN
        scope: Scope configuration
        
    Returns:
        True if resource should be evaluated, False otherwise
    """
    # Check account-level scoping first (most common)
    if not _account_in_scope(account_id, scope):
        return False
    
    # TODO: Add resource-level scoping (tags, etc.) when needed
    # For now, if account is in scope, evaluate all resources in that account
    return True

def _account_in_scope(account_id: str, scope: ScopeConfig) -> bool:
    """Check if account is in scope based on include/exclude lists and tags"""
    
    # Check explicit include/exclude account lists
    if scope.include_accounts and account_id not in scope.include_accounts:
        return False
    
    if scope.exclude_accounts and account_id in scope.exclude_accounts:
        return False
    
    # Check account tags if specified
    if scope.include_tags or scope.exclude_tags:
        account_tags = _get_account_tags(account_id)
        
        # Check include tags - account must have at least one matching tag
        if scope.include_tags:
            has_include_tag = False
            for tag_key, tag_values in scope.include_tags.items():
                account_tag_value = account_tags.get(tag_key)
                if account_tag_value and account_tag_value in tag_values:
                    has_include_tag = True
                    break
            if not has_include_tag:
                return False
        
        # Check exclude tags - account must not have any matching tag
        if scope.exclude_tags:
            for tag_key, tag_values in scope.exclude_tags.items():
                account_tag_value = account_tags.get(tag_key)
                if account_tag_value and account_tag_value in tag_values:
                    return False
    
    # Check OU paths if specified
    if scope.include_ou_paths or scope.exclude_ou_paths:
        account_ou_path = _get_account_ou_path(account_id)
        
        # Check include OU paths
        if scope.include_ou_paths:
            has_include_ou = False
            for ou_path in scope.include_ou_paths:
                if account_ou_path and account_ou_path.startswith(ou_path):
                    has_include_ou = True
                    break
            if not has_include_ou:
                return False
        
        # Check exclude OU paths
        if scope.exclude_ou_paths:
            for ou_path in scope.exclude_ou_paths:
                if account_ou_path and account_ou_path.startswith(ou_path):
                    return False
    
    return True

@lru_cache(maxsize=128)
def _get_account_tags(account_id: str) -> Dict[str, str]:
    """Get account tags with caching"""
    if account_id in _account_metadata_cache:
        return _account_metadata_cache[account_id].get('tags', {})
    
    # This would need cross-account access to the customer's Organizations
    # For now, return empty dict - implement when cross-account access is ready
    tags = {}
    
    # Cache the result
    if account_id not in _account_metadata_cache:
        _account_metadata_cache[account_id] = {}
    _account_metadata_cache[account_id]['tags'] = tags
    
    return tags

@lru_cache(maxsize=128)
def _get_account_ou_path(account_id: str) -> Optional[str]:
    """Get account OU path with caching"""
    if account_id in _account_metadata_cache:
        return _account_metadata_cache[account_id].get('ou_path')
    
    # This would need cross-account access to the customer's Organizations
    # For now, return None - implement when cross-account access is ready
    ou_path = None
    
    # Cache the result
    if account_id not in _account_metadata_cache:
        _account_metadata_cache[account_id] = {}
    _account_metadata_cache[account_id]['ou_path'] = ou_path
    
    return ou_path

def clear_account_cache():
    """Clear the account metadata cache"""
    global _account_metadata_cache
    _account_metadata_cache.clear()
    _get_account_tags.cache_clear()
    _get_account_ou_path.cache_clear()
