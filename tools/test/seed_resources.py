#!/usr/bin/env python3
"""
E2E Testing Script - Creates real AWS resources for testing qrie system
"""
import boto3
import argparse
import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Add lambda directory to path
lambda_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'qrie-infra', 'lambda')
sys.path.append(lambda_dir)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
RESOURCE_TAG_KEY = 'qrie-test'
RESOURCE_TAG_VALUE = 'true'
RESOURCE_PREFIX = 'qrie-test'

def get_table_names():
    """Get table names from environment or use defaults"""
    return {
        'accounts': os.getenv('ACCOUNTS_TABLE', 'qrie_accounts'),
        'resources': os.getenv('RESOURCES_TABLE', 'qrie_resources'),
        'findings': os.getenv('FINDINGS_TABLE', 'qrie_findings'),
        'policies': os.getenv('POLICIES_TABLE', 'qrie_policies')
    }

def ensure_account_registered(account_id, region, profile):
    """Ensure the test account is registered in qrie_accounts table"""
    logger.info(f"Ensuring account {account_id} is registered...")
    
    session = boto3.Session(profile_name=profile, region_name=region)
    dynamodb = session.resource('dynamodb')
    table_names = get_table_names()
    accounts_table = dynamodb.Table(table_names['accounts'])
    
    try:
        response = accounts_table.get_item(Key={'AccountId': account_id})
        if 'Item' in response:
            logger.info(f"Account {account_id} already registered")
            return
        
        accounts_table.put_item(Item={
            'AccountId': account_id,
            'Status': 'active',
            'OnboardedAt': datetime.utcnow().isoformat() + 'Z',
            'LastInventoryScan': datetime.utcnow().isoformat() + 'Z'
        })
        logger.info(f"✓ Account {account_id} registered successfully")
    except Exception as e:
        logger.error(f"Error registering account: {str(e)}")
        raise

def get_all_policy_ids():
    """Get all policy IDs"""
    return [
        'S3BucketPublicReadProhibited', 'S3BucketVersioningEnabled', 'S3BucketEncryptionEnabled',
        'EC2EBSEncryptionEnabled', 'EC2PublicIPProhibited',
        'IAMPasswordPolicyCompliant', 'IAMAccessKeyNotRotated', 'IAMUserMFAEnabled',
        'RDSPublicAccessProhibited', 'RDSEncryptionEnabled', 'RDSBackupEnabled'
    ]

def ensure_policies_active(region, profile):
    """Ensure all policies are launched with default scope"""
    logger.info("Ensuring all policies are active with default scope...")
    
    session = boto3.Session(profile_name=profile, region_name=region)
    dynamodb = session.resource('dynamodb')
    table_names = get_table_names()
    policies_table = dynamodb.Table(table_names['policies'])
    
    policy_ids = get_all_policy_ids()
    launched_count = 0
    
    for policy_id in policy_ids:
        try:
            response = policies_table.get_item(Key={'PolicyId': policy_id})
            if 'Item' in response:
                item = response['Item']
                if item.get('Status') == 'active':
                    continue
                policies_table.update_item(
                    Key={'PolicyId': policy_id},
                    UpdateExpression='SET #status = :status, UpdatedAt = :updated',
                    ExpressionAttributeNames={'#status': 'Status'},
                    ExpressionAttributeValues={
                        ':status': 'active',
                        ':updated': datetime.utcnow().isoformat() + 'Z'
                    }
                )
                launched_count += 1
            else:
                policies_table.put_item(Item={
                    'PolicyId': policy_id,
                    'Status': 'active',
                    'Scope': {},
                    'CreatedAt': datetime.utcnow().isoformat() + 'Z',
                    'UpdatedAt': datetime.utcnow().isoformat() + 'Z'
                })
                launched_count += 1
        except Exception as e:
            logger.error(f"Error processing policy {policy_id}: {str(e)}")
            continue
    
    if launched_count > 0:
        logger.info(f"✓ {launched_count} policies launched/updated")
    else:
        logger.info("✓ All policies already active")

