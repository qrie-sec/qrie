"""
S3 Inventory Generation Module
"""
import time
from typing import Dict
import traceback
import boto3, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.logger import error
from data_access.inventory_manager import InventoryManager

def generate_s3_inventory(account_id: str, inventory_manager, cached: bool = False) -> Dict:
    """Generate S3 inventory for an account"""
    # Return cached data if available and recent
    existing_resources = inventory_manager.get_resources_by_account_service(f"{account_id}_s3")
    if existing_resources and cached:
        return {'resources_found': len(existing_resources), 'cached': True}
    
    start_time = time.time()
    try:
        from cross_account import get_cross_account_session
        session = get_cross_account_session(account_id, 'us-east-1')
        s3_client = session.client('s3')
        
        # List all buckets
        response = s3_client.list_buckets()
        buckets = response.get('Buckets', [])
        
        resources_found = 0
        resources = []
        for bucket in buckets:
            bucket_name = bucket['Name']
            bucket_arn = f"arn:aws:s3:::{bucket_name}"
            
            try:
                # Get bucket configuration
                bucket_config = {
                    'Name': bucket_name,
                    'CreationDate': bucket['CreationDate'].isoformat() if bucket.get('CreationDate') else None
                }
                
                # Get public access block configuration
                try:
                    pab_response = s3_client.get_public_access_block(Bucket=bucket_name)
                    bucket_config['PublicAccessBlockConfiguration'] = pab_response.get('PublicAccessBlockConfiguration', {})
                except s3_client.exceptions.NoSuchPublicAccessBlockConfiguration:
                    # No public access block configured - this is expected for many buckets
                    bucket_config['PublicAccessBlockConfiguration'] = {}
                
                # Store in inventory
                inventory_manager.upsert_resource(account_id, 's3', bucket_arn, bucket_config)
                resources_found += 1
                resource = {
                    'service': 's3',
                    'account_id': account_id,
                    'resource_id': bucket_arn,
                    'resource_data': bucket_config
                }
                resources.append(resource)
            except Exception as e:
                error(f"Error processing bucket {bucket_name}: {str(e)}\n{traceback.format_exc()}")
                continue
        
        return {
            'service': 's3',
            'account_id': account_id,
            'resources_found': resources_found, 
            'cached': False,
            'execution_time_seconds': time.time() - start_time
        }
        
    except Exception as e:
        error(f"Error generating S3 inventory for account {account_id}: {str(e)}\n{traceback.format_exc()}")
        return {
            'service': 's3',
            'account_id': account_id,
            'resources_found': 0,
            'cached': False,
            'execution_time_seconds': time.time() - start_time,
            'error': str(e)
        }
