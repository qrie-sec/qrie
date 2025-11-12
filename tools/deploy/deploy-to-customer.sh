#!/bin/bash
set -e

# Usage: ./deploy-to-customer.sh <customer-account-id> [region]
CUSTOMER_ACCOUNT_ID=$1
REGION=${2:-us-east-1}

if [ -z "$CUSTOMER_ACCOUNT_ID" ]; then
  echo "Usage: $0 <customer-account-id> [region]"
  exit 1
fi

echo "🚀 Deploying qrie to customer account: $CUSTOMER_ACCOUNT_ID"

# 1. Assume role in customer account
echo "🔐 Assuming deployment role..."
TEMP_ROLE=$(aws sts assume-role \
  --role-arn "arn:aws:iam::$CUSTOMER_ACCOUNT_ID:role/QrieDeploymentRole" \
  --role-session-name "qrie-deployment-$(date +%s)")

export AWS_ACCESS_KEY_ID=$(echo $TEMP_ROLE | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo $TEMP_ROLE | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo $TEMP_ROLE | jq -r '.Credentials.SessionToken')

# 2. Deploy infrastructure
echo "🏗️  Deploying infrastructure..."
cd qrie-infra
cdk deploy QrieCore --require-approval never

# 3. Get outputs
echo "📋 Getting deployment outputs..."
API_URL=$(aws cloudformation describe-stacks \
  --stack-name QrieCore \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

UI_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name QrieCore \
  --query 'Stacks[0].Outputs[?OutputKey==`UiBucket`].OutputValue' \
  --output text)

# 4. Build and deploy UI
echo "🎨 Building and deploying UI..."
cd ../qrie-ui
export NEXT_PUBLIC_API_BASE_URL="$API_URL"
npm run build

aws s3 sync ./out "s3://$UI_BUCKET/" --delete

echo "✅ Deployment complete!"
echo "🔗 API URL: $API_URL"
echo "🌐 UI Bucket: $UI_BUCKET"
