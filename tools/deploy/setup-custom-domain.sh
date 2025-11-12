#!/bin/bash

# Setup Custom Domain for Qrie UI
# Usage: ./setup-custom-domain.sh <domain> <region> <profile>
# Example: ./setup-custom-domain.sh us-east-1.customer.qrie.com us-east-1 qop

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check arguments
if [ $# -ne 3 ]; then
    print_error "Usage: $0 <domain> <region> <profile>"
    print_error "Example: $0 us-east-1.customer.qrie.com us-east-1 qop"
    exit 1
fi

DOMAIN=$1
REGION=$2
PROFILE=$3

print_status "Setting up custom domain: $DOMAIN"
print_status "Region: $REGION"
print_status "Profile: $PROFILE"

# Navigate to qrie-infra directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INFRA_DIR="$PROJECT_ROOT/qrie-infra"

if [ ! -f "$INFRA_DIR/cdk.json" ]; then
    print_error "qrie-infra directory not found at $INFRA_DIR"
    exit 1
fi

cd "$INFRA_DIR"
print_status "Working directory: $(pwd)"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    print_success "Virtual environment activated"
else
    print_error "Virtual environment not found. Please run setup first."
    exit 1
fi

# Deploy QrieWeb stack with custom domain
print_status "Deploying QrieWeb stack with custom domain..."
cdk deploy QrieWeb \
    --profile "$PROFILE" \
    --region "$REGION" \
    -c ui_domain="$DOMAIN" \
    --require-approval never

# Get CloudFront distribution domain
CLOUDFRONT_DOMAIN=$(aws cloudformation describe-stacks \
    --stack-name QrieWeb \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='UiDistributionDomain'].OutputValue" \
    --output text)

print_success "Custom domain deployment completed!"
print_warning "IMPORTANT: You need to create a DNS record to complete the setup:"
echo ""
echo "DNS Configuration Required:"
echo "  Type: CNAME"
echo "  Name: $DOMAIN"
echo "  Value: $CLOUDFRONT_DOMAIN"
echo ""
print_warning "The SSL certificate will be automatically validated via DNS once the CNAME is created."
print_status "After DNS propagation, your UI will be available at: https://$DOMAIN"

# Show current status
print_status "Current CloudFront domain: https://$CLOUDFRONT_DOMAIN"
print_status "Target custom domain: https://$DOMAIN"
