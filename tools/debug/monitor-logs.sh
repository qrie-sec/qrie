#!/bin/bash

# Script to monitor Qrie Lambda logs in real-time
# Usage: ./monitor-logs.sh [lambda-name] [region] [profile]
#
# Lambda names: api, event, scan, inventory, all
# Default: api

set -e

LAMBDA_NAME="${1:-api}"
REGION="${2:-us-east-1}"
PROFILE="${3:-qop}"

# Map lambda names to log groups
case "$LAMBDA_NAME" in
    api)
        LOG_GROUP="/aws/lambda/qrie_api_handler"
        DISPLAY_NAME="API Handler"
        ;;
    event|event-processor)
        LOG_GROUP="/aws/lambda/qrie_event_processor"
        DISPLAY_NAME="Event Processor"
        ;;
    scan|policy-scanner)
        LOG_GROUP="/aws/lambda/qrie_policy_scanner"
        DISPLAY_NAME="Policy Scanner"
        ;;
    inventory|inventory-generator)
        LOG_GROUP="/aws/lambda/qrie_inventory_generator"
        DISPLAY_NAME="Inventory Generator"
        ;;
    all)
        echo "🔍 Monitoring ALL Qrie Lambda logs..."
        echo "Region: $REGION"
        echo "Profile: $PROFILE"
        echo ""
        echo "Available Lambda functions:"
        echo "  - qrie_api_handler"
        echo "  - qrie_event_processor"
        echo "  - qrie_policy_scanner"
        echo "  - qrie_inventory_generator"
        echo ""
        echo "Use: ./monitor-logs.sh [lambda-name] to monitor a specific Lambda"
        echo "     lambda-name: api, event, scan, inventory"
        exit 0
        ;;
    *)
        echo "❌ Unknown Lambda name: $LAMBDA_NAME"
        echo ""
        echo "Usage: ./monitor-logs.sh [lambda-name] [region] [profile]"
        echo ""
        echo "Available lambda names:"
        echo "  api              - API Handler"
        echo "  event            - Event Processor"
        echo "  scan             - Policy Scanner"
        echo "  inventory        - Inventory Generator"
        echo "  all              - Show all available Lambdas"
        echo ""
        echo "Examples:"
        echo "  ./monitor-logs.sh event us-east-1 qop"
        echo "  ./monitor-logs.sh api"
        exit 1
        ;;
esac

echo "🔍 Monitoring $DISPLAY_NAME logs..."
echo "Log Group: $LOG_GROUP"
echo "Region: $REGION"
echo "Profile: $PROFILE"
echo ""

# Check if log group exists
echo "Checking if log group exists..."
if ! aws logs describe-log-groups \
    --log-group-name-prefix "$LOG_GROUP" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query "logGroups[?logGroupName=='$LOG_GROUP']" \
    --output text 2>/dev/null | grep -q "$LOG_GROUP"; then
    echo "❌ Log group not found: $LOG_GROUP"
    echo ""
    echo "Possible reasons:"
    echo "  1. Lambda function hasn't been deployed yet"
    echo "  2. Wrong region (check --region)"
    echo "  3. Wrong AWS profile (check --profile)"
    echo ""
    echo "Available log groups:"
    aws logs describe-log-groups \
        --log-group-name-prefix "/aws/lambda/qrie" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query "logGroups[].logGroupName" \
        --output text 2>/dev/null || echo "  (none found)"
    exit 1
fi

echo "✅ Log group found"
echo ""
echo "💡 Tip: Invoke the Lambda to see logs appear here"
echo "   Example: Trigger an S3 event or manually invoke the Lambda"
echo ""
echo "Press Ctrl+C to stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Color codes
GRAY='\033[0;90m'
LIGHT_GRAY='\033[0;37m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
RESET='\033[0m'

# Tail logs in real-time with color coding
# Note: --follow will wait for new logs even if none exist yet
aws logs tail "$LOG_GROUP" \
    --follow \
    --format short \
    --region "$REGION" \
    --profile "$PROFILE" 2>&1 | awk -v gray="$GRAY" -v light_gray="$LIGHT_GRAY" -v yellow="$YELLOW" -v red="$RED" -v magenta="$MAGENTA" -v reset="$RESET" '
{
    line = $0
    if (line ~ /DEBUG/) {
        print gray line reset
    } else if (line ~ /INFO/) {
        print light_gray line reset
    } else if (line ~ /WARN/) {
        print yellow line reset
    } else if (line ~ /ERROR/) {
        print red line reset
    } else if (line ~ /FATAL/) {
        print magenta line reset
    } else {
        print line
    }
    fflush()
}'