def create_s3_resources(account_id, region, profile, compliant=False):
    """Create S3 buckets for testing"""
    logger.info(f"Creating S3 resources (compliant={compliant})...")
    session = boto3.Session(profile_name=profile, region_name=region)
    s3 = session.client('s3')
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{account_id}'
    
    try:
        try:
            s3.head_bucket(Bucket=bucket_name)
            exists = True
        except:
            exists = False
        
        if not exists:
            if region == 'us-east-1':
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
            logger.info(f"  ✓ Created bucket: {bucket_name}")
        
        s3.put_bucket_tagging(Bucket=bucket_name, Tagging={'TagSet': [
            {'Key': RESOURCE_TAG_KEY, 'Value': RESOURCE_TAG_VALUE},
            {'Key': 'Purpose', 'Value': 'E2E Testing'}
        ]})
        
        if compliant:
            s3.put_public_access_block(Bucket=bucket_name, PublicAccessBlockConfiguration={
                'BlockPublicAcls': True, 'IgnorePublicAcls': True,
                'BlockPublicPolicy': True, 'RestrictPublicBuckets': True
            })
            s3.put_bucket_versioning(Bucket=bucket_name, VersioningConfiguration={'Status': 'Enabled'})
            s3.put_bucket_encryption(Bucket=bucket_name, ServerSideEncryptionConfiguration={
                'Rules': [{'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}, 'BucketKeyEnabled': True}]
            })
            logger.info(f"  ✓ Bucket {bucket_name} configured as COMPLIANT")
        else:
            s3.delete_public_access_block(Bucket=bucket_name)
            s3.put_bucket_versioning(Bucket=bucket_name, VersioningConfiguration={'Status': 'Suspended'})
            try:
                s3.delete_bucket_encryption(Bucket=bucket_name)
            except:
                pass
            logger.info(f"  ✓ Bucket {bucket_name} configured as NON-COMPLIANT")
        
        return [bucket_name]
    except Exception as e:
        logger.error(f"Error creating S3 resources: {str(e)}")
        raise

def create_iam_resources(account_id, region, profile, compliant=False):
    """Create IAM resources for testing"""
    logger.info(f"Creating IAM resources (compliant={compliant})...")
    session = boto3.Session(profile_name=profile, region_name=region)
    iam = session.client('iam')
    user_name = f'{RESOURCE_PREFIX}-user-{account_id}'
    
    try:
        if compliant:
            iam.update_account_password_policy(
                MinimumPasswordLength=14, RequireSymbols=True, RequireNumbers=True,
                RequireUppercaseCharacters=True, RequireLowercaseCharacters=True,
                AllowUsersToChangePassword=True, MaxPasswordAge=90, PasswordReusePrevention=24
            )
            logger.info(f"  ✓ Password policy configured as COMPLIANT")
        else:
            iam.update_account_password_policy(
                MinimumPasswordLength=8, RequireSymbols=False, RequireNumbers=False,
                RequireUppercaseCharacters=False, RequireLowercaseCharacters=False,
                AllowUsersToChangePassword=True
            )
            logger.info(f"  ✓ Password policy configured as NON-COMPLIANT")
        
        try:
            iam.get_user(UserName=user_name)
        except iam.exceptions.NoSuchEntityException:
            iam.create_user(UserName=user_name, Tags=[
                {'Key': RESOURCE_TAG_KEY, 'Value': RESOURCE_TAG_VALUE},
                {'Key': 'Purpose', 'Value': 'E2E Testing'}
            ])
            logger.info(f"  ✓ Created user: {user_name}")
        
        keys_response = iam.list_access_keys(UserName=user_name)
        for key in keys_response['AccessKeyMetadata']:
            iam.delete_access_key(UserName=user_name, AccessKeyId=key['AccessKeyId'])
        
        if not compliant:
            key_response = iam.create_access_key(UserName=user_name)
            logger.info(f"  ✓ Created access key (will appear as not rotated)")
        
        return [user_name]
    except Exception as e:
        logger.error(f"Error creating IAM resources: {str(e)}")
        raise

def cleanup_resources(account_id, region, profile, purge_findings=True):
    """Delete all test resources and optionally purge findings"""
    logger.info(f"Cleaning up resources for account {account_id}...")
    session = boto3.Session(profile_name=profile, region_name=region)
    s3 = session.client('s3')
    iam = session.client('iam')
    dynamodb = session.resource('dynamodb')
    
    resources_deleted = []
    
    # Delete S3 bucket
    try:
        bucket_name = f'{RESOURCE_PREFIX}-bucket-{account_id}'
        try:
            response = s3.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in response:
                objects = [{'Key': obj['Key']} for obj in response['Contents']]
                s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})
            s3.delete_bucket(Bucket=bucket_name)
            logger.info(f"  ✓ Deleted S3 bucket: {bucket_name}")
            resources_deleted.append(f's3://{bucket_name}')
        except s3.exceptions.NoSuchBucket:
            pass
    except Exception as e:
        logger.error(f"Error in S3 cleanup: {str(e)}")
    
    # Delete IAM user
    try:
        user_name = f'{RESOURCE_PREFIX}-user-{account_id}'
        try:
            keys_response = iam.list_access_keys(UserName=user_name)
            for key in keys_response['AccessKeyMetadata']:
                iam.delete_access_key(UserName=user_name, AccessKeyId=key['AccessKeyId'])
            iam.delete_user(UserName=user_name)
            logger.info(f"  ✓ Deleted IAM user: {user_name}")
            resources_deleted.append(f'iam::user/{user_name}')
        except iam.exceptions.NoSuchEntityException:
            pass
    except Exception as e:
        logger.error(f"Error in IAM cleanup: {str(e)}")
    
    # Purge findings
    if purge_findings:
        try:
            logger.info(f"Purging findings for account {account_id}...")
            table_names = get_table_names()
            findings_table = dynamodb.Table(table_names['findings'])
            
            response = findings_table.scan(
                FilterExpression='begins_with(AccountService, :account)',
                ProjectionExpression='ARN, Policy',
                ExpressionAttributeValues={':account': f'{account_id}_'}
            )
            
            findings = response['Items']
            while 'LastEvaluatedKey' in response:
                response = findings_table.scan(
                    FilterExpression='begins_with(AccountService, :account)',
                    ProjectionExpression='ARN, Policy',
                    ExpressionAttributeValues={':account': f'{account_id}_'},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                findings.extend(response['Items'])
            
            if findings:
                with findings_table.batch_writer() as batch:
                    for finding in findings:
                        batch.delete_item(Key={'ARN': finding['ARN'], 'Policy': finding['Policy']})
                logger.info(f"  ✓ Purged {len(findings)} findings")
            else:
                logger.info(f"  No findings found for account {account_id}")
        except Exception as e:
            logger.error(f"Error purging findings: {str(e)}")
    
    logger.info(f"✓ Cleanup complete - deleted {len(resources_deleted)} resources")
    return resources_deleted

def main():
    parser = argparse.ArgumentParser(
        description='E2E Testing - Create real AWS resources for testing qrie system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./seed_resources.py --non-compliant --account-id 050261919630 --region us-east-1 --profile qop
  ./seed_resources.py --compliant --account-id 050261919630 --region us-east-1 --profile qop
  ./seed_resources.py --remediate --account-id 050261919630 --region us-east-1 --profile qop
  ./seed_resources.py --cleanup --account-id 050261919630 --region us-east-1 --profile qop
        """
    )
    
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--non-compliant', action='store_true', help='Create non-compliant resources')
    mode.add_argument('--compliant', action='store_true', help='Create compliant resources')
    mode.add_argument('--remediate', action='store_true', help='Make resources compliant')
    mode.add_argument('--cleanup', action='store_true', help='Delete resources and purge findings')
    
    parser.add_argument('--account-id', required=True, help='AWS account ID')
    parser.add_argument('--region', required=True, help='AWS region')
    parser.add_argument('--profile', required=True, help='AWS profile')
    
    args = parser.parse_args()
    
    try:
        if args.cleanup:
            cleanup_resources(args.account_id, args.region, args.profile, purge_findings=True)
        else:
            ensure_account_registered(args.account_id, args.region, args.profile)
            ensure_policies_active(args.region, args.profile)
            
            compliant = args.compliant or args.remediate
            create_s3_resources(args.account_id, args.region, args.profile, compliant)
            create_iam_resources(args.account_id, args.region, args.profile, compliant)
            
            logger.info("✓ Resource creation complete")
            logger.info("Wait 2-3 minutes for CloudTrail events to process and findings to appear")
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
