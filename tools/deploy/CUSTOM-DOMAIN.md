# Custom Domain Setup for Qrie UI

This guide explains how to set up a custom domain for your Qrie UI instead of using the default CloudFront domain.

## Overview

By default, Qrie UI is accessible via a CloudFront domain like `d3ajiq1wfvnwon.cloudfront.net`. You can configure a custom domain such as:

- `us-east-1.customer.qrie.com`
- `qrie.customer.com` 
- `security.customer.com`

## Prerequisites

1. **Domain ownership**: You must own the domain you want to use
2. **DNS access**: Ability to create DNS records for your domain
3. **Deployed infrastructure**: QrieCore and QrieWeb stacks must be deployed

## Setup Process

### Option 1: Automated Setup (Recommended)

Use the provided script:

```bash
./tools/deploy/setup-custom-domain.sh us-east-1.customer.qrie.com us-east-1 qop
```

### Option 2: Manual Setup

1. **Deploy with custom domain**:
   ```bash
   cd qrie-infra
   source .venv/bin/activate
   cdk deploy QrieWeb -c ui_domain=us-east-1.customer.qrie.com --profile qop
   ```

2. **Get CloudFront domain**:
   ```bash
   aws cloudformation describe-stacks --stack-name QrieWeb --profile qop \
     --query "Stacks[0].Outputs[?OutputKey=='UiDistributionDomain'].OutputValue" --output text
   ```

3. **Create DNS record**:
   - Type: `CNAME`
   - Name: `us-east-1.customer.qrie.com`
   - Value: `d3ajiq1wfvnwon.cloudfront.net` (from step 2)

## Domain Naming Conventions

### Recommended Patterns

For multi-region deployments:
- `{region}.{customer}.qrie.com` (e.g., `us-east-1.acme.qrie.com`)
- `{region}.qrie.{customer}.com` (e.g., `us-east-1.qrie.acme.com`)

For single region:
- `qrie.{customer}.com` (e.g., `qrie.acme.com`)
- `security.{customer}.com` (e.g., `security.acme.com`)

### Examples

```bash
# Multi-region setup
./setup-custom-domain.sh us-east-1.acme.qrie.com us-east-1 qop
./setup-custom-domain.sh eu-west-1.acme.qrie.com eu-west-1 qop

# Single region
./setup-custom-domain.sh qrie.acme.com us-east-1 qop
```

## SSL Certificate

- SSL certificates are automatically provisioned via AWS Certificate Manager
- Certificates use DNS validation (requires the CNAME record)
- Certificates are created in `us-east-1` (required for CloudFront)

## DNS Propagation

- DNS changes can take 5-60 minutes to propagate
- SSL certificate validation may take 5-30 minutes after DNS propagation
- Total setup time: 10-90 minutes

## Verification

After setup, verify your custom domain:

```bash
# Check DNS resolution
nslookup us-east-1.customer.qrie.com

# Test HTTPS access
curl -I https://us-east-1.customer.qrie.com

# Check certificate
openssl s_client -connect us-east-1.customer.qrie.com:443 -servername us-east-1.customer.qrie.com
```

## Troubleshooting

### Common Issues

1. **DNS not resolving**: Wait for DNS propagation (up to 60 minutes)
2. **SSL certificate pending**: Ensure CNAME record is correct and propagated
3. **403 Forbidden**: Check S3 bucket policy and CloudFront OAC configuration

### Useful Commands

```bash
# Check stack outputs
aws cloudformation describe-stacks --stack-name QrieWeb --profile qop

# Check certificate status
aws acm list-certificates --region us-east-1 --profile qop

# Check CloudFront distribution
aws cloudfront list-distributions --profile qop
```

## Cleanup

To remove custom domain:

```bash
cd qrie-infra
cdk deploy QrieWeb --profile qop  # Deploy without ui_domain context
```

This will revert to the default CloudFront domain.
