"""
EC2 service-specific support for inventory generation, event processing, and resource description.
"""
from typing import Dict, List, Optional


# ============================================================================
# ARN EXTRACTION FROM EVENTS
# ============================================================================

def extract_arn_from_event(detail: dict) -> Optional[str]:
    """
    Extract EC2 resource ARN from CloudTrail event detail.
    
    Args:
        detail: CloudTrail event detail dict
        
    Returns:
        EC2 resource ARN or None if cannot be extracted
        
    TODO: Implement EC2 ARN extraction from CloudTrail events
    """
    # Check resources array first
    resources = detail.get('resources', [])
    if resources and len(resources) > 0:
        arn = resources[0].get('ARN')
        if arn:
            return arn
    
    # TODO: Construct ARN from requestParameters for events without resources array
    # Examples: RunInstances, CreateVolume, CreateSecurityGroup
    
    return None


# ============================================================================
# RESOURCE DESCRIPTION
# ============================================================================

def describe_resource(arn: str, account_id: str, ec2_client=None) -> dict:
    """
    Describe EC2 resource configuration.
    
    Args:
        arn: EC2 resource ARN
        account_id: AWS account ID (for cross-account access)
        ec2_client: Optional pre-configured EC2 client (for testing)
        
    Returns:
        Resource configuration dict
        
    TODO: Implement EC2 resource description
    """
    raise NotImplementedError("EC2 resource description not yet implemented")


# ============================================================================
# INVENTORY GENERATION
# ============================================================================

def list_resources(account_id: str, ec2_client=None) -> List[Dict]:
    """
    List all EC2 resources in an account.
    
    Args:
        account_id: AWS account ID
        ec2_client: Optional pre-configured EC2 client (for testing)
        
    Returns:
        List of resource configuration dicts
        
    TODO: Implement EC2 inventory generation
    """
    raise NotImplementedError("EC2 inventory generation not yet implemented")
