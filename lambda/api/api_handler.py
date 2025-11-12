"""API handler - single Lambda URL entry point for the qrie UI."""
import os
import json
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.logger import info, error
from common.exceptions import ApiException

# Import handlers from individual API modules
from api.resources_api import (
    handle_list_resources_paginated,
    handle_list_accounts as resources_handle_list_accounts,
    handle_list_services,
    handle_get_resources_summary,
)
from api.findings_api import handle_list_findings_paginated, handle_get_findings_summary
from api.policies_api import (
    handle_get_policies,
    handle_launch_policy,
    handle_update_policy,
    handle_delete_policy,
)
from api.dashboard_api import handle_get_dashboard_summary


def lambda_handler(event, context):
    """Route supported UI endpoints to their handlers."""
    try:
        # Parse request
        method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
        path = event.get("rawPath", "/")
        query_params = event.get("queryStringParameters") or {}
        request_id = context.aws_request_id if context else "unknown"
        
        # Log incoming request with ID for correlation
        info(f"[{request_id}] {method} {path}")

        # Headers (CORS is handled by Lambda Function URL configuration)
        headers = {
            "Content-Type": "application/json",
        }

        # Handle preflight OPTIONS request
        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": headers,
                "body": "",
            }

        # Route to appropriate handlers
        if path == "/resources" and method == "GET":
            return handle_list_resources_paginated(query_params, headers)

        if path == "/accounts" and method == "GET":
            return resources_handle_list_accounts(headers)

        if path == "/services" and method == "GET":
            return handle_list_services(query_params, headers)

        if path == "/findings" and method == "GET":
            return handle_list_findings_paginated(query_params, headers)

        # Unified policies endpoint
        if path == "/policies" and method == "GET":
            return handle_get_policies(query_params, headers)
        
        if path == "/policies" and method == "POST":
            body = event.get("body", "{}")
            return handle_launch_policy(body, headers)
        
        # Policy-specific endpoints with path parameters
        if path.startswith("/policies/") and method == "PUT":
            policy_id = path.split("/")[-1]
            body = event.get("body", "{}")
            return handle_update_policy(policy_id, body, headers)
        
        if path.startswith("/policies/") and method == "DELETE":
            policy_id = path.split("/")[-1]
            return handle_delete_policy(policy_id, headers)

        # Summary endpoints
        if path == "/summary/dashboard" and method == "GET":
            return handle_get_dashboard_summary(query_params, headers)
            
        if path == "/summary/resources" and method == "GET":
            return handle_get_resources_summary(query_params, headers)
            
        if path == "/summary/findings" and method == "GET":
            return handle_get_findings_summary(query_params, headers)

        return {
            "statusCode": 404,
            "headers": headers,
            "body": json.dumps({"error": f"Endpoint not found: {method} {path}"}),
        }

    except ApiException as err:
        # Handle custom API exceptions with specific status codes
        request_id = context.aws_request_id if context else "unknown"
        import traceback
        error(f"[{request_id}] API error ({err.status_code}): {err.message}\n{traceback.format_exc()}")
        
        response_body = {"error": err.message}
        if err.details:
            response_body["details"] = err.details
        
        return {
            "statusCode": err.status_code,
            "headers": headers,
            "body": json.dumps(response_body),
        }
    
    except Exception as err:  # pylint: disable=broad-except
        # Handle unexpected exceptions
        request_id = context.aws_request_id if context else "unknown"
        import traceback
        error(f"[{request_id}] Unexpected error: {err}\n{traceback.format_exc()}")

        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": "Internal server error"}),
        }
