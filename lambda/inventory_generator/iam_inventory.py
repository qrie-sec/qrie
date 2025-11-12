"""
IAM Inventory Generation Module
"""
import time
from typing import Dict
import traceback
import boto3, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.logger import error
from data_access.inventory_manager import InventoryManager

def generate_iam_inventory(account_id: str, inventory_manager, cached: bool = False) -> Dict:
    """Generate IAM inventory for an account"""
    start_time = time.time()
    
    try:
        from cross_account import get_session
        session = get_session(account_id, 'us-east-1')  # IAM is global but needs a region
        iam_client = session.client('iam')
        
        resources_found = 0
        
        # Get IAM users
        paginator = iam_client.get_paginator('list_users')
        for page in paginator.paginate():
            for user in page.get('Users', []):
                user_name = user['UserName']
                arn = f"arn:aws:iam::{account_id}:user/{user_name}"
                
                try:
                    config = {
                        'UserName': user_name,
                        'UserId': user.get('UserId'),
                        'Path': user.get('Path'),
                        'CreateDate': user.get('CreateDate').isoformat() if user.get('CreateDate') else None,
                        'PasswordLastUsed': user.get('PasswordLastUsed').isoformat() if user.get('PasswordLastUsed') else None
                    }
                    
                    inventory_manager.upsert_resource(account_id, 'iam', arn, config)
                    resources_found += 1
                except Exception as e:
                    error(f"Error processing user {user_name}: {str(e)}\n{traceback.format_exc()}")
                    continue
        
        # Get IAM roles
        paginator = iam_client.get_paginator('list_roles')
        for page in paginator.paginate():
            for role in page.get('Roles', []):
                role_name = role['RoleName']
                arn = role['Arn']
                
                config = {
                    'RoleName': role_name,
                    'RoleId': role.get('RoleId'),
                    'Path': role.get('Path'),
                    'CreateDate': role.get('CreateDate').isoformat() if role.get('CreateDate') else None,
                    'AssumeRolePolicyDocument': role.get('AssumeRolePolicyDocument'),
                    'MaxSessionDuration': role.get('MaxSessionDuration')
                }
                
                inventory_manager.upsert_resource(account_id, 'iam', arn, config)
                resources_found += 1
        
        execution_time = time.time() - start_time
        return {
            'service': 'iam',
            'account_id': account_id,
            'resources_found': resources_found,
            'cached': cached,
            'execution_time_seconds': execution_time
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        error(f"Error generating IAM inventory for account {account_id}: {str(e)}\n{traceback.format_exc()}")
        return {
            'service': 'iam',
            'account_id': account_id,
            'resources_found': 0,
            'cached': False,
            'execution_time_seconds': execution_time,
            'error': str(e)
        }
