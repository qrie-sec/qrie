"""Unit tests for DashboardManager."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone

# Add lambda directory to path
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))

from data_access.dashboard_manager import DashboardManager  # noqa: E402


@pytest.fixture
def dashboard_manager():
    with (
        patch("data_access.dashboard_manager.get_summary_table") as mock_table,
        patch("data_access.dashboard_manager.PolicyManager") as mock_policy_mgr_cls,
        patch("data_access.dashboard_manager.FindingsManager") as mock_findings_mgr_cls,
        patch("data_access.dashboard_manager.InventoryManager") as mock_inventory_mgr_cls,
    ):
        # Configure mock DynamoDB table
        mock_ddb_table = MagicMock()
        mock_table.return_value = mock_ddb_table
        
        # Configure mock policy manager
        mock_policy_mgr = MagicMock()
        mock_policy_mgr.list_launched_policies.return_value = [object(), object(), object()]
        
        # Mock policy definition
        mock_policy_def = MagicMock()
        mock_policy_def.severity = 90
        mock_policy_mgr.get_policy_definition.return_value = mock_policy_def
        mock_policy_mgr_cls.return_value = mock_policy_mgr

        # Configure mock inventory manager
        mock_inventory_mgr = MagicMock()
        mock_inventory_mgr.get_resources_summary.return_value = {
            "total_resources": 120,
            "total_accounts": 4,
        }
        mock_inventory_mgr_cls.return_value = mock_inventory_mgr

        # Configure mock findings manager
        mock_findings_mgr = MagicMock()
        mock_findings_mgr.get_findings_summary.return_value = {
            "total_findings": 100,
            "open_findings": 50,
            "resolved_findings": 50,
            "critical_findings": 8,
            "high_findings": 20,
            "medium_findings": 15,
            "low_findings": 7,
            "policies": [
                {"policy": "S3BucketPublic", "open_findings": 25, "severity": 90, "resolved_findings": 10},
                {"policy": "EC2Unencrypted", "open_findings": 15, "severity": 70, "resolved_findings": 5},
            ]
        }
        
        # Mock table scan for weekly findings
        mock_findings_mgr.table = MagicMock()
        mock_findings_mgr.table.scan.return_value = {
            "Items": [
                {
                    "State": "ACTIVE",
                    "Severity": 90,
                    "FirstSeen": "2024-10-15T10:00:00Z",
                    "LastEvaluated": "2024-10-15T10:00:00Z"
                },
                {
                    "State": "RESOLVED",
                    "Severity": 70,
                    "FirstSeen": "2024-10-10T10:00:00Z",
                    "LastEvaluated": "2024-10-16T10:00:00Z"
                }
            ]
        }
        
        mock_findings_mgr_cls.return_value = mock_findings_mgr

        manager = DashboardManager()
        return manager, mock_ddb_table, mock_policy_mgr, mock_findings_mgr, mock_inventory_mgr


def test_get_dashboard_summary_cache_miss(dashboard_manager):
    """Test dashboard summary computation when cache is empty."""
    manager, mock_table, policy_mgr, findings_mgr, inventory_mgr = dashboard_manager
    
    # Mock cache miss
    mock_table.get_item.return_value = {}
    
    # Mock lock acquisition
    mock_table.put_item.return_value = {}
    
    summary = manager.get_dashboard_summary("2024-10-17")
    
    # Verify structure
    assert "total_open_findings" in summary
    assert "critical_open_findings" in summary
    assert "high_open_findings" in summary
    assert "resolved_this_month" in summary
    assert "active_policies" in summary
    assert "resources" in summary
    assert "accounts" in summary
    assert "findings_weekly" in summary
    assert "top_policies" in summary
    assert "policies_launched_this_month" in summary
    
    # Verify values
    assert summary["total_open_findings"] == 50
    assert summary["critical_open_findings"] == 8
    assert summary["high_open_findings"] == 20
    assert summary["active_policies"] == 3
    assert summary["resources"] == 120
    assert summary["accounts"] == 4
    
    # Verify weekly findings is an array
    assert isinstance(summary["findings_weekly"], list)
    assert len(summary["findings_weekly"]) == 8
    
    # Verify top policies
    assert isinstance(summary["top_policies"], list)
    assert len(summary["top_policies"]) == 2
    assert summary["top_policies"][0]["policy_id"] == "S3BucketPublic"
    assert summary["top_policies"][0]["open_findings"] == 25
    
    # Verify managers were called
    assert policy_mgr.list_launched_policies.called
    assert findings_mgr.get_findings_summary.called
    assert inventory_mgr.get_resources_summary.called
    
    # Verify cache was saved
    assert mock_table.put_item.call_count >= 1


def test_get_dashboard_summary_cache_hit(dashboard_manager):
    """Test dashboard summary returns cached data when fresh."""
    manager, mock_table, policy_mgr, findings_mgr, inventory_mgr = dashboard_manager
    
    # Mock fresh cache
    cached_summary = {
        "total_open_findings": 100,
        "critical_open_findings": 20,
        "high_open_findings": 40,
        "resolved_this_month": 15,
        "active_policies": 5,
        "resources": 500,
        "accounts": 10,
        "findings_weekly": [],
        "top_policies": [],
        "policies_launched_this_month": 1
    }
    
    mock_table.get_item.return_value = {
        "Item": {
            "Type": "dashboard",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "summary": cached_summary
        }
    }
    
    summary = manager.get_dashboard_summary("2024-10-17")
    
    # Should return cached data
    assert summary == cached_summary
    
    # Should not call managers (cache hit)
    assert not policy_mgr.list_launched_policies.called
    assert not findings_mgr.get_findings_summary.called
    assert not inventory_mgr.get_resources_summary.called


def test_weekly_findings_structure(dashboard_manager):
    """Test weekly findings data structure."""
    manager, mock_table, *_ = dashboard_manager
    
    # Mock cache miss to trigger computation
    mock_table.get_item.return_value = {}
    mock_table.put_item.return_value = {}
    
    summary = manager.get_dashboard_summary("2024-10-17")
    
    # Verify weekly findings structure
    weekly = summary["findings_weekly"]
    assert len(weekly) == 8
    
    for week in weekly:
        assert "week_start" in week
        assert "total_findings" in week
        assert "open_findings" in week
        assert "new_findings" in week
        assert "closed_findings" in week
        assert "critical_new" in week
        assert "is_current" in week
        
        # Verify types
        assert isinstance(week["week_start"], str)
        assert isinstance(week["total_findings"], int)
        assert isinstance(week["open_findings"], int)
        assert isinstance(week["new_findings"], int)
        assert isinstance(week["closed_findings"], int)
        assert isinstance(week["critical_new"], int)
        assert isinstance(week["is_current"], bool)
    
    # Last week should be current
    assert weekly[-1]["is_current"] == True
    # Other weeks should not be current
    assert all(not w["is_current"] for w in weekly[:-1])


def test_top_policies_structure(dashboard_manager):
    """Test top policies data structure."""
    manager, mock_table, *_ = dashboard_manager
    
    # Mock cache miss to trigger computation
    mock_table.get_item.return_value = {}
    mock_table.put_item.return_value = {}
    
    summary = manager.get_dashboard_summary("2024-10-17")
    
    # Verify top policies structure
    top_policies = summary["top_policies"]
    assert isinstance(top_policies, list)
    assert len(top_policies) <= 10  # Max 10 policies
    
    for policy in top_policies:
        assert "policy_id" in policy
        assert "open_findings" in policy
        assert "severity" in policy
        
        # Verify types
        assert isinstance(policy["policy_id"], str)
        assert isinstance(policy["open_findings"], int)
        assert isinstance(policy["severity"], int)
        
        # Verify severity range
        assert 0 <= policy["severity"] <= 100


def test_lock_acquisition_failure(dashboard_manager):
    """Test behavior when lock acquisition fails (concurrent refresh)."""
    manager, mock_table, *_ = dashboard_manager
    
    # Mock stale cache
    old_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat()
    stale_summary = {
        "total_findings": 50,
        "total_open_findings": 25,
        "critical_open_findings": 5,
        "active_policies": 2,
        "resources": 100,
        "accounts": 2,
        "findings_weekly": [],
        "top_policies": [],
        "policies_launched_this_month": 0
    }
    
    mock_table.get_item.return_value = {
        "Item": {
            "Type": "dashboard",
            "updated_at": old_time,
            "summary": stale_summary
        }
    }
    
    # Mock lock acquisition failure (ConditionalCheckFailedException)
    from botocore.exceptions import ClientError
    mock_table.put_item.side_effect = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException"}},
        "PutItem"
    )
    
    summary = manager.get_dashboard_summary("2024-10-17")
    
    # Should serve stale data when lock fails
    assert summary == stale_summary
