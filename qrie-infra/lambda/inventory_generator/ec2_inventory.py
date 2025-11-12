"""
EC2 Inventory Generation Module
"""
import time
from typing import Dict
import traceback
import boto3, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.logger import error

def generate_ec2_inventory(account_id: str, inventory_manager, cached: bool = False) -> Dict:
    """Generate EC2 inventory for an account"""
    start_time = time.time()
    
    try:
        from cross_account import get_session
        session = get_session(account_id, 'us-east-1')  # Default region
        ec2_client = session.client('ec2')
        
        # Get all EC2 instances
        response = ec2_client.describe_instances()
        resources_found = 0
        
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instance_id = instance['InstanceId']
                arn = f"arn:aws:ec2:us-east-1:{account_id}:instance/{instance_id}"
                
                # Store instance configuration
                config = {
                    'InstanceId': instance_id,
                    'InstanceType': instance.get('InstanceType'),
                    'State': instance.get('State', {}),
                    'SecurityGroups': instance.get('SecurityGroups', []),
                    'SubnetId': instance.get('SubnetId'),
                    'VpcId': instance.get('VpcId'),
                    'PublicIpAddress': instance.get('PublicIpAddress'),
                    'PrivateIpAddress': instance.get('PrivateIpAddress')
                }
                
                inventory_manager.upsert_resource(account_id, 'ec2', arn, config)
                resources_found += 1
        
        execution_time = time.time() - start_time
        return {
            'service': 'ec2',
            'account_id': account_id,
            'resources_found': resources_found,
            'cached': cached,
            'execution_time_seconds': execution_time
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        error(f"Error generating EC2 inventory for account {account_id}: {str(e)}\n{traceback.format_exc()}")
        return {
            'service': 'ec2',
            'account_id': account_id,
            'resources_found': 0,
            'cached': False,
            'execution_time_seconds': execution_time,
            'error': str(e)
        }
