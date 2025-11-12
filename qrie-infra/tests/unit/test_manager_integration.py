"""
Integration tests for manager interactions.
Tests how managers work together in real scenarios.
"""
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock
import sys
import os
import time

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

from data_access.findings_manager import FindingsManager
from data_access.policy_manager import PolicyManager
from data_access.inventory_manager import InventoryManager
from policy_definition import PolicyDefinition, Policy, ScopeConfig


@pytest.fixture
def mock_tables():
    """Mock all DynamoDB tables"""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Findings table
        findings_table = dynamodb.create_table(
            TableName='test-findings',
            KeySchema=[
                {'AttributeName': 'ARN', 'KeyType': 'HASH'},
                {'AttributeName': 'Policy', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'ARN', 'AttributeType': 'S'},
                {'AttributeName': 'Policy', 'AttributeType': 'S'},
                {'AttributeName': 'AccountService', 'AttributeType': 'S'},
                {'AttributeName': 'State', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'AccountService-State-index',
                    'KeySchema': [
                        {'AttributeName': 'AccountService', 'KeyType': 'HASH'},
                        {'AttributeName': 'State', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
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
        
        # Policies table
        policies_table = dynamodb.create_table(
            TableName='test-policies',
            KeySchema=[
                {'AttributeName': 'PolicyId', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PolicyId', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        yield {
            'findings': findings_table,
            'resources': resources_table,
            'policies': policies_table
        }


@pytest.fixture
def managers(mock_tables):
    """Initialize all managers with mocked tables"""
    with patch('data_access.findings_manager.get_findings_table', return_value=mock_tables['findings']), \
         patch('data_access.inventory_manager.get_resources_table', return_value=mock_tables['resources']), \
         patch('data_access.policy_manager.get_policies_table', return_value=mock_tables['policies']):
        
        findings_manager = FindingsManager()
        inventory_manager = InventoryManager()
        policy_manager = PolicyManager()
        
        return {
            'findings': findings_manager,
            'inventory': inventory_manager,
            'policy': policy_manager
        }


class TestManagerIntegration:
    """Integration tests for manager interactions"""

    def test_policy_evaluation_workflow(self, managers):
        """Test complete policy evaluation workflow"""
        findings_mgr = managers['findings']
        inventory_mgr = managers['inventory']
        policy_mgr = managers['policy']
        
        # 1. Create inventory resource
        s3_arn = 'arn:aws:s3:::test-bucket'
        account_id = '123456789012'
        service = 's3'
        
        resource_config = {
            'BucketName': 'test-bucket',
            'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        }
        
        inventory_mgr.upsert_resource(account_id, service, s3_arn, resource_config, int(time.time() * 1000))
        
        # 2. Launch a policy
        scope = ScopeConfig(include_accounts=[account_id])
        
        # Use real policy that exists in codebase
        policy_mgr.launch_policy("S3BucketPublic", scope, severity=95)
        
        # 3. Verify resource exists in inventory
        resource = inventory_mgr.get_resource(s3_arn, account_id)
        assert resource is not None
        assert resource['Configuration'] == resource_config
        
        # 4. Verify policy is launched
        launched_policy = policy_mgr.get_launched_policy("S3BucketPublic")
        assert launched_policy is not None
        assert launched_policy.severity == 95
        
        # 5. Create a finding (simulating policy evaluation)
        evidence = {
            'bucket_name': 'test-bucket',
            'public_access_block': resource_config['PublicAccessBlockConfiguration'],
            'violation': 'Bucket allows public access'
        }
        
        findings_mgr.put_finding(
            s3_arn, 
            "S3BucketPublic", 
            f"{account_id}_{service}",
            85, 
            "ACTIVE", 
            evidence
        , int(time.time() * 1000))
        
        # 6. Verify finding was created
        finding = findings_mgr.get_finding_by_resource_and_policy(s3_arn, "S3BucketPublic")
        assert finding is not None
        assert finding.severity == 85
        assert finding.state == "ACTIVE"
        assert finding.evidence == evidence
        
        # 7. Get findings summary
        summary = findings_mgr.get_open_findings_summary(account_id)
        assert summary == {'s3': 1}

    def test_resource_lifecycle_with_findings(self, managers):
        """Test resource lifecycle affecting findings"""
        findings_mgr = managers['findings']
        inventory_mgr = managers['inventory']
        
        s3_arn = 'arn:aws:s3:::lifecycle-test-bucket'
        account_id = '123456789012'
        service = 's3'
        account_service = f"{account_id}_{service}"
        
        # 1. Create resource
        inventory_mgr.upsert_resource(account_id, service, s3_arn, {'BucketName': 'lifecycle-test-bucket'}, int(time.time() * 1000))
        
        # 2. Create findings for the resource
        findings_mgr.put_finding(s3_arn, "policy-1", account_service, 85, "ACTIVE", {}, int(time.time() * 1000))
        findings_mgr.put_finding(s3_arn, "policy-2", account_service, 50, "ACTIVE", {}, int(time.time() * 1000))
        
        # 3. Verify findings exist
        findings = findings_mgr.get_findings_for_resource(s3_arn)
        assert len(findings) == 2
        
        # 4. Delete resource from inventory
        inventory_mgr.delete_resource(s3_arn, account_id)
        
        # 5. Clean up findings (simulating resource deletion workflow)
        findings_mgr.delete_findings_for_resource(s3_arn)
        
        # 6. Verify resource and findings are gone
        resource = inventory_mgr.get_resource(s3_arn, account_id)
        assert resource is None
        
        findings = findings_mgr.get_findings_for_resource(s3_arn)
        assert len(findings) == 0

    def test_policy_scope_filtering(self, managers):
        """Test policy scoping affects which resources are evaluated"""
        policy_mgr = managers['policy']
        inventory_mgr = managers['inventory']
        
        # Create resources in different accounts
        prod_account = '123456789012'
        dev_account = '987654321098'
        
        inventory_mgr.upsert_resource(prod_account, 's3', 'arn:aws:s3:::prod-bucket', {}, int(time.time() * 1000))
        inventory_mgr.upsert_resource(dev_account, 's3', 'arn:aws:s3:::dev-bucket', {}, int(time.time() * 1000))
        
        # Launch policy that only applies to prod account
        scope = ScopeConfig(include_accounts=[prod_account])
        
        # Use real policy that exists
        policy_mgr.launch_policy("S3BucketVersioningDisabled", scope)
        
        # Get applicable policies for each account
        with patch('scoping.should_evaluate_resource') as mock_should_evaluate:
            # Mock scoping to return True for prod, False for dev
            def side_effect(account_id, arn, scope_config):
                return account_id == prod_account
            
            mock_should_evaluate.side_effect = side_effect
            
            prod_policies = policy_mgr.get_applicable_policies('s3', prod_account)
            dev_policies = policy_mgr.get_applicable_policies('s3', dev_account)
            
            assert len(prod_policies) == 1
            assert len(dev_policies) == 0

    def test_inventory_summary_with_findings(self, managers):
        """Test inventory summary correlates with findings"""
        inventory_mgr = managers['inventory']
        findings_mgr = managers['findings']
        
        account_id = '123456789012'
        
        # Create resources across different services
        inventory_mgr.upsert_resource(account_id, 's3', 'arn:aws:s3:::bucket1', {}, int(time.time() * 1000))
        inventory_mgr.upsert_resource(account_id, 's3', 'arn:aws:s3:::bucket2', {}, int(time.time() * 1000))
        inventory_mgr.upsert_resource(account_id, 'ec2', 'arn:aws:ec2:us-east-1:123456789012:instance/i-123', {}, int(time.time() * 1000))
        inventory_mgr.upsert_resource(account_id, 'iam', 'arn:aws:iam::123456789012:user/test-user', {}, int(time.time() * 1000))
        
        # Create findings for some resources
        findings_mgr.put_finding('arn:aws:s3:::bucket1', 'policy-1', f'{account_id}_s3', 85, 'ACTIVE', {}, int(time.time() * 1000))
        findings_mgr.put_finding('arn:aws:ec2:us-east-1:123456789012:instance/i-123', 'policy-2', f'{account_id}_ec2', 50, 'ACTIVE', {}, int(time.time() * 1000))
        
        # Get summaries
        inventory_summary = inventory_mgr.get_inventory_summary(account_id)
        findings_summary = findings_mgr.get_open_findings_summary(account_id)
        
        # Verify inventory summary
        assert inventory_summary == {'s3': 2, 'ec2': 1, 'iam': 1}
        
        # Verify findings summary (only services with findings)
        assert findings_summary == {'s3': 1, 'ec2': 1}
        
        # Services with resources but no findings should not appear in findings summary
        assert 'iam' not in findings_summary

    def test_policy_update_affects_evaluation(self, managers):
        """Test that updating a policy affects future evaluations"""
        policy_mgr = managers['policy']
        findings_mgr = managers['findings']
        
        account_id = '123456789012'
        policy_id = 'S3BucketPublic'
        resource_arn = 'arn:aws:s3:::test-bucket'
        
        # Launch policy with initial severity
        scope = ScopeConfig(include_accounts=[account_id])
        
        # Use real policy that exists
        policy_mgr.launch_policy(policy_id, scope, severity=70)
        
        # Create initial finding
        findings_mgr.put_finding(resource_arn, policy_id, f'{account_id}_s3', 50, 'ACTIVE', {}, int(time.time() * 1000))
        
        # Update policy severity
        policy_mgr.update_launched_policy(policy_id, severity=95)
        
        # Verify policy was updated
        updated_policy = policy_mgr.get_launched_policy(policy_id)
        assert updated_policy.severity == 95
        
        # Simulate re-evaluation with new severity
        findings_mgr.put_finding(resource_arn, policy_id, f'{account_id}_s3', 95, 'ACTIVE', {}, int(time.time() * 1000))
        
        # Verify finding reflects new severity
        finding = findings_mgr.get_finding_by_resource_and_policy(resource_arn, policy_id)
        assert finding.severity == 95

    def test_cross_manager_caching(self, managers):
        """Test that caching works correctly across managers"""
        policy_mgr = managers['policy']
        
        # Mock policy definition
        sample_policy = PolicyDefinition(
            policy_id="cached-policy",
            description="Cached policy test",
            service="s3",
            category="security",
            severity=80,
            remediation="Fix issue",
            evaluation_module="cached_policy"
        )
        
        with patch.object(policy_mgr, 'get_available_policies', return_value=[sample_policy]) as mock_get_available:
            # Multiple calls to get_policy_definition should use cache
            policy1 = policy_mgr.get_policy_definition("cached-policy")
            policy2 = policy_mgr.get_policy_definition("cached-policy")
            policy3 = policy_mgr.get_policy_definition("cached-policy")
            
            assert policy1 == policy2 == policy3 == sample_policy
            
            # get_available_policies should be called only once due to caching
            assert mock_get_available.call_count == 1

    def test_error_handling_across_managers(self, managers):
        """Test error handling when managers interact"""
        findings_mgr = managers['findings']
        policy_mgr = managers['policy']
        
        # Try to create finding for non-existent policy
        # This should not fail, but the policy lookup might
        findings_mgr.put_finding(
            'arn:aws:s3:::test-bucket',
            'nonexistent-policy',
            '123456789012_s3',
            85,
            'ACTIVE',
            {}
        , int(time.time() * 1000))
        
        # Verify finding was still created (managers are independent)
        finding = findings_mgr.get_finding_by_resource_and_policy(
            'arn:aws:s3:::test-bucket',
            'nonexistent-policy'
        )
        assert finding is not None
        
        # Try to get policy definition that doesn't exist
        policy_def = policy_mgr.get_policy_definition('nonexistent-policy')
        assert policy_def is None
