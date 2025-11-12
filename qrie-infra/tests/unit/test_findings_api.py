"""Unit tests for Findings API
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from moto import mock_aws
import boto3
from common.exceptions import ValidationError

# Add lambda directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'lambda'))
headers = {'Content-Type': 'application/json'}
# Mock environment variables before importing
with patch.dict(os.environ, {
    'RESOURCES_TABLE': 'test-resources-table',
    'FINDINGS_TABLE': 'test-findings-table',
    'POLICIES_TABLE': 'test-policies-table',
    'AWS_DEFAULT_REGION': 'us-east-1'
}):
    from api.findings_api import handle_list_findings_paginated
    from api.resources_api import handle_list_accounts
    from api.policies_api import handle_get_policies
    from data_access.findings_manager import Finding
    


@mock_aws
class TestFindingsAPI:
    """Test Findings API endpoints"""
    
    def setup_method(self, method):
        """Setup test fixtures"""
        self.mock_context = Mock()
        self.base_event = {
            'requestContext': {'http': {'method': 'GET'}},
            'rawPath': '/findings',
            'queryStringParameters': {}
        }
        
        # Create mock DynamoDB table
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.create_table(
            TableName='test-findings-table',
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
        
        # Sample finding for tests
        self.sample_finding = Finding(
            arn='arn:aws:s3:::test-bucket',
            policy='S3BucketVersioningDisabled',
            account_service='123456789012_s3',
            severity=90,
            state='ACTIVE',
            first_seen='2023-01-01T00:00:00Z',
            last_evaluated='2023-01-01T00:00:00Z',
            evidence={'bucket_versioning': False}
        )
    
    @patch('api.findings_api.get_findings_manager')
    def test_list_findings_no_filters(self, mock_get_findings_manager):
        """Test GET /findings with no filters"""
        mock_manager = Mock()
        mock_get_findings_manager.return_value = mock_manager
        mock_manager.get_findings_paginated.return_value = {
            'findings': [self.sample_finding],
            'count': 1
        }
        
        headers = {'Content-Type': 'application/json'}
        response = handle_list_findings_paginated({}, headers)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'findings' in body
        assert len(body['findings']) == 1
        assert body['findings'][0]['arn'] == 'arn:aws:s3:::test-bucket'
        assert body['findings'][0]['policy'] == 'S3BucketVersioningDisabled'
    
    @patch('api.findings_api.get_findings_manager')
    def test_list_findings_with_filters(self, mock_get_findings_manager):
        """Test GET /findings with multiple filters"""
        mock_manager = Mock()
        mock_get_findings_manager.return_value = mock_manager
        mock_manager.get_findings_paginated.return_value = {
            'findings': [],
            'count': 0,
            'next_token': 'abc123'
        }
        
        query_params = {
            'account': '123456789012',
            'policy': 'S3BucketVersioningDisabled',
            'state': 'ACTIVE',
            'severity': 'critical',
            'page_size': '25'
        }
        headers = {'Content-Type': 'application/json'}
        
        response = handle_list_findings_paginated(query_params, headers)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'findings' in body
        assert 'next_token' in body
        
        # Verify manager was called with correct parameters
        mock_manager.get_findings_paginated.assert_called_once_with(
            account_id='123456789012',
            policy_id='S3BucketVersioningDisabled',
            state_filter='ACTIVE',
            severity_filter='critical',
            page_size=25,
            next_token=None
        )
    
    def test_invalid_state_filter(self):
        """Test invalid state filter raises ValidationError"""
        
        with pytest.raises(ValidationError, match='state must be ACTIVE or RESOLVED'):
            handle_list_findings_paginated({'state': 'invalid'}, headers)
    
    @patch('api.resources_api.get_customer_accounts')
    def test_list_accounts(self, mock_get_accounts):
        """Test GET /accounts"""
        mock_get_accounts.return_value = [
            {'AccountId': '123456789012', 'ou': 'Engineering'},
            {'AccountId': '123456789013', 'ou': 'Finance'}
        ]
        
        headers = {'Content-Type': 'application/json'}
        
        response = handle_list_accounts(headers)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 2
        assert body[0]['account_id'] == '123456789012'
    
    @patch('api.policies_api.FindingsManager')
    @patch('api.policies_api.get_policy_manager')
    def test_list_policies_active_only(self, mock_get_policy_manager, mock_findings_manager_class):
        """Test GET /policies?status=active"""
        # Mock FindingsManager
        mock_findings_manager = Mock()
        mock_findings_manager.get_findings_summary.return_value = {
            'policies': [{'policy': 'S3BucketVersioningDisabled', 'open_findings': 5}]
        }
        mock_findings_manager_class.return_value = mock_findings_manager
        
        # Mock PolicyManager
        mock_policy_manager = Mock()
        mock_get_policy_manager.return_value = mock_policy_manager
        
        # Mock policy object with proper ScopeConfig
        from policy_definition import ScopeConfig
        mock_policy = Mock()
        mock_policy.policy_id = 'S3BucketVersioningDisabled'
        mock_policy.status = 'active'
        mock_policy.severity = 90
        mock_policy.description = 'Test policy'
        mock_policy.remediation = 'Fix it'
        mock_policy.service = 's3'
        mock_policy.category = 'security'
        mock_policy.scope = ScopeConfig(
            include_accounts=[],
            exclude_accounts=[],
            include_tags={},
            exclude_tags={},
            include_ou_paths=[],
            exclude_ou_paths=[]
        )
        mock_policy.created_at = '2024-01-01T00:00:00'
        mock_policy.updated_at = '2024-01-01T00:00:00'
        
        mock_policy_manager.list_launched_policies.return_value = [mock_policy]
        
        response = handle_get_policies({'status': 'active'}, headers)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 1
        assert body[0]['policy_id'] == 'S3BucketVersioningDisabled'
        assert body[0]['status'] == 'active'
    
    @patch('api.policies_api.FindingsManager')
    @patch('api.policies_api.get_policy_manager')
    def test_list_policies_all(self, mock_get_policy_manager, mock_findings_manager_class):
        """Test GET /policies with status=all (returns active + available)"""
        # Mock FindingsManager
        mock_findings_manager = Mock()
        mock_findings_manager.get_findings_summary.return_value = {
            'policies': [{'policy': 'ActivePolicy', 'open_findings': 3}]
        }
        mock_findings_manager_class.return_value = mock_findings_manager
        
        # Mock PolicyManager
        mock_policy_manager = Mock()
        mock_get_policy_manager.return_value = mock_policy_manager
        
        # Mock active policy with proper ScopeConfig
        from policy_definition import ScopeConfig
        active_policy = Mock()
        active_policy.policy_id = 'ActivePolicy'
        active_policy.status = 'active'
        active_policy.severity = 90
        active_policy.description = 'Active policy'
        active_policy.remediation = 'Fix it'
        active_policy.service = 's3'
        active_policy.category = 'security'
        active_policy.scope = ScopeConfig(
            include_accounts=[],
            exclude_accounts=[],
            include_tags={},
            exclude_tags={},
            include_ou_paths=[],
            exclude_ou_paths=[]
        )
        active_policy.created_at = '2024-01-01T00:00:00'
        active_policy.updated_at = '2024-01-01T00:00:00'
        
        # Mock available policy definition
        available_policy = Mock()
        available_policy.policy_id = 'AvailablePolicy'
        available_policy.description = 'Available policy'
        available_policy.service = 'ec2'
        available_policy.category = 'compliance'
        available_policy.severity = 70
        available_policy.remediation = 'Fix it too'
        
        mock_policy_manager.list_launched_policies.return_value = [active_policy]
        mock_policy_manager.get_available_policies.return_value = [available_policy]
        
        response = handle_get_policies({'status': 'all'}, headers)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 2  # 1 active + 1 available
    
    def test_options_request(self):
        """Test OPTIONS request for CORS - handled by unified API"""
        # This test is now covered by the unified API test
        pass
    
    def test_invalid_method(self):
        """Test invalid HTTP method - handled by unified API"""
        # This test is now covered by the unified API test
        pass
    
    def test_invalid_path(self):
        """Test invalid path - handled by unified API"""
        # This test is now covered by the unified API test
        pass
    
    @patch('api.findings_api.get_findings_manager')
    def test_page_size_validation(self, mock_get_findings_manager):
        """Test page size is capped at 100"""
        mock_manager = Mock()
        mock_get_findings_manager.return_value = mock_manager
        
        with pytest.raises(ValidationError, match='page_size cannot be greater than 100'):
            handle_list_findings_paginated({'page_size': '150'}, headers)
        
        mock_manager.get_findings_paginated.assert_not_called()
    
    @patch('api.findings_api.get_findings_manager')
    def test_state_parameter_passthrough(self, mock_get_findings_manager):
        """Test state parameter is passed through directly"""
        mock_manager = Mock()
        mock_get_findings_manager.return_value = mock_manager
        mock_manager.get_findings_paginated.return_value = {
            'findings': [],
            'count': 0
        }
        
        # Test 'ACTIVE' -> 'ACTIVE'
        handle_list_findings_paginated({'state': 'ACTIVE'}, headers)
        
        mock_manager.get_findings_paginated.assert_called_with(
            account_id=None,
            policy_id=None,
            state_filter='ACTIVE',
            severity_filter=None,
            page_size=50,
            next_token=None
        )
        
        # Test 'RESOLVED' -> 'RESOLVED'
        mock_manager.reset_mock()
        
        handle_list_findings_paginated({'state': 'RESOLVED'}, headers)
        
        mock_manager.get_findings_paginated.assert_called_with(
            account_id=None,
            policy_id=None,
            state_filter='RESOLVED',
            severity_filter=None,
            page_size=50,
            next_token=None
        )
