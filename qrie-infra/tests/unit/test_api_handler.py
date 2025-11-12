"""
Unit tests for API Handler
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
    from api.api_handler import lambda_handler


@mock_aws
class TestAPIHandler:
    """Test API Handler"""
    
    def setup_method(self, method):
        """Setup test fixtures"""
        self.mock_context = Mock()
        self.base_event = {
            'requestContext': {'http': {'method': 'GET'}},
            'rawPath': '/resources',
            'queryStringParameters': {}
        }
    
    def test_options_request(self):
        """Test OPTIONS request for CORS preflight"""
        event = self.base_event.copy()
        event['requestContext']['http']['method'] = 'OPTIONS'
        
        response = lambda_handler(event, self.mock_context)
        
        # OPTIONS should return 200 with empty body
        # CORS headers are added by Lambda Function URL configuration, not in code
        assert response['statusCode'] == 200
        assert response['body'] == ''
        assert 'Content-Type' in response['headers']
    
    @patch('api.api_handler.handle_list_resources_paginated')
    def test_resources_endpoint(self, mock_handle_list_resources_paginated):
        """Test /resources endpoint routing"""
        mock_handle_list_resources_paginated.return_value = {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'resources': []})
        }
        
        event = self.base_event.copy()
        event['rawPath'] = '/resources'
        
        response = lambda_handler(event, self.mock_context)
        
        assert response['statusCode'] == 200
        mock_handle_list_resources_paginated.assert_called_once()
    
    @patch('api.api_handler.handle_list_accounts')
    def test_accounts_endpoint(self, mock_handle_accounts):
        """Test /accounts endpoint routing"""
        mock_handle_accounts.return_value = {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps([])
        }
        
        event = self.base_event.copy()
        event['rawPath'] = '/accounts'
        
        response = lambda_handler(event, self.mock_context)
        
        assert response['statusCode'] == 200
        mock_handle_accounts.assert_called_once()
    
    @patch('api.api_handler.handle_list_services')
    def test_services_endpoint(self, mock_handle_services):
        """Test /services endpoint routing"""
        mock_handle_services.return_value = {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps([])
        }
        
        event = self.base_event.copy()
        event['rawPath'] = '/services'
        
        response = lambda_handler(event, self.mock_context)
        
        assert response['statusCode'] == 200
        mock_handle_services.assert_called_once()
    
    @patch('api.api_handler.handle_list_findings_paginated')
    def test_findings_endpoint(self, mock_handle_findings_paginated):
        """Test /findings endpoint routing"""
        mock_handle_findings_paginated.return_value = {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'findings': []})
        }
        
        event = self.base_event.copy()
        event['rawPath'] = '/findings'
        
        response = lambda_handler(event, self.mock_context)
        
        assert response['statusCode'] == 200
        mock_handle_findings_paginated.assert_called_once()
    
    @patch('api.api_handler.handle_get_policies')
    def test_policies_get_endpoint(self, mock_handle_get_policies):
        """Test GET /policies endpoint routing"""
        mock_handle_get_policies.return_value = {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps([])
        }
        
        event = self.base_event.copy()
        event['rawPath'] = '/policies'
        event['requestContext']['http']['method'] = 'GET'
        
        response = lambda_handler(event, self.mock_context)
        
        assert response['statusCode'] == 200
        mock_handle_get_policies.assert_called_once()
    
    @patch('api.api_handler.handle_launch_policy')
    def test_policies_post_endpoint(self, mock_handle_launch_policy):
        """Test POST /policies endpoint routing"""
        mock_handle_launch_policy.return_value = {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Policy launched'})
        }
        
        event = self.base_event.copy()
        event['rawPath'] = '/policies'
        event['requestContext']['http']['method'] = 'POST'
        event['body'] = json.dumps({'policy_id': 'S3BucketPublic'})
        
        response = lambda_handler(event, self.mock_context)
        
        assert response['statusCode'] == 201
        mock_handle_launch_policy.assert_called_once()
    
    @patch('api.api_handler.handle_update_policy')
    def test_policies_put_endpoint(self, mock_handle_update_policy):
        """Test PUT /policies/{id} endpoint routing"""
        mock_handle_update_policy.return_value = {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Policy updated'})
        }
        
        event = self.base_event.copy()
        event['rawPath'] = '/policies/S3BucketPublic'
        event['requestContext']['http']['method'] = 'PUT'
        event['body'] = json.dumps({'severity': 95})
        
        response = lambda_handler(event, self.mock_context)
        
        assert response['statusCode'] == 200
        mock_handle_update_policy.assert_called_once_with('S3BucketPublic', event['body'], response['headers'])
    
    @patch('api.api_handler.handle_delete_policy')
    def test_policies_delete_endpoint(self, mock_handle_delete_policy):
        """Test DELETE /policies/{id} endpoint routing"""
        mock_handle_delete_policy.return_value = {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Policy deleted', 'findings_deleted': 5})
        }
        
        event = self.base_event.copy()
        event['rawPath'] = '/policies/S3BucketPublic'
        event['requestContext']['http']['method'] = 'DELETE'
        
        response = lambda_handler(event, self.mock_context)
        
        assert response['statusCode'] == 200
        mock_handle_delete_policy.assert_called_once_with('S3BucketPublic', response['headers'])
    
    
    def test_invalid_path(self):
        """Test invalid path returns 404"""
        event = self.base_event.copy()
        event['rawPath'] = '/invalid'
        
        response = lambda_handler(event, self.mock_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'Endpoint not found' in body['error']
    
    def test_error_handling(self):
        """Test error handling returns 500"""
        event = self.base_event.copy()
        # Cause an error by making query_params None instead of dict
        event['queryStringParameters'] = None
        event['rawPath'] = '/resources'
        
        with patch('api.api_handler.handle_list_resources_paginated', side_effect=Exception('Test error')):
            response = lambda_handler(event, self.mock_context)
            
            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert body['error'] == 'Internal server error'
