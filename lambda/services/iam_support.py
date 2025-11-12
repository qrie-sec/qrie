"""
IAM service-specific support for inventory generation, event processing, and resource description.
"""
from typing import Dict, List, Optional


# ============================================================================
# ARN EXTRACTION FROM EVENTS
# ============================================================================

def extract_arn_from_event(detail: dict) -> Optional[str]:
    """
    Extract IAM resource ARN from CloudTrail event detail.
    
    Args:
        detail: CloudTrail event detail dict
        
    Returns:
        IAM resource ARN or None if cannot be extracted
        
    TODO: Implement IAM ARN extraction from CloudTrail events
    """
    # Check resources array first
    resources = detail.get('resources', [])
    if resources and len(resources) > 0:
        arn = resources[0].get('ARN')
        if arn:
            return arn
    
    # TODO: Construct ARN from requestParameters for events without resources array
    # Examples: CreateUser, CreateRole, PutUserPolicy
    
    return None


# ============================================================================
# RESOURCE DESCRIPTION
# ============================================================================

def describe_resource(arn: str, account_id: str, iam_client=None) -> dict:
    """
    Describe IAM resource configuration.
    
    Args:
        arn: IAM resource ARN
        account_id: AWS account ID (for cross-account access)
        iam_client: Optional pre-configured IAM client (for testing)
        
    Returns:
        Resource configuration dict
        
    TODO: Implement IAM resource description
    """
    raise NotImplementedError("IAM resource description not yet implemented")


# ============================================================================
# INVENTORY GENERATION
# ============================================================================

def list_resources(account_id: str, iam_client=None) -> List[Dict]:
    """
    List all IAM resources in an account.
    
    Args:
        account_id: AWS account ID
        iam_client: Optional pre-configured IAM client (for testing)
        
    Returns:
        List of resource configuration dicts
        
    TODO: Implement IAM inventory generation
    """
    raise NotImplementedError("IAM inventory generation not yet implemented")
