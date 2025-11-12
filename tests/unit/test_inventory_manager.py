"""
Unit tests for InventoryManager.
Tests inventory CRUD operations, resource generation, and caching.
"""
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock
import sys
import os
import json
import time
from datetime import datetime

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

from data_access.inventory_manager import InventoryManager


@pytest.fixture
def mock_table():
    """Mock DynamoDB table for testing"""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-resources',
            KeySchema=[
                {'AttributeName': 'AccountService', 'KeyType': 'HASH'},
                {'AttributeName': 'ARN', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'AccountService', 'AttributeType': 'S'},
                {'AttributeName': 'ARN', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        yield table


@pytest.fixture
def inventory_manager(mock_table):
    """InventoryManager instance with mocked table"""
    with patch('data_access.inventory_manager.get_resources_table', return_value=mock_table):
        manager = InventoryManager()
        return manager


@pytest.fixture
def sample_s3_resource():
    """Sample S3 resource configuration"""
    return {
        'arn': 'arn:aws:s3:::test-bucket',
        'account_id': '123456789012',
        'service': 's3',
        'resource_type': 'bucket',
        'configuration': {
            'BucketName': 'test-bucket',
            'CreationDate': '2023-01-01T00:00:00Z',
            'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        }
    }


class TestInventoryManager:
    """Test suite for InventoryManager"""

    def test_upsert_resource_new(self, inventory_manager, sample_s3_resource):
        """Test creating a new resource"""
        inventory_manager.upsert_resource(
            sample_s3_resource['account_id'],
            sample_s3_resource['service'],
            sample_s3_resource['arn'],
            sample_s3_resource['configuration'],
            int(time.time() * 1000)
        )
        
        # Verify resource was created
        account_service = f"{sample_s3_resource['account_id']}_{sample_s3_resource['service']}"
        response = inventory_manager.resource_table.get_item(
            Key={'AccountService': account_service, 'ARN': sample_s3_resource['arn']}
        )
        
        assert 'Item' in response
        item = response['Item']
        assert item['ARN'] == sample_s3_resource['arn']
        assert item['AccountService'] == account_service
        assert item['Configuration'] == sample_s3_resource['configuration']
        assert 'LastSeenAt' in item

    def test_upsert_resource_update_existing(self, inventory_manager, sample_s3_resource):
        """Test updating an existing resource"""
        # Create initial resource
        inventory_manager.upsert_resource(
            sample_s3_resource['account_id'],
            sample_s3_resource['service'],
            sample_s3_resource['arn'],
            sample_s3_resource['configuration'],
            int(time.time() * 1000)
        )
        
        # Update with new configuration
        updated_config = sample_s3_resource['configuration'].copy()
        updated_config['PublicAccessBlockConfiguration']['BlockPublicAcls'] = True
        
        inventory_manager.upsert_resource(
            sample_s3_resource['account_id'],
            sample_s3_resource['service'],
            sample_s3_resource['arn'],
            updated_config,
            int(time.time() * 1000)
        )
        
        # Verify update
        account_service = f"{sample_s3_resource['account_id']}_{sample_s3_resource['service']}"
        response = inventory_manager.resource_table.get_item(
            Key={'AccountService': account_service, 'ARN': sample_s3_resource['arn']}
        )
        
        item = response['Item']
        assert item['Configuration']['PublicAccessBlockConfiguration']['BlockPublicAcls'] is True

    def test_get_resource(self, inventory_manager, sample_s3_resource):
        """Test retrieving a specific resource"""
        # Create resource
        inventory_manager.upsert_resource(
            sample_s3_resource['account_id'],
            sample_s3_resource['service'],
            sample_s3_resource['arn'],
            sample_s3_resource['configuration'],
            int(time.time() * 1000)
        )
        
        # Retrieve resource (provide account_id for S3 resources)
        resource = inventory_manager.get_resource(sample_s3_resource['arn'], sample_s3_resource['account_id'])
        
        assert resource is not None
        assert resource['ARN'] == sample_s3_resource['arn']
        assert resource['Configuration'] == sample_s3_resource['configuration']

    def test_get_resource_nonexistent(self, inventory_manager):
        """Test retrieving a non-existent resource"""
        resource = inventory_manager.get_resource('arn:aws:s3:::nonexistent-bucket', '123456789012')
        assert resource is None

    def test_get_resources_by_account_service(self, inventory_manager, sample_s3_resource):
        """Test retrieving resources by account and service"""
        account_service = f"{sample_s3_resource['account_id']}_{sample_s3_resource['service']}"
        
        # Create multiple resources
        for i in range(3):
            arn = f"arn:aws:s3:::test-bucket-{i}"
            config = sample_s3_resource['configuration'].copy()
            config['BucketName'] = f"test-bucket-{i}"
            
            inventory_manager.upsert_resource(sample_s3_resource['account_id'], sample_s3_resource['service'], arn, config, int(time.time() * 1000))
        
        # Retrieve resources
        resources = inventory_manager.get_resources_by_account_service(account_service)
        
        assert len(resources) == 3
        assert all(r['AccountService'] == account_service for r in resources)
        
        bucket_names = {r['Configuration']['BucketName'] for r in resources}
        assert bucket_names == {'test-bucket-0', 'test-bucket-1', 'test-bucket-2'}

    def test_get_resources_by_account_service_with_limit(self, inventory_manager, sample_s3_resource):
        """Test retrieving resources with limit"""
        account_service = f"{sample_s3_resource['account_id']}_{sample_s3_resource['service']}"
        
        # Create multiple resources
        for i in range(5):
            arn = f"arn:aws:s3:::test-bucket-{i}"
            inventory_manager.upsert_resource(
                sample_s3_resource['account_id'],
                sample_s3_resource['service'],
                arn,
                {},
                int(time.time() * 1000)
            )
        
        # Retrieve with limit
        resources = inventory_manager.get_resources_by_account_service(account_service, limit=3)
        assert len(resources) <= 3

    def test_get_all_resources(self, inventory_manager, sample_s3_resource):
        """Test retrieving all resources"""
        # Create resources for different services
        s3_arn = 'arn:aws:s3:::test-bucket'
        ec2_arn = 'arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0'
        
        inventory_manager.upsert_resource('123456789012', 's3', s3_arn, {}, int(time.time() * 1000))
        inventory_manager.upsert_resource('123456789012', 'ec2', ec2_arn, {}, int(time.time() * 1000))
        
        resources = inventory_manager.get_all_resources()
        assert len(resources) == 2
        
        arns = {r['ARN'] for r in resources}
        assert arns == {s3_arn, ec2_arn}

    def test_delete_resource(self, inventory_manager, sample_s3_resource):
        """Test deleting a resource"""
        # Create resource
        inventory_manager.upsert_resource(
            sample_s3_resource['account_id'],
            sample_s3_resource['service'],
            sample_s3_resource['arn'],
            sample_s3_resource['configuration'],
            int(time.time() * 1000)
        )
        
        # Verify resource exists
        resource = inventory_manager.get_resource(sample_s3_resource['arn'], sample_s3_resource['account_id'])
        assert resource is not None
        
        # Delete resource
        inventory_manager.delete_resource(sample_s3_resource['arn'], sample_s3_resource['account_id'])
        
        # Verify resource is deleted
        resource = inventory_manager.get_resource(sample_s3_resource['arn'], sample_s3_resource['account_id'])
        assert resource is None

    def test_delete_resource_nonexistent(self, inventory_manager):
        """Test deleting a non-existent resource (should not raise error)"""
        # Should not raise an exception
        inventory_manager.delete_resource('arn:aws:s3:::nonexistent-bucket', '123456789012')

    def test_get_inventory_summary(self, inventory_manager):
        """Test getting inventory summary by service"""
        # Create resources for different services
        inventory_manager.upsert_resource('123456789012', 's3', 'arn:aws:s3:::bucket1', {}, int(time.time() * 1000))
        inventory_manager.upsert_resource('123456789012', 's3', 'arn:aws:s3:::bucket2', {}, int(time.time() * 1000))
        inventory_manager.upsert_resource('123456789012', 'ec2', 'arn:aws:ec2:us-east-1:123456789012:instance/i-123', {}, int(time.time() * 1000))
        
        summary = inventory_manager.get_inventory_summary('123456789012')
        
        assert summary == {'s3': 2, 'ec2': 1}

    def test_caching_behavior(self, inventory_manager):
        """Test that caching works correctly"""
        with patch('common_utils.get_customer_accounts') as mock_get_accounts:
            mock_get_accounts.return_value = [{'account_id': '123456789012'}]
            
            # First call
            accounts1 = inventory_manager._get_customer_accounts_cached()
            # Second call should use cache
            accounts2 = inventory_manager._get_customer_accounts_cached()
            
            assert accounts1 == accounts2
            # get_customer_accounts should be called only once due to caching
            assert mock_get_accounts.call_count == 1

    @patch('data_access.inventory_manager.get_resources_table')
    def test_manager_initialization(self, mock_get_table):
        """Test InventoryManager initialization"""
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        manager = InventoryManager()
        assert manager.resource_table == mock_table


    def test_resource_arn_parsing(self, inventory_manager):
        """Test ARN parsing for different resource types"""
        test_cases = [
            ('arn:aws:s3:::test-bucket', '123456789012', 's3'),
            ('arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0', '123456789012', 'ec2'),
            ('arn:aws:iam::123456789012:user/test-user', '123456789012', 'iam')
        ]
        
        for arn, expected_account, expected_service in test_cases:
            inventory_manager.upsert_resource(expected_account, expected_service, arn, {}, int(time.time() * 1000))
            
            # For S3, provide account_id; for others, ARN contains it
            if expected_service == 's3':
                resource = inventory_manager.get_resource(arn, expected_account)
            else:
                resource = inventory_manager.get_resource(arn)
            
            assert resource is not None
            assert resource['ARN'] == arn
            assert expected_service in resource['AccountService']

    def test_get_s3_resource_without_account_id_fails(self, inventory_manager):
        """Test that retrieving S3 resource without account_id raises ValueError (fail fast)"""
        # Create S3 resource
        s3_arn = 'arn:aws:s3:::test-bucket-scan'
        inventory_manager.upsert_resource('123456789012', 's3', s3_arn, {'BucketName': 'test-bucket-scan'}, int(time.time() * 1000))
        
        # Attempting to retrieve without account_id should raise ValueError
        with pytest.raises(ValueError, match="ARN does not contain account ID"):
            inventory_manager.get_resource(s3_arn)
