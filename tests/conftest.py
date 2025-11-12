"""
Pytest configuration and shared fixtures for all tests.
"""
import pytest
import os
import sys
from unittest.mock import patch

# Add lambda directory to Python path for all tests
lambda_path = os.path.join(os.path.dirname(__file__), '../lambda')
if lambda_path not in sys.path:
    sys.path.insert(0, lambda_path)


@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for all tests"""
    env_vars = {
        'AWS_DEFAULT_REGION': 'us-east-1',
        'AWS_ACCESS_KEY_ID': 'testing',
        'AWS_SECRET_ACCESS_KEY': 'testing',
        'AWS_SECURITY_TOKEN': 'testing',
        'AWS_SESSION_TOKEN': 'testing',
        'FINDINGS_TABLE': 'test-findings',
        'RESOURCES_TABLE': 'test-resources',
        'POLICIES_TABLE': 'test-policies',
        'ACCOUNTS_TABLE': 'test-accounts'
    }
    
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture
def sample_account():
    """Sample customer account for testing"""
    return {
        'account_id': '123456789012',
        'account_name': 'Test Account',
        'email': 'test@example.com',
        'status': 'active',
        'onboarded_at': '2023-01-01T00:00:00Z'
    }


@pytest.fixture
def sample_arn():
    """Sample AWS resource ARN"""
    return 'arn:aws:s3:::test-bucket'


@pytest.fixture
def sample_evidence():
    """Sample evidence for policy findings"""
    return {
        'public_access_block': {
            'BlockPublicAcls': False,
            'IgnorePublicAcls': False,
            'BlockPublicPolicy': False,
            'RestrictPublicBuckets': False
        },
        'bucket_policy': {
            'has_policy': True,
            'allows_public_read': True
        }
    }
