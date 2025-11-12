
# Qrie Infrastructure

AWS CDK infrastructure for Qrie On-Premises (QOP) accounts.

## 🏗️ Architecture

### Stacks

- **QrieCore**: Main infrastructure stack with DynamoDB tables, Lambda functions, and IAM roles
- **QrieWeb**: UI hosting stack with S3 bucket and CloudFront distribution

### Components

```
lambda/
├── api/                    # API handlers for UI endpoints
├── data_access/           # Data access layer with caching
├── event_processor/       # CloudTrail event processing
├── inventory_generator/   # Resource inventory collection
├── scan_processor/        # Policy evaluation engine
├── policies/              # Security policy definitions
└── common.py             # Shared utilities

stacks/
├── core_stack.py         # Main infrastructure stack
└── web_stack.py          # UI hosting stack
```

## 🚀 Deployment

### Prerequisites

```bash
# Install CDK CLI
npm install -g aws-cdk

# Setup Python environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap
```

### Deploy Infrastructure

```bash
# From project root
./qop.py --deploy-core --region us-east-1 --profile your-profile

# Or manually
cdk deploy QrieCore --require-approval never
```

### Deploy UI Hosting

```bash
cdk deploy QrieWeb --require-approval never
```

## 🔧 Development

### Policy Development

See [POLICY_NAMING.md](./POLICY_NAMING.md) for policy naming conventions and guidelines.

**Quick Reference:**
- Policy names describe the **non-compliant state** being detected
- Format: `{Service}{NonCompliantCondition}` (e.g., `S3BucketPublic`, `EC2UnencryptedEBS`)
- Use PascalCase for policy IDs, snake_case for file names

### Local Testing

```bash
# Run unit tests
./qop.py --test-unit

# Run integration tests (requires deployed infrastructure)
./qop.py --test-integ --region us-east-1 --profile your-profile
```

### Useful CDK Commands

```bash
cdk ls                    # List all stacks
cdk synth                 # Synthesize CloudFormation templates
cdk diff                  # Compare deployed stack with current state
cdk deploy QrieCore       # Deploy specific stack
cdk destroy QrieCore      # Delete stack
```

## 📊 Monitoring

### CloudWatch Logs

```bash
# Use the color-coded monitoring script (recommended)
../tools/debug/monitor-lambda-logs.sh us-east-1 qop

# Or directly with AWS CLI
# API logs (with color-coded levels: DEBUG=gray, INFO=light gray, WARN=yellow, ERROR=red, FATAL=magenta)
aws logs tail "/aws/lambda/qrie_api_handler" --follow --region us-east-1 --profile qop

# Event processing logs
aws logs tail "/aws/lambda/qrie_event_processor" --follow --region us-east-1 --profile qop

# Inventory generation logs
aws logs tail "/aws/lambda/qrie_inventory_generator" --follow --region us-east-1 --profile qop
```

**Request Correlation**: All API requests log with AWS request ID for correlation:
- Format: `[abc123-def456-789ghi] POST /policies/launch`
- Policy operations include policy_id: `Launch policy request: policy_id=S3BucketPublic`
- Errors include full stack traces and request context

### Stack Outputs

After deployment, get important URLs and identifiers:

```bash
aws cloudformation describe-stacks --stack-name QrieCore --query 'Stacks[0].Outputs'

# Or use the orchestrator
../qop.py --info --region us-east-1 --profile qop
```

## 🔐 Security

### IAM Roles

- **QrieReadOnly-{account}**: Cross-account read access for customer accounts
- **Lambda execution roles**: Scoped permissions for each Lambda function
- **Event processing role**: Permissions to write to DynamoDB tables

### Data Storage

- **qrie_accounts**: Customer account registry
- **qrie_resources**: Resource inventory with configurations
- **qrie_findings**: Security findings and compliance violations
- **qrie_policies**: Launched policy configurations

## 🧪 Testing

### Unit Tests

Located in `tests/unit/` - test data access layer and business logic.

### Integration Tests

Test deployed infrastructure with real AWS resources.

### API Tests

Comprehensive testing of all API endpoints with various scenarios.
