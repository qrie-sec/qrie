"""Dashboard API - Handles dashboard summary requests."""
import os
import json
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.logger import info
from common.exceptions import ValidationError
from data_access.dashboard_manager import DashboardManager

# Initialize manager lazily
dashboard_manager = None


def get_dashboard_manager():
    """Return a cached DashboardManager instance."""
    global dashboard_manager
    if dashboard_manager is None:
        dashboard_manager = DashboardManager()
    return dashboard_manager


def handle_get_dashboard_summary(query_params, headers):
    """Handle GET /summary/dashboard?date=<YYYY-MM-DD>"""
    date = query_params.get('date')
    
    info(f"Dashboard summary request: date={date}")
    
    if not date:
        raise ValidationError('date parameter is required (YYYY-MM-DD format)')
    
    # Basic date format validation
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise ValidationError('Invalid date format. Use YYYY-MM-DD')
    
    summary = get_dashboard_manager().get_dashboard_summary(date)
    
    info(f"Dashboard summary retrieved: {summary['total_open_findings']} open findings, "
          f"{summary['active_policies']} active policies, {summary['resources']} resources")
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(summary)
    }
