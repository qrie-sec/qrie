#!/bin/bash

# Backward compatibility wrapper for monitor-logs.sh
# This script now redirects to the new monitor-logs.sh with 'api' as default
# Usage: ./monitor-lambda-logs.sh [region] [profile]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REGION="${1:-us-east-1}"
PROFILE="${2:-qop}"

# Call the new script with 'api' as the lambda name
exec "$SCRIPT_DIR/monitor-logs.sh" api "$REGION" "$PROFILE"
