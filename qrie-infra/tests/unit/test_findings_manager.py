"""
Unit tests for FindingsManager.
Tests all CRUD operations, caching, and business logic.
"""
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock
from datetime import datetime
from decimal import Decimal
import sys
import os
import time

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

from data_access.findings_manager import FindingsManager, Finding


@pytest.fixture
def mock_tables():
    """Mock DynamoDB tables for testing (findings + summary)"""
    with mock_aws():
        # Create mock DynamoDB tables
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
        
        # Summary table for caching
        summary_table = dynamodb.create_table(
            TableName='test-summary',
            KeySchema=[
                {'AttributeName': 'Type', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'Type', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        yield {'findings': findings_table, 'summary': summary_table}


@pytest.fixture
def findings_manager(mock_tables):
    """FindingsManager instance with mocked tables"""
    with patch('data_access.findings_manager.get_findings_table', return_value=mock_tables['findings']), \
         patch('data_access.findings_manager.get_summary_table', return_value=mock_tables['summary']):
        manager = FindingsManager()
        return manager


class TestFindingsManager:
    """Test suite for FindingsManager"""

    def test_put_finding_new(self, findings_manager):
        """Test creating a new finding"""
        arn = "arn:aws:s3:::test-bucket"
        policy_id = "S3-public-bucket-policy"
        account_service = "123456789012_s3"
        severity = 85
        state = "OPEN"
        evidence = {"public": True, "bucket_policy": "allow_all"}
        
        findings_manager.put_finding(arn, policy_id, account_service, severity, state, evidence, int(time.time() * 1000))
        
        # Verify finding was created
        response = findings_manager.table.get_item(Key={'ARN': arn, 'Policy': policy_id})
        assert 'Item' in response
        
        item = response['Item']
        assert item['ARN'] == arn
        assert item['Policy'] == policy_id
        assert item['AccountService'] == account_service
        assert item['Severity'] == severity
        assert item['State'] == state
        assert item['Evidence'] == evidence
        assert 'FirstSeen' in item
        assert 'LastEvaluated' in item

    def test_put_finding_update_existing(self, findings_manager):
        """Test updating an existing finding"""
        arn = "arn:aws:s3:::test-bucket"
        policy_id = "S3-public-bucket-policy"
        account_service = "123456789012_s3"
        
        # Create initial finding
        findings_manager.put_finding(arn, policy_id, account_service, 50, "OPEN", {"test": 1}, int(time.time() * 1000))
        
        # Update the finding
        findings_manager.put_finding(arn, policy_id, account_service, 85, "OPEN", {"test": 2}, int(time.time() * 1000))
        
        # Verify update
        response = findings_manager.table.get_item(Key={'ARN': arn, 'Policy': policy_id})
        item = response['Item']
        
        assert item['Severity'] == 85
        assert item['Evidence'] == {"test": 2}
        # FirstSeen should remain unchanged, LastEvaluated should be updated
        assert 'FirstSeen' in item
        assert 'LastEvaluated' in item

    def test_close_finding(self, findings_manager):
        """Test closing a finding"""
        arn = "arn:aws:s3:::test-bucket"
        policy_id = "S3-public-bucket-policy"
        account_service = "123456789012_s3"
        
        # Create finding
        findings_manager.put_finding(arn, policy_id, account_service, 85, "ACTIVE", {}, int(time.time() * 1000))
        
        # Close finding
        findings_manager.close_finding(arn, policy_id)
        
        # Verify finding is closed
        response = findings_manager.table.get_item(Key={'ARN': arn, 'Policy': policy_id})
        item = response['Item']
        assert item['State'] == 'RESOLVED'

    def test_close_finding_nonexistent(self, findings_manager):
        """Test closing a non-existent finding (should not raise error)"""
        # Should not raise an exception
        findings_manager.close_finding("arn:aws:s3:::nonexistent", "nonexistent-policy")

    def test_get_finding_by_resource_and_policy(self, findings_manager):
        """Test retrieving a specific finding"""
        arn = "arn:aws:s3:::test-bucket"
        policy_id = "S3-public-bucket-policy"
        account_service = "123456789012_s3"
        evidence = {"public": True}
        
        # Create finding
        findings_manager.put_finding(
            arn, policy_id, account_service, 85, "OPEN", evidence
        , int(time.time() * 1000))
        # Retrieve finding
        finding = findings_manager.get_finding_by_resource_and_policy(arn, policy_id)
        
        assert finding is not None
        assert isinstance(finding, Finding)
        assert finding.policy == policy_id
        assert finding.account_service == account_service
        assert finding.severity == 85
        assert finding.state == "OPEN"
        assert finding.evidence == evidence

    def test_get_finding_nonexistent(self, findings_manager):
        """Test retrieving a non-existent finding"""
        finding = findings_manager.get_finding_by_resource_and_policy(
            "arn:aws:s3:::nonexistent", "nonexistent-policy"
        )
        assert finding is None

    def test_get_findings_for_resource(self, findings_manager):
        """Test retrieving all findings for a resource"""
        arn = "arn:aws:s3:::test-bucket"
        account_service = "123456789012_s3"
        
        # Create multiple findings for the same resource
        findings_manager.put_finding(arn, "policy1", account_service, "85", "ACTIVE", {}, int(time.time() * 1000))
        findings_manager.put_finding(arn, "policy2", account_service, 50, "RESOLVED", {}, int(time.time() * 1000))
        
        findings = findings_manager.get_findings_for_resource(arn)
        
        assert len(findings) == 2
        assert all(isinstance(f, Finding) for f in findings)
        assert all(f.arn == arn for f in findings)
        
        policies = {f.policy for f in findings}
        assert policies == {"policy1", "policy2"}

    def test_get_findings_for_account_service_with_filter(self, findings_manager):
        """Test retrieving findings for account/service with state filter"""
        account_service = "123456789012_s3"
        
        # Create findings with different states
        findings_manager.put_finding("arn:aws:s3:::bucket1", "policy1", account_service, 85, "ACTIVE", {}, int(time.time() * 1000))
        findings_manager.put_finding("arn:aws:s3:::bucket2", "policy1", account_service, 50, "RESOLVED", {}, int(time.time() * 1000))
        findings_manager.put_finding("arn:aws:s3:::bucket3", "policy2", account_service, 20, "ACTIVE", {}, int(time.time() * 1000))
        
        # Test ACTIVE filter
        active_findings = findings_manager.get_findings_for_account_service(
            "123456789012", "s3", state_filter="ACTIVE"
        )
        assert len(active_findings) == 2
        assert all(f.state == "ACTIVE" for f in active_findings)
        
        # Test RESOLVED filter
        resolved_findings = findings_manager.get_findings_for_account_service(
            "123456789012", "s3", state_filter="RESOLVED"
        )
        assert len(resolved_findings) == 1
        assert resolved_findings[0].state == "RESOLVED"

    def test_get_findings_for_account_service_with_limit(self, findings_manager):
        """Test retrieving findings with limit"""
        account_service = "123456789012_s3"
        
        # Create multiple findings
        for i in range(5):
            findings_manager.put_finding(f"arn:aws:s3:::bucket{i}", "policy1", account_service, 85, "ACTIVE", {}, int(time.time() * 1000))
        
        findings = findings_manager.get_findings_for_account_service(
            "123456789012", "s3", limit=3
        )
        assert len(findings) <= 3

    def test_get_findings_paginated_with_filters(self, findings_manager):
        """Test paginated findings retrieval with filters and next_token"""
        account_id = "123456789012"
        account_service = f"{account_id}_s3"

        for i in range(6):
            findings_manager.put_finding(
                f"arn:aws:s3:::bucket{i}",
                "policy-foo" if i % 2 == 0 else "policy-bar",
                account_service,
                80,
                "ACTIVE" if i % 3 else "RESOLVED",
                {"idx": i},
                int(time.time() * 1000)
            )

        result = findings_manager.get_findings_paginated(
            account_id=account_id,
            policy_id="policy-foo",
            state_filter="ACTIVE",
            page_size=5,
        )

        assert "findings" in result
        assert result["count"] <= 5
        assert all(f.policy == "policy-foo" for f in result["findings"])
        assert all(f.state == "ACTIVE" for f in result["findings"])
        if result["count"] == 5:
            assert "next_token" in result

    def test_count_findings_with_filters(self, findings_manager):
        """Test count_findings with different filter combinations"""
        account_id = "123456789012"
        account_service = f"{account_id}_ec2"

        findings_manager.put_finding("arn:aws:ec2:::i-1", "policy-a", account_service, 90, "ACTIVE", {}, int(time.time() * 1000))
        findings_manager.put_finding("arn:aws:ec2:::i-2", "policy-a", account_service, 60, "RESOLVED", {}, int(time.time() * 1000))
        findings_manager.put_finding("arn:aws:ec2:::i-3", "policy-b", account_service, 70, "ACTIVE", {}, int(time.time() * 1000))

        assert findings_manager.count_findings() == 3
        assert findings_manager.count_findings(policy_id="policy-a") == 2
        assert findings_manager.count_findings(account_id=account_id) == 3
        assert findings_manager.count_findings(state_filter="ACTIVE") == 2
        assert findings_manager.count_findings(policy_id="policy-a", state_filter="RESOLVED") == 1

    def test_get_findings_summary(self, findings_manager):
        """Test findings summary aggregation with severity breakdowns"""
        account_service = "123456789012_lambda"

        # Critical (>=90) ACTIVE
        findings_manager.put_finding("arn:aws:lambda:fn1", "policy-x", account_service, 95, "ACTIVE", {}, int(time.time() * 1000))
        # Medium (25-49) RESOLVED
        findings_manager.put_finding("arn:aws:lambda:fn2", "policy-x", account_service, 45, "RESOLVED", {}, int(time.time() * 1000))
        # Critical (>=90) ACTIVE
        findings_manager.put_finding("arn:aws:lambda:fn3", "policy-y", account_service, 92, "ACTIVE", {}, int(time.time() * 1000))
        # High (50-89) ACTIVE
        findings_manager.put_finding("arn:aws:lambda:fn4", "policy-z", account_service, 70, "ACTIVE", {}, int(time.time() * 1000))
        # Low (<25) ACTIVE
        findings_manager.put_finding("arn:aws:lambda:fn5", "policy-z", account_service, 15, "ACTIVE", {}, int(time.time() * 1000))

        summary = findings_manager.get_findings_summary()

        # Test aggregate counts
        assert summary["total_findings"] == 5
        assert summary["open_findings"] == 4
        assert summary["resolved_findings"] == 1
        assert summary["critical_findings"] == 2  # severity >= 90 and ACTIVE
        assert summary["high_findings"] == 1      # severity 50-89 and ACTIVE
        assert summary["medium_findings"] == 0    # severity 25-49 and ACTIVE (none)
        assert summary["low_findings"] == 1       # severity 0-24 and ACTIVE
        
        # Test per-policy counts
        policies = {item["policy"]: item for item in summary["policies"]}
        assert policies["policy-x"]["total_findings"] == 2
        assert policies["policy-x"]["open_findings"] == 1
        assert policies["policy-x"]["resolved_findings"] == 1
        assert policies["policy-y"]["open_findings"] == 1
        assert policies["policy-y"]["resolved_findings"] == 0
        
        # Verify policies include severity
        assert "severity" in policies["policy-x"]

    def test_convert_decimals_to_int(self, findings_manager):
        """Test Decimal conversion utility"""
        data = {
            "number": Decimal("10"),
            "ratio": Decimal("1.5"),
            "nested": {"value": Decimal("3")},
            "list": [Decimal("2"), {"inner": Decimal("4.2")}],
        }

        converted = findings_manager._convert_decimals_to_int(data)
        assert converted == {
            "number": 10,
            "ratio": 1.5,
            "nested": {"value": 3},
            "list": [2, {"inner": 4.2}],
        }

    def test_get_open_findings_summary(self, findings_manager):
        """Test getting summary of open findings by service"""
        # Create findings for different services
        findings_manager.put_finding("arn:aws:s3:::bucket1", "policy1", "123456789012_s3", 85, "ACTIVE", {}, int(time.time() * 1000))
        findings_manager.put_finding("arn:aws:s3:::bucket2", "policy1", "123456789012_s3", 50, "ACTIVE", {}, int(time.time() * 1000))
        findings_manager.put_finding("arn:aws:s3:::bucket3", "policy1", "123456789012_s3", 20, "RESOLVED", {}, int(time.time() * 1000))
        findings_manager.put_finding("arn:aws:ec2:::instance1", "policy2", "123456789012_ec2", 85, "ACTIVE", {}, int(time.time() * 1000))
        
        summary = findings_manager.get_open_findings_summary("123456789012")
        
        assert summary == {"s3": 2, "ec2": 1}

    def test_delete_findings_for_resource(self, findings_manager):
        """Test deleting all findings for a resource"""
        arn = "arn:aws:s3:::test-bucket"
        account_service = "123456789012_s3"
        
        # Create multiple findings for the resource
        findings_manager.put_finding(arn, "policy1", account_service, 85, "OPEN", {}, int(time.time() * 1000))
        findings_manager.put_finding(arn, "policy2", account_service, 50, "OPEN", {}, int(time.time() * 1000))
        
        # Verify findings exist
        findings = findings_manager.get_findings_for_resource(arn)
        assert len(findings) == 2
        
        # Delete findings
        findings_manager.delete_findings_for_resource(arn)
        
        # Verify findings are deleted
        findings = findings_manager.get_findings_for_resource(arn)
        assert len(findings) == 0

    def test_finding_dataclass(self):
        """Test Finding dataclass functionality"""
        finding = Finding(
            arn="arn:aws:s3:::test-bucket",
            policy="test-policy",
            account_service="123456789012_s3",
            severity=85,
            state="OPEN",
            first_seen="2023-01-01T00:00:00Z",
            last_evaluated="2023-01-01T01:00:00Z",
            evidence={"test": True}
        )
        
        assert finding.arn == "arn:aws:s3:::test-bucket"
        assert finding.policy == "test-policy"
        assert finding.account_service == "123456789012_s3"
        assert finding.severity == 85
        assert finding.state == "OPEN"
        assert finding.evidence == {"test": True}

    @patch('data_access.findings_manager.get_findings_table')
    def test_manager_initialization(self, mock_get_table):
        """Test FindingsManager initialization"""
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        manager = FindingsManager()
        assert manager.table == mock_table

    def test_pagination_token_handling(self, findings_manager):
        """Test pagination functionality"""
        account_service = "123456789012_s3"
        
        # Create multiple findings
        for i in range(10):
            findings_manager.put_finding(
                f"arn:aws:s3:::bucket{i:02d}", 
                "policy1", 
                account_service, 
                85, 
                "OPEN", 
                {}
            , int(time.time() * 1000))
        
        # Test paginated query
        result = findings_manager.get_findings_for_account_service_paginated(
            "123456789012", "s3", page_size=5
        )
        
        assert 'findings' in result
        assert 'count' in result
        assert len(result['findings']) <= 5
        assert result['count'] <= 5
        
        # If there are more results, next_token should be present
        if result['count'] == 5:
            assert 'next_token' in result

    def test_findings_summary_caching(self, findings_manager):
        """Test findings summary caching with 15-minute TTL"""
        # Mock PolicyManager inside the method where it's imported
        with patch('data_access.policy_manager.PolicyManager') as mock_pm_class:
            mock_pm_instance = MagicMock()
            mock_pm_instance.get_policy_definition.return_value = None
            mock_pm_class.return_value = mock_pm_instance
            
            account_service = "123456789012_s3"
            findings_manager.put_finding("arn:aws:s3:::bucket1", "policy1", account_service, 95, "ACTIVE", {}, int(time.time() * 1000))
            
            # First call - should compute and cache
            summary1 = findings_manager.get_findings_summary()
            assert summary1["total_findings"] == 1
            assert summary1["critical_findings"] == 1
            
            # Verify cache was saved
            cache_item = findings_manager.summary_table.get_item(Key={'Type': 'findings_summary_all'})
            assert 'Item' in cache_item
            assert 'summary' in cache_item['Item']
            assert 'updated_at' in cache_item['Item']
            
            # Add more findings
            findings_manager.put_finding("arn:aws:s3:::bucket2", "policy1", account_service, 70, "ACTIVE", {}, int(time.time() * 1000))
            
            # Second call - should return cached value (stale but fresh within 15 min)
            summary2 = findings_manager.get_findings_summary()
            assert summary2["total_findings"] == 1  # Still cached value
            
            # Verify cache hit by checking it's the same object structure
            assert summary2 == summary1
