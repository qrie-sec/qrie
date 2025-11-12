"""
S3 service-specific support for inventory generation, event processing, and resource description.
"""
import boto3
from typing import Dict, List, Optional
from common.logger import debug, info, error


# ============================================================================
# ARN EXTRACTION FROM EVENTS
# ============================================================================

def extract_arn_from_event(detail: dict) -> Optional[str]:
    """
    Extract S3 bucket ARN from CloudTrail event detail.
    
    Args:
        detail: CloudTrail event detail dict
        
    Returns:
        S3 bucket ARN or None if cannot be extracted
        
    Note:
        CreateBucket events have empty resources[] array, so we construct
        ARN from requestParameters.bucketName
    """
    # Method 1: Check resources array (most events)
    resources = detail.get('resources', [])
    if resources and len(resources) > 0:
        arn = resources[0].get('ARN')
        if arn:
            return arn
    
    # Method 2: Construct from bucketName (CreateBucket fallback)
    request_params = detail.get('requestParameters', {})
    bucket_name = request_params.get('bucketName')
    if bucket_name:
        return f"arn:aws:s3:::{bucket_name}"
    
    return None


# ============================================================================
# RESOURCE DESCRIPTION
# ============================================================================

def describe_resource(arn: str, account_id: str, s3_client=None) -> dict:
    """
    Describe S3 bucket configuration.
    
    Args:
        arn: S3 bucket ARN (format: arn:aws:s3:::bucket-name)
        account_id: AWS account ID (for cross-account access)
        s3_client: Optional pre-configured S3 client (for testing)
        
    Returns:
        Bucket configuration dict with all relevant settings
        
    Raises:
        Exception: If bucket cannot be described
    """
    bucket_name = arn.split(':::')[-1]
    
    # Use provided client or create one with cross-account access
    if s3_client is None:
        s3_client = _get_cross_account_s3_client(account_id)
    
    config = {
        'Name': bucket_name,
        'ARN': arn
    }
    
    # Get bucket location
    location = s3_client.get_bucket_location(Bucket=bucket_name)
    config['Location'] = location.get('LocationConstraint') or 'us-east-1'
    
    # Get public access block configuration (critical for security policies)
    try:
        pab = s3_client.get_public_access_block(Bucket=bucket_name)
        config['PublicAccessBlockConfiguration'] = pab.get('PublicAccessBlockConfiguration', {})
    except s3_client.exceptions.NoSuchPublicAccessBlockConfiguration:
        config['PublicAccessBlockConfiguration'] = None
    except Exception as e:
        debug(f"Could not get public access block for {bucket_name}: {str(e)}")
    
    # Get versioning
    versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
    config['Versioning'] = versioning.get('Status', 'Disabled')
    
    # Get encryption
    try:
        encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
        config['Encryption'] = encryption.get('ServerSideEncryptionConfiguration', {})
    except s3_client.exceptions.ServerSideEncryptionConfigurationNotFoundError:
        config['Encryption'] = None
    except Exception as e:
        debug(f"Could not get encryption for {bucket_name}: {str(e)}")
    
    # Get logging
    try:
        logging = s3_client.get_bucket_logging(Bucket=bucket_name)
        config['Logging'] = logging.get('LoggingEnabled', {})
    except Exception as e:
        debug(f"Could not get logging for {bucket_name}: {str(e)}")
    
    return config


# ============================================================================
# INVENTORY GENERATION
# ============================================================================

def list_resources(account_id: str, s3_client=None) -> dict:
    """
    List all S3 buckets in an account.
    
    Args:
        account_id: AWS account ID
        s3_client: Optional pre-configured S3 client (for testing)
        
    Returns:
        Dict with 'resources' (list of bucket configs) and 'failed_count' (int)
    """
    if s3_client is None:
        s3_client = _get_cross_account_s3_client(account_id)
    
    buckets = []
    failed_count = 0
    
    try:
        response = s3_client.list_buckets()
        bucket_list = response.get('Buckets', [])
        
        info(f"Found {len(bucket_list)} S3 buckets in account {account_id}")
        
        for bucket in bucket_list:
            bucket_name = bucket['Name']
            arn = f"arn:aws:s3:::{bucket_name}"
            
            try:
                config = describe_resource(arn, account_id, s3_client)
                buckets.append(config)
            except Exception as e:
                error(f"Error describing bucket {bucket_name}: {str(e)}")
                failed_count += 1
                continue
        
        return {
            'resources': buckets,
            'failed_count': failed_count
        }
    
    except Exception as e:
        error(f"Error listing S3 buckets for account {account_id}: {str(e)}")
        raise


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_cross_account_s3_client(account_id: str):
    """
    Get S3 client with cross-account access.
    
    Args:
        account_id: AWS account ID to access
        
    Returns:
        Configured boto3 S3 client
    """
    sts = boto3.client('sts')
    role_arn = f"arn:aws:iam::{account_id}:role/QrieInventoryRole"
    
    assumed_role = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=f"qrie-s3-access-{account_id}"
    )
    
    credentials = assumed_role['Credentials']
    return boto3.client(
        's3',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )
