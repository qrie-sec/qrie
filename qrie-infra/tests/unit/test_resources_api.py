"""Unit tests for Resources API
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
    from api.resources_api import handle_list_resources_paginated, handle_list_accounts, handle_list_services


@mock_aws
class TestResourcesAPI:
    """Test Resources API endpoints"""
    
    def setup_method(self, method):
        """Setup test fixtures"""
        self.mock_context = Mock()
        self.base_event = {
            'requestContext': {'http': {'method': 'GET'}},
            'rawPath': '/resources',
            'queryStringParameters': {}
        }
        
        # Create mock DynamoDB table
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.create_table(
            TableName='test-resources-table',
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
    
    @patch('api.resources_api.get_inventory_manager')
    def test_list_resources_no_filters(self, mock_get_inventory_manager):
        """Test GET /resources with no filters"""
        # Mock response
        mock_manager = Mock()
        mock_get_inventory_manager.return_value = mock_manager
        mock_manager.get_resources_paginated.return_value = {
            'resources': [
                {
                    'ARN': 'arn:aws:s3:::test-bucket',
                    'AccountService': '123456789012_s3',
                    'LastSeenAt': '2023-01-01T00:00:00Z'
                }
            ],
            'count': 1
        }
        
        headers = {'Content-Type': 'application/json'}
        response = handle_list_resources_paginated({}, headers)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'resources' in body
        assert len(body['resources']) == 1
        assert body['resources'][0]['arn'] == 'arn:aws:s3:::test-bucket'
    
    @patch('api.resources_api.get_inventory_manager')
    def test_list_resources_with_filters(self, mock_get_inventory_manager):
        """Test GET /resources with account and type filters"""
        mock_manager = Mock()
        mock_get_inventory_manager.return_value = mock_manager
        mock_manager.get_resources_paginated.return_value = {
            'resources': [],
            'count': 0,
            'next_token': 'abc123'
        }
        
        query_params = {
            'account': '123456789012',
            'type': 's3',
            'page_size': '25'
        }
        headers = {'Content-Type': 'application/json'}
        
        response = handle_list_resources_paginated(query_params, headers)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'resources' in body
        assert 'next_token' in body
        
        # Verify manager was called with correct parameters
        mock_manager.get_resources_paginated.assert_called_once_with(
            account_id='123456789012',
            service='s3',
            page_size=25,
            next_token=None
        )
    
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
        assert body[0]['ou'] == 'Engineering'
    
    @patch('api.resources_api.SUPPORTED_SERVICES', ['s3', 'ec2', 'iam'])
    def test_list_services(self):
        """Test GET /services"""
        query_params = {'supported': 'true'}
        headers = {'Content-Type': 'application/json'}
        
        response = handle_list_services(query_params, headers)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 3
        assert any(service['service_name'] == 's3' for service in body)
    
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
    
    @patch('api.resources_api.get_inventory_manager')
    def test_page_size_validation(self, mock_get_inventory_manager):
        """Test page size is capped at 100"""
        mock_manager = Mock()
        mock_get_inventory_manager.return_value = mock_manager
        mock_manager.get_resources_paginated.return_value = {
            'resources': [],
            'count': 0
        }
        
        query_params = {'page_size': '150'}
        headers = {'Content-Type': 'application/json'}
        
        response = handle_list_resources_paginated(query_params, headers)
        
        # Should cap at 100
        mock_manager.get_resources_paginated.assert_called_once_with(
            account_id=None,
            service=None,
            page_size=100,
            next_token=None
        )
