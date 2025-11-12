"""
Cross-account utilities for QOP lambdas to access customer AWS accounts.
"""
import boto3
import os
from typing import Dict, Optional
from botocore.exceptions import ClientError


# Set external ID at module load time
_qop_account_id = boto3.client('sts').get_caller_identity()['Account']
EXTERNAL_ID = f"qrie-{_qop_account_id}-2024"

def get_cross_account_session(customer_account_id: str, region: str) -> boto3.Session:
    
    role_arn = f"arn:aws:iam::{customer_account_id}:role/QrieReadOnly-{customer_account_id}"
    
    sts_client = boto3.client('sts')
    
    try:
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=f"qrie-policy-eval-{customer_account_id}",
            ExternalId=EXTERNAL_ID,
            DurationSeconds=3600  # 1 hour
        )
        
        credentials = response['Credentials']
        
        return boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=region
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDenied':
            raise ClientError(
                error_response={
                    'Error': {
                        'Code': 'CrossAccountAccessDenied',
                        'Message': f'Failed to assume role in customer account {customer_account_id}. Check role trust policy and external ID.'
                    }
                },
                operation_name='AssumeRole'
            )
        raise


# Alias for backward compatibility with tests
get_session = get_cross_account_session
