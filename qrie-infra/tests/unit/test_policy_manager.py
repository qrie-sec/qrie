"""
Unit tests for PolicyManager.
Tests policy discovery, launched policy management, and caching.
"""
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import sys
import os
import tempfile
import importlib.util

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

from data_access.policy_manager import PolicyManager
from policy_definition import PolicyDefinition, Policy, ScopeConfig


@pytest.fixture
def mock_table():
    """Mock DynamoDB table for testing"""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-policies',
            KeySchema=[
                {'AttributeName': 'PolicyId', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PolicyId', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        yield table


@pytest.fixture
def policy_manager(mock_table):
    """PolicyManager instance with mocked table"""
    with patch('data_access.policy_manager.get_policies_table', return_value=mock_table):
        manager = PolicyManager()
        return manager


@pytest.fixture
def sample_policy_definition():
    """Sample policy definition for testing"""
    return PolicyDefinition(
        policy_id="test-policy",
        description="Test policy for unit tests",
        service="s3",
        category="security",
        severity=80,
        remediation="Fix the test issue",
        evaluation_module="test_policy"
    )


@pytest.fixture
def sample_scope_config():
    """Sample scope configuration for testing"""
    return ScopeConfig(
        include_accounts=["123456789012"],
        exclude_accounts=None,
        include_tags={"Environment": "prod"},
        exclude_tags=None,
        include_ou_paths=None,
        exclude_ou_paths=None
    )


class TestPolicyManager:
    """Test suite for PolicyManager"""

    def test_launch_policy(self, policy_manager, sample_scope_config):
        """Test launching a policy"""
        with patch.object(policy_manager, 'get_policy_definition') as mock_get_def:
            mock_get_def.return_value = PolicyDefinition(
                policy_id="test-policy",
                description="Test policy",
                service="s3",
                category="security",
                severity=80,
                remediation="Test remediation",
                evaluation_module="test_policy"
            )
            
            policy_manager.launch_policy("test-policy", sample_scope_config, severity=90)
            
            # Verify policy was stored in DynamoDB
            response = policy_manager.table.get_item(Key={'PolicyId': 'test-policy'})
            assert 'Item' in response
            
            item = response['Item']
            assert item['PolicyId'] == 'test-policy'
            assert item['Status'] == 'active'
            assert item['Severity'] == 90
            assert 'CreatedAt' in item
            assert 'UpdatedAt' in item
            assert 'Scope' in item

    def test_launch_policy_nonexistent(self, policy_manager, sample_scope_config):
        """Test launching a non-existent policy raises error"""
        with patch.object(policy_manager, 'get_policy_definition', return_value=None):
            with pytest.raises(ValueError, match="Policy nonexistent-policy not found"):
                policy_manager.launch_policy("nonexistent-policy", sample_scope_config)

    def test_list_launched_policies(self, policy_manager, sample_scope_config):
        """Test listing launched policies"""
        with patch.object(policy_manager, 'get_policy_definition') as mock_get_def:
            mock_get_def.return_value = PolicyDefinition(
                policy_id="test-policy",
                description="Test policy",
                service="s3",
                category="security",
                severity=80,
                remediation="Test remediation",
                evaluation_module="test_policy"
            )
            
            # Launch multiple policies
            policy_manager.launch_policy("test-policy-1", sample_scope_config)
            policy_manager.launch_policy("test-policy-2", sample_scope_config)
            
            # Test listing all policies
            policies = policy_manager.list_launched_policies()
            assert len(policies) == 2
            assert all(isinstance(p, Policy) for p in policies)
            
            policy_ids = {p.policy_id for p in policies}
            assert policy_ids == {"test-policy-1", "test-policy-2"}
            
            # Test filtering by status
            active_policies = policy_manager.list_launched_policies(status_filter='active')
            assert len(active_policies) == 2

    def test_get_launched_policy(self, policy_manager, sample_scope_config):
        """Test getting a specific launched policy"""
        with patch.object(policy_manager, 'get_policy_definition') as mock_get_def:
            mock_get_def.return_value = PolicyDefinition(
                policy_id="test-policy",
                description="Test policy",
                service="s3",
                category="security",
                severity=80,
                remediation="Test remediation",
                evaluation_module="test_policy"
            )
            
            policy_manager.launch_policy("test-policy", sample_scope_config, severity=90)
            
            launched_policy = policy_manager.get_launched_policy("test-policy")
            
            assert launched_policy is not None
            assert isinstance(launched_policy, Policy)
            assert launched_policy.policy_id == "test-policy"
            assert launched_policy.status == "active"
            assert launched_policy.severity == 90
            assert launched_policy.scope.include_accounts == ["123456789012"]

    def test_get_launched_policy_nonexistent(self, policy_manager):
        """Test getting a non-existent launched policy"""
        policy = policy_manager.get_launched_policy("nonexistent-policy")
        assert policy is None

    def test_update_launched_policy(self, policy_manager, sample_scope_config):
        """Test updating a launched policy"""
        with patch.object(policy_manager, 'get_policy_definition') as mock_get_def:
            mock_get_def.return_value = PolicyDefinition(
                policy_id="test-policy",
                description="Test policy",
                service="s3",
                category="security",
                severity=80,
                remediation="Test remediation",
                evaluation_module="test_policy"
            )
            
            # Launch policy
            policy_manager.launch_policy("test-policy", sample_scope_config)
            
            # Update policy
            new_scope = ScopeConfig(include_accounts=["987654321098"])
            result = policy_manager.update_launched_policy(
                "test-policy", 
                severity=95, 
                scope=new_scope,
                status="inactive"
            )
            
            assert result is True
            
            # Verify update
            updated_policy = policy_manager.get_launched_policy("test-policy")
            assert updated_policy.severity == 95
            assert updated_policy.status == "inactive"
            assert updated_policy.scope.include_accounts == ["987654321098"]

    def test_update_launched_policy_nonexistent(self, policy_manager):
        """Test updating a non-existent policy"""
        result = policy_manager.update_launched_policy("nonexistent-policy", severity=95)
        assert result is False

    @patch('data_access.policy_manager.Path')
    def test_get_available_policies(self, mock_path, policy_manager):
        """Test discovering available policies"""
        # Mock the policies directory
        mock_policies_dir = MagicMock()
        mock_path.return_value.__truediv__.return_value = mock_policies_dir
        mock_policies_dir.exists.return_value = True
        
        # Mock policy files
        mock_policy_file = MagicMock()
        mock_policy_file.name = "test_policy.py"
        mock_policy_file.stem = "test_policy"
        mock_policies_dir.glob.return_value = [mock_policy_file]
        
    def test_get_available_policies(self, policy_manager):
        """Test getting available policies"""
        policies = policy_manager.get_available_policies()
        
        # Should find at least the test_policy and s3_public_bucket policies
        assert len(policies) >= 2
        
        # Check that we have PolicyDefinition objects
        assert all(isinstance(p, PolicyDefinition) for p in policies)
        
        # Check that we can find actual policies (after renaming)
        policy_ids = {p.policy_id for p in policies}
        assert "S3BucketPublic" in policy_ids  # Renamed from S3-public-bucket-policy
        assert "S3BucketVersioningDisabled" in policy_ids  # Renamed from S3BucketVersioning

    def test_get_policy_definition(self, policy_manager):
        """Test getting a specific policy definition"""
        sample_policy = PolicyDefinition(
            policy_id="test-policy",
            description="Test policy description",
            service="s3",
            category="security",
            severity=80,
            remediation="Test remediation",
            evaluation_module="test_policy"
        )
        
        with patch.object(policy_manager, 'get_available_policies', return_value=[sample_policy]):
            policy_def = policy_manager.get_policy_definition("test-policy")
            assert policy_def == sample_policy
            
            # Test non-existent policy
            nonexistent = policy_manager.get_policy_definition("nonexistent")
            assert nonexistent is None

    def test_get_policies_by_service(self, policy_manager):
        """Test filtering policies by service"""
        policies = [
            PolicyDefinition(policy_id="s3-policy", description="S3", service="s3", category="security", severity=80, remediation="", evaluation_module=""),
            PolicyDefinition(policy_id="ec2-policy", description="EC2", service="ec2", category="security", severity=80, remediation="", evaluation_module=""),
            PolicyDefinition(policy_id="s3-policy-2", description="S3-2", service="s3", category="compliance", severity=60, remediation="", evaluation_module="")
        ]
        
        with patch.object(policy_manager, 'get_available_policies', return_value=policies):
            s3_policies = policy_manager.get_policies_by_service("s3")
            assert len(s3_policies) == 2
            assert all(p.service == "s3" for p in s3_policies)

    def test_get_policies_by_category(self, policy_manager):
        """Test filtering policies by category"""
        policies = [
            PolicyDefinition(policy_id="policy-1", description="P1", service="s3", category="security", severity=80, remediation="", evaluation_module=""),
            PolicyDefinition(policy_id="policy-2", description="P2", service="ec2", category="compliance", severity=80, remediation="", evaluation_module=""),
            PolicyDefinition(policy_id="policy-3", description="P3", service="s3", category="security", severity=60, remediation="", evaluation_module="")
        ]
        
        with patch.object(policy_manager, 'get_available_policies', return_value=policies):
            security_policies = policy_manager.get_policies_by_category("security")
            assert len(security_policies) == 2
            assert all(p.category == "security" for p in security_policies)

    def test_create_policy_evaluator(self, policy_manager, sample_scope_config):
        """Test creating a policy evaluator"""
        sample_policy = PolicyDefinition(
            policy_id="test-policy",
            description="Test policy",
            service="s3",
            category="security",
            severity=80,
            remediation="Test remediation",
            evaluation_module="test_policy"
        )
        
        launched_policy = Policy(
            policy_id="test-policy",
            description="Test policy",
            service="s3",
            category="security",
            severity=90,
            remediation="Test remediation",
            evaluation_module="test_policy",
            scope=sample_scope_config,
            status="active",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z"
        )
        
        # Mock evaluator class
        mock_evaluator_class = MagicMock()
        mock_evaluator_instance = MagicMock()
        mock_evaluator_class.return_value = mock_evaluator_instance
        
        with patch.object(policy_manager, 'get_policy_definition', return_value=sample_policy), \
             patch.object(policy_manager, 'get_policy_evaluator_class', return_value=mock_evaluator_class):
            
            evaluator = policy_manager.create_policy_evaluator("test-policy", launched_policy)
            
            assert evaluator == mock_evaluator_instance
            mock_evaluator_class.assert_called_once_with("test-policy", 90, sample_scope_config)

    def test_get_applicable_policies(self, policy_manager, sample_scope_config):
        """Test getting applicable policies for account and service"""
        # Create a launched policy
        with patch.object(policy_manager, 'get_policy_definition') as mock_get_def:
            mock_get_def.return_value = PolicyDefinition(
                policy_id="s3-policy",
                description="S3 policy",
                service="s3",
                category="security",
                severity=80,
                remediation="Test remediation",
                evaluation_module="s3_policy"
            )
            
            policy_manager.launch_policy("s3-policy", sample_scope_config)
            
            with patch('scoping.should_evaluate_resource', return_value=True):
                applicable = policy_manager.get_applicable_policies("s3", "123456789012")
                
                assert len(applicable) == 1
                assert applicable[0]['policy_id'] == 's3-policy'
                assert applicable[0]['service'] == 's3'

    def test_scope_serialization_deserialization(self, policy_manager):
        """Test scope configuration serialization and deserialization"""
        scope = ScopeConfig(
            include_accounts=["123456789012", "987654321098"],
            exclude_accounts=["111111111111"],
            include_tags={"Environment": "prod", "Team": "security"},
            exclude_tags={"Status": "deprecated"},
            include_ou_paths=["/Root/Production/"],
            exclude_ou_paths=["/Root/Development/"]
        )
        
        # Test serialization
        serialized = policy_manager._serialize_scope(scope)
        assert isinstance(serialized, dict)
        assert serialized['IncludeAccounts'] == ["123456789012", "987654321098"]
        assert serialized['IncludeTags'] == {"Environment": "prod", "Team": "security"}
        
        # Test deserialization
        deserialized = policy_manager._deserialize_scope(serialized)
        assert isinstance(deserialized, ScopeConfig)
        assert deserialized.include_accounts == ["123456789012", "987654321098"]
        assert deserialized.exclude_accounts == ["111111111111"]
        assert deserialized.include_tags == {"Environment": "prod", "Team": "security"}

    @patch('data_access.policy_manager.get_policies_table')
    def test_manager_initialization(self, mock_get_table):
        """Test PolicyManager initialization"""
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        manager = PolicyManager()
        assert manager.table == mock_table

    def test_caching_behavior(self, policy_manager):
        """Test that caching works correctly"""
        sample_policy = PolicyDefinition(
            policy_id="test-policy",
            description="Test policy",
            service="s3",
            category="security",
            severity=80,
            remediation="Test remediation",
            evaluation_module="test_policy"
        )
        
        with patch.object(policy_manager, 'get_available_policies', return_value=[sample_policy]) as mock_get_available:
            # First call
            policy1 = policy_manager.get_policy_definition("test-policy")
            # Second call should use cache
            policy2 = policy_manager.get_policy_definition("test-policy")
            
            assert policy1 == policy2
            # get_available_policies should be called only once due to caching
            assert mock_get_available.call_count == 1
