"""
Unit tests for InventoryManager caching functionality.
Tests the new 15-minute caching pattern with findings integration.
"""
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock
import sys
import os
from datetime import datetime, timezone, timedelta

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

from data_access.inventory_manager import InventoryManager


@pytest.fixture
def mock_tables():
    """Create all required mock tables"""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Resources table
        resources_table = dynamodb.create_table(
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
        
        # Summary table
        summary_table = dynamodb.create_table(
            TableName='test-summary',
            KeySchema=[
                {'AttributeName': 'Type', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'Type', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Findings table
        findings_table = dynamodb.create_table(
            TableName='test-findings',
            KeySchema=[
                {'AttributeName': 'ARN', 'KeyType': 'HASH'},
                {'AttributeName': 'Policy', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'ARN', 'AttributeType': 'S'},
                {'AttributeName': 'Policy', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        yield resources_table, summary_table, findings_table


@pytest.fixture
def inventory_manager_with_caching(mock_tables):
    """InventoryManager with all tables for caching tests"""
    resources_table, summary_table, findings_table = mock_tables
    
    with (
        patch('data_access.inventory_manager.get_resources_table', return_value=resources_table),
        patch('data_access.inventory_manager.get_summary_table', return_value=summary_table),
        patch('data_access.findings_manager.get_findings_table', return_value=findings_table),
        patch('data_access.findings_manager.get_summary_table', return_value=summary_table)
    ):
        manager = InventoryManager()
        yield manager, resources_table, summary_table, findings_table


class TestInventoryManagerCaching:
    """Test suite for inventory caching functionality"""
    
    def test_resources_summary_with_caching(self, inventory_manager_with_caching):
        """Test that resources summary uses 15-minute caching"""
        manager, resources_table, summary_table, findings_table = inventory_manager_with_caching
        
        # Add some test resources
        resources_table.put_item(Item={
            'AccountService': '123456789012_s3',
            'ARN': 'arn:aws:s3:::test-bucket-1',
            'LastSeenAt': datetime.now(timezone.utc).isoformat()
        })
        resources_table.put_item(Item={
            'AccountService': '123456789012_s3',
            'ARN': 'arn:aws:s3:::test-bucket-2',
            'LastSeenAt': datetime.now(timezone.utc).isoformat()
        })
        resources_table.put_item(Item={
            'AccountService': '123456789012_ec2',
            'ARN': 'arn:aws:ec2:us-east-1:123456789012:instance/i-123',
            'LastSeenAt': datetime.now(timezone.utc).isoformat()
        })
        
        # Add some test findings
        findings_table.put_item(Item={
            'ARN': 'arn:aws:s3:::test-bucket-1',
            'Policy': 'S3BucketPublic',
            'AccountService': '123456789012_s3',
            'Severity': 90,
            'State': 'ACTIVE',
            'FirstSeen': datetime.now(timezone.utc).isoformat(),
            'LastEvaluated': datetime.now(timezone.utc).isoformat(),
            'Evidence': {}
        })
        
        # First call - should compute and cache
        print("\n=== First call (cache miss) ===")
        summary1 = manager.get_resources_summary()
        
        # Verify structure
        assert 'total_resources' in summary1
        assert 'total_findings' in summary1
        assert 'critical_findings' in summary1
        assert 'high_findings' in summary1
        assert 'resource_types' in summary1
        
        assert summary1['total_resources'] == 3
        assert summary1['total_accounts'] == 1
        
        # Verify resource types structure
        assert len(summary1['resource_types']) == 2
        for rt in summary1['resource_types']:
            assert 'resource_type' in rt
            assert 'all_resources' in rt
            assert 'non_compliant' in rt
        
        # Verify cache was saved
        cache_response = summary_table.get_item(Key={'Type': 'resources_summary_all'})
        assert 'Item' in cache_response
        assert 'summary' in cache_response['Item']
        assert 'updated_at' in cache_response['Item']
        
        # Second call - should use cache
        print("\n=== Second call (cache hit) ===")
        summary2 = manager.get_resources_summary()
        
        # Should return same data
        assert summary2 == summary1
    
    def test_resources_summary_includes_findings_data(self, inventory_manager_with_caching):
        """Test that summary includes findings counts"""
        manager, resources_table, summary_table, findings_table = inventory_manager_with_caching
        
        # Add resources
        resources_table.put_item(Item={
            'AccountService': '123456789012_s3',
            'ARN': 'arn:aws:s3:::bucket1',
            'LastSeenAt': datetime.now(timezone.utc).isoformat()
        })
        
        # Add findings with different severities
        findings_table.put_item(Item={
            'ARN': 'arn:aws:s3:::bucket1',
            'Policy': 'CriticalPolicy',
            'AccountService': '123456789012_s3',
            'Severity': 95,
            'State': 'ACTIVE',
            'FirstSeen': datetime.now(timezone.utc).isoformat(),
            'LastEvaluated': datetime.now(timezone.utc).isoformat(),
            'Evidence': {}
        })
        findings_table.put_item(Item={
            'ARN': 'arn:aws:s3:::bucket1',
            'Policy': 'HighPolicy',
            'AccountService': '123456789012_s3',
            'Severity': 70,
            'State': 'ACTIVE',
            'FirstSeen': datetime.now(timezone.utc).isoformat(),
            'LastEvaluated': datetime.now(timezone.utc).isoformat(),
            'Evidence': {}
        })
        
        summary = manager.get_resources_summary()
        
        # Verify findings data is included
        assert summary['total_findings'] == 2
        assert summary['critical_findings'] == 1
        assert summary['high_findings'] == 1
    
    def test_resources_summary_non_compliant_counts(self, inventory_manager_with_caching):
        """Test that non_compliant counts are calculated correctly"""
        manager, resources_table, summary_table, findings_table = inventory_manager_with_caching
        
        # Add 3 S3 buckets
        for i in range(3):
            resources_table.put_item(Item={
                'AccountService': '123456789012_s3',
                'ARN': f'arn:aws:s3:::bucket-{i}',
                'LastSeenAt': datetime.now(timezone.utc).isoformat()
            })
        
        # Add 2 EC2 instances
        for i in range(2):
            resources_table.put_item(Item={
                'AccountService': '123456789012_ec2',
                'ARN': f'arn:aws:ec2:us-east-1:123456789012:instance/i-{i}',
                'LastSeenAt': datetime.now(timezone.utc).isoformat()
            })
        
        # Add findings for 2 S3 buckets and 1 EC2 instance
        findings_table.put_item(Item={
            'ARN': 'arn:aws:s3:::bucket-0',
            'Policy': 'S3Policy',
            'AccountService': '123456789012_s3',
            'Severity': 80,
            'State': 'ACTIVE',
            'FirstSeen': datetime.now(timezone.utc).isoformat(),
            'LastEvaluated': datetime.now(timezone.utc).isoformat(),
            'Evidence': {}
        })
        findings_table.put_item(Item={
            'ARN': 'arn:aws:s3:::bucket-1',
            'Policy': 'S3Policy',
            'AccountService': '123456789012_s3',
            'Severity': 80,
            'State': 'ACTIVE',
            'FirstSeen': datetime.now(timezone.utc).isoformat(),
            'LastEvaluated': datetime.now(timezone.utc).isoformat(),
            'Evidence': {}
        })
        findings_table.put_item(Item={
            'ARN': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0',
            'Policy': 'EC2Policy',
            'AccountService': '123456789012_ec2',
            'Severity': 60,
            'State': 'ACTIVE',
            'FirstSeen': datetime.now(timezone.utc).isoformat(),
            'LastEvaluated': datetime.now(timezone.utc).isoformat(),
            'Evidence': {}
        })
        
        summary = manager.get_resources_summary()
        
        # Find S3 and EC2 in resource_types
        s3_type = next(rt for rt in summary['resource_types'] if rt['resource_type'] == 's3')
        ec2_type = next(rt for rt in summary['resource_types'] if rt['resource_type'] == 'ec2')
        
        # Verify counts
        assert s3_type['all_resources'] == 3
        assert s3_type['non_compliant'] == 2
        assert ec2_type['all_resources'] == 2
        assert ec2_type['non_compliant'] == 1
    
    def test_resources_summary_per_account(self, inventory_manager_with_caching):
        """Test resources summary filtered by account"""
        manager, resources_table, summary_table, findings_table = inventory_manager_with_caching
        
        # Add resources for two accounts
        resources_table.put_item(Item={
            'AccountService': '111111111111_s3',
            'ARN': 'arn:aws:s3:::account1-bucket',
            'LastSeenAt': datetime.now(timezone.utc).isoformat()
        })
        resources_table.put_item(Item={
            'AccountService': '222222222222_s3',
            'ARN': 'arn:aws:s3:::account2-bucket',
            'LastSeenAt': datetime.now(timezone.utc).isoformat()
        })
        
        # Get summary for account 1
        summary = manager.get_resources_summary(account_id='111111111111')
        
        assert summary['total_resources'] == 1
        assert summary['total_accounts'] == 1
        assert len(summary['resource_types']) == 1
        assert summary['resource_types'][0]['resource_type'] == 's3'
        assert summary['resource_types'][0]['all_resources'] == 1
    
    def test_cache_expiry_and_refresh(self, inventory_manager_with_caching):
        """Test that stale cache triggers refresh"""
        manager, resources_table, summary_table, findings_table = inventory_manager_with_caching
        
        # Add a resource
        resources_table.put_item(Item={
            'AccountService': '123456789012_s3',
            'ARN': 'arn:aws:s3:::bucket1',
            'LastSeenAt': datetime.now(timezone.utc).isoformat()
        })
        
        # First call - compute and cache
        summary1 = manager.get_resources_summary()
        assert summary1['total_resources'] == 1
        
        # Manually create stale cache (16 minutes old)
        stale_time = (datetime.now(timezone.utc) - timedelta(minutes=16)).isoformat()
        summary_table.put_item(Item={
            'Type': 'resources_summary_all',
            'updated_at': stale_time,
            'summary': {
                'total_resources': 999,  # Old data
                'total_accounts': 1,
                'total_findings': 0,
                'critical_findings': 0,
                'high_findings': 0,
                'resource_types': []
            }
        })
        
        # Second call - should detect stale cache and refresh
        summary2 = manager.get_resources_summary()
        
        # Should have fresh data, not the stale 999
        assert summary2['total_resources'] == 1
