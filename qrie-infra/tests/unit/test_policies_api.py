"""Unit tests for Policies API
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from moto import mock_aws
import boto3

# Add lambda directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'lambda'))

# Mock environment variables before importing
with patch.dict(os.environ, {
    'RESOURCES_TABLE': 'test-resources-table',
    'FINDINGS_TABLE': 'test-findings-table',
    'POLICIES_TABLE': 'test-policies-table',
    'AWS_DEFAULT_REGION': 'us-east-1'
}):
    from api.policies_api import handle_get_policies, handle_launch_policy, handle_update_policy, handle_delete_policy
    from policy_definition import ScopeConfig
    from common.exceptions import ValidationError, NotFoundError


@mock_aws
class TestPoliciesAPI:
    """Test Policies API endpoints"""
    
    def setup_method(self, method):
        """Setup test fixtures"""
        self.headers = {'Content-Type': 'application/json'}
    
    # GET /policies tests (already covered in test_findings_api.py)
    
    @patch('api.policies_api.boto3.client')
    @patch('api.policies_api.get_policy_manager')
    def test_launch_policy_success(self, mock_get_policy_manager, mock_boto3_client):
        """Test POST /policies - successful launch"""
        # Mock policy manager
        mock_policy_manager = Mock()
        mock_get_policy_manager.return_value = mock_policy_manager
        
        # Mock Lambda client for scan trigger
        mock_lambda_client = Mock()
        mock_boto3_client.return_value = mock_lambda_client
        
        body = {
            'policy_id': 'S3BucketPublic',
            'scope': {
                'include_accounts': ['123456789012'],
                'exclude_accounts': [],
                'include_tags': {'Environment': ['prod']},
                'exclude_tags': {},
                'include_ou_paths': [],
                'exclude_ou_paths': []
            },
            'severity': 95,
            'remediation': 'Custom remediation steps'
        }
        
        response = handle_launch_policy(json.dumps(body), self.headers)
        
        assert response['statusCode'] == 201
        response_body = json.loads(response['body'])
        assert 'Policy S3BucketPublic launched successfully' in response_body['message']
        assert response_body['bootstrap_scan_triggered'] == True
        
        # Verify policy manager was called correctly
        mock_policy_manager.launch_policy.assert_called_once()
        call_args = mock_policy_manager.launch_policy.call_args
        assert call_args.kwargs['policy_id'] == 'S3BucketPublic'
        assert call_args.kwargs['severity'] == 95
        assert call_args.kwargs['remediation'] == 'Custom remediation steps'
        
        # Verify scan was triggered
        mock_lambda_client.invoke.assert_called_once()
    
    def test_launch_policy_missing_policy_id(self):
        """Test POST /policies - missing policy_id"""
        body = {'scope': {}}
        
        with pytest.raises(ValidationError, match='policy_id is required'):
            handle_launch_policy(json.dumps(body), self.headers)
    
    @patch('api.policies_api.get_policy_manager')
    def test_launch_policy_minimal_request(self, mock_get_policy_manager):
        """Test POST /policies - minimal valid request"""
        mock_policy_manager = Mock()
        mock_get_policy_manager.return_value = mock_policy_manager
        
        body = {'policy_id': 'S3BucketPublic'}
        
        with patch('api.policies_api.boto3.client'):
            response = handle_launch_policy(json.dumps(body), self.headers)
        
        assert response['statusCode'] == 201
        
        # Verify default scope was created
        call_args = mock_policy_manager.launch_policy.call_args
        scope = call_args.kwargs['scope']
        assert scope.include_accounts == []
        assert scope.exclude_accounts == []
    
    @patch('api.policies_api.get_policy_manager')
    def test_update_policy_success(self, mock_get_policy_manager):
        """Test PUT /policies/{id} - successful update"""
        mock_policy_manager = Mock()
        mock_policy_manager.update_launched_policy.return_value = True
        mock_get_policy_manager.return_value = mock_policy_manager
        
        body = {
            'severity': 85,
            'remediation': 'Updated remediation',
            'scope': {
                'include_accounts': ['123456789012', '123456789013'],
                'exclude_accounts': [],
                'include_tags': {},
                'exclude_tags': {},
                'include_ou_paths': [],
                'exclude_ou_paths': []
            }
        }
        
        with patch('api.policies_api.boto3.client'):
            response = handle_update_policy('S3BucketPublic', json.dumps(body), self.headers)
        
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert 'Policy S3BucketPublic updated successfully' in response_body['message']
        
        # Verify update was called with correct parameters
        mock_policy_manager.update_launched_policy.assert_called_once()
        call_args = mock_policy_manager.update_launched_policy.call_args
        assert call_args.args[0] == 'S3BucketPublic'
        assert call_args.kwargs['severity'] == 85
        assert call_args.kwargs['remediation'] == 'Updated remediation'
    
    @patch('api.policies_api.get_policy_manager')
    def test_update_policy_not_found(self, mock_get_policy_manager):
        """Test PUT /policies/{id} - policy not found"""
        mock_policy_manager = Mock()
        mock_policy_manager.update_launched_policy.return_value = False
        mock_get_policy_manager.return_value = mock_policy_manager
        
        body = {'severity': 85}
        
        with pytest.raises(NotFoundError, match='Policy NonExistent not found'):
            handle_update_policy('NonExistent', json.dumps(body), self.headers)
    
    def test_update_policy_no_fields(self):
        """Test PUT /policies/{id} - no fields provided"""
        body = {}
        
        with pytest.raises(ValidationError, match='At least one field .* must be provided'):
            handle_update_policy('S3BucketPublic', json.dumps(body), self.headers)
    
    @patch('api.policies_api.FindingsManager')
    @patch('api.policies_api.get_policy_manager')
    def test_delete_policy_success(self, mock_get_policy_manager, mock_findings_manager_class):
        """Test DELETE /policies/{id} - successful deletion"""
        # Mock policy manager
        mock_policy_manager = Mock()
        mock_launched_policy = Mock()
        mock_policy_manager.get_launched_policy.return_value = mock_launched_policy
        mock_get_policy_manager.return_value = mock_policy_manager
        
        # Mock findings manager
        mock_findings_manager = Mock()
        mock_findings_manager.purge_findings_for_policy.return_value = 42
        mock_findings_manager_class.return_value = mock_findings_manager
        
        response = handle_delete_policy('S3BucketPublic', self.headers)
        
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert 'Policy S3BucketPublic deleted successfully' in response_body['message']
        assert response_body['findings_deleted'] == 42
        
        # Verify findings were purged
        mock_findings_manager.purge_findings_for_policy.assert_called_once_with('S3BucketPublic')
        
        # Verify policy was deleted
        mock_policy_manager.delete_launched_policy.assert_called_once_with('S3BucketPublic')
    
    @patch('api.policies_api.get_policy_manager')
    def test_delete_policy_not_found(self, mock_get_policy_manager):
        """Test DELETE /policies/{id} - policy not found"""
        mock_policy_manager = Mock()
        mock_policy_manager.get_launched_policy.return_value = None
        mock_get_policy_manager.return_value = mock_policy_manager
        
        with pytest.raises(NotFoundError, match='Policy NonExistent not found'):
            handle_delete_policy('NonExistent', self.headers)
    
    @patch('api.policies_api.FindingsManager')
    @patch('api.policies_api.get_policy_manager')
    def test_delete_policy_purge_failure(self, mock_get_policy_manager, mock_findings_manager_class):
        """Test DELETE /policies/{id} - findings purge failure"""
        # Mock policy manager
        mock_policy_manager = Mock()
        mock_launched_policy = Mock()
        mock_policy_manager.get_launched_policy.return_value = mock_launched_policy
        mock_get_policy_manager.return_value = mock_policy_manager
        
        # Mock findings manager to raise exception
        mock_findings_manager = Mock()
        mock_findings_manager.purge_findings_for_policy.side_effect = Exception('Purge failed')
        mock_findings_manager_class.return_value = mock_findings_manager
        
        with pytest.raises(Exception, match='Purge failed'):
            handle_delete_policy('S3BucketPublic', self.headers)
        
        # Policy deletion should not be called if purge fails
        mock_policy_manager.delete_launched_policy.assert_not_called()
