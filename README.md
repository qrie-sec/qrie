# Qrie - Cloud Security Posture Management (CSPM)

Qrie is a non-SaaS, on-premises CSPM solution that provides dedicated AWS accounts for security and compliance monitoring.

---

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Node.js 18+ and Python 3.12+
- CDK CLI installed (`npm install -g aws-cdk`)

### Setup & Deployment

```bash
# Clone and setup
git clone <repository-url>
cd qrie
python -m venv .venv
source .venv/bin/activate

# Configure AWS credentials
aws configure --profile qop

# Build and deploy
./qop.py --build --region us-east-1
./qop.py --deploy-core --region us-east-1 --profile qop
./qop.py --deploy-ui --region us-east-1 --profile qop

# Get deployment info
./qop.py --info --region us-east-1 --profile qop
```

### Get Help

```bash
./qop.py -h
```

---

## 🏗️ Architecture

### System Overview

qrie provides:
- **Real-time drift detection** via CloudTrail events
- **Scheduled compliance scans** (weekly inventory, daily policy evaluation)
- **Multi-account monitoring** from a centralized QOP (Qrie On-Premises) account
- **Policy-based security findings** with remediation guidance

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Customer AWS Accounts                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │  Account A │  │  Account B │  │  Account C │           │
│  │ CloudTrail │  │ CloudTrail │  │ CloudTrail │           │
│  │     ↓      │  │     ↓      │  │     ↓      │           │
│  │ EventBridge│  │ EventBridge│  │ EventBridge│           │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘           │
│        └────────────────┴────────────────┘                   │
└─────────────────────────┼─────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    QOP Account (us-east-1)                   │
│  EventBridge → SQS → Lambda Functions → DynamoDB            │
│  API Lambda ← UI (CloudFront + S3)                          │
└─────────────────────────────────────────────────────────────┘
```

### Repository Structure

- **[qrie-infra/](qrie-infra/README.md)**: AWS CDK infrastructure code for QOP accounts
- **[qrie-ui/](qrie-ui/README.md)**: Next.js frontend for security dashboard
- **qrie-lp/**: Landing page and marketing site
- **tools/**: Scripts for build, test, deploy, and data operations

---

## 📊 Operations

### Monitoring

```bash
# Color-coded log monitoring (recommended)
./tools/debug/monitor-lambda-logs.sh [region] [profile]

# Direct AWS CLI
aws logs tail "/aws/lambda/qrie_api_handler" --follow --region us-east-1 --profile qop
aws logs tail "/aws/lambda/qrie_event_processor" --follow --region us-east-1 --profile qop
```

**Log Correlation**: All API requests include request ID: `[abc123-def456] POST /policies/launch`

### Test Endpoints

After deployment, test these endpoints:
- `GET /accounts` - Customer accounts
- `GET /resources` - Resource inventory
- `GET /findings` - Security findings
- `GET /policies` - Policy management
- `GET /summary/dashboard` - Dashboard data
- `POST /policies` - Launch new policy
- `PUT /policies/{policy_id}` - Update policy
- `DELETE /policies/{policy_id}` - Delete policy

### Customer Onboarding

**1. QOP Setup** (one-time per region):
```bash
./qop.py --deploy-core --region us-east-1 --profile qop
./qop.py --deploy-ui --region us-east-1 --profile qop
```

**2. Customer Account Setup**:
```bash
# Deploy EventBridge rules in customer account
aws cloudformation deploy \
  --template-file qrie-infra/onboarding/customer_bootstrap.yaml \
  --stack-name qrie-eventbridge-rules \
  --parameter-overrides QopAccountId=<QOP_ACCOUNT_ID> QopRegion=us-east-1 \
  --region us-east-1 \
  --profile customer

# Create IAM role for cross-account access
aws cloudformation deploy \
  --template-file tools/onboarding/iam-role.yaml \
  --stack-name qrie-inventory-role \
  --parameter-overrides QopAccountId=<QOP_ACCOUNT_ID> \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1 \
  --profile customer
```

**3. Add Account to qrie**:
```bash
aws dynamodb put-item \
  --table-name qrie_accounts \
  --item '{"account_id": {"S": "<CUSTOMER_ACCOUNT_ID>"}, "account_name": {"S": "Customer Name"}, "status": {"S": "active"}}' \
  --region us-east-1 \
  --profile qop
```

**4. Run Initial Inventory**:
```bash
./qop.py --generate-inventory --region us-east-1 --profile qop
```

**5. Launch Policies**: Navigate to UI → Management page and launch desired policies

### Customer Bootstrap Template

**Source of Truth:** `qrie-infra/onboarding/customer_bootstrap.yaml`  
**Served to Customers:** `qrie-lp/public/onboarding/customer_bootstrap.yaml` (copy)

To update:
```bash
vim qrie-infra/onboarding/customer_bootstrap.yaml
cp qrie-infra/onboarding/customer_bootstrap.yaml qrie-lp/public/onboarding/
```

---

## 🔧 Development

### Local Setup

```bash
# Python environment
cd qrie-infra
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# UI environment
cd ../qrie-ui
pnpm install
```

### Running Tests

```bash
# Unit tests
./qop.py --test-unit

# Or directly with pytest
cd qrie-infra
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=lambda --cov-report=html
open htmlcov/index.html

# E2E tests (requires deployed infrastructure)
pytest tests/e2e/ -v --region us-east-1 --profile qop
```

### Local UI Development

```bash
cd qrie-ui
pnpm dev  # Opens http://localhost:3000
```

**Note**: Update `.env.local` to point to your deployed API URL

### Code Layout

```
qrie/
├── qop.py                          # Main orchestrator CLI
├── qrie-infra/                     # Backend & infrastructure
│   ├── app.py                      # CDK app entry point
│   ├── stacks/
│   │   ├── core_stack.py           # Lambda, DynamoDB, EventBridge
│   │   └── web_stack.py            # CloudFront, S3, UI hosting
│   ├── lambda/
│   │   ├── common/                 # Shared modules
│   │   ├── services/               # Service-specific support (S3, EC2, IAM)
│   │   ├── api/                    # API handlers
│   │   ├── data_access/            # Data access layer
│   │   ├── event_processor/        # Real-time event processing
│   │   ├── inventory_generator/    # Scheduled inventory scans
│   │   ├── scan_processor/         # Policy evaluation
│   │   └── policies/               # Policy evaluators
│   └── tests/
│       ├── unit/                   # Unit tests
│       └── e2e/                    # End-to-end tests
├── qrie-ui/                        # Frontend application
│   ├── app/                        # Next.js app router
│   ├── components/                 # React components
│   └── lib/                        # API client & types
├── tools/                          # Operational tools
│   ├── debug/                      # Log monitoring
│   ├── deploy/                     # Deployment scripts
│   └── data/                       # Test data generation
└── changelog/                      # Change documentation
```

### Key Design Patterns

**Service Registry Pattern**:
- `services/__init__.py` provides dynamic service loading
- Each service has `extract_arn_from_event()`, `describe_resource()`, `list_resources()`
- No inheritance, composition-based

**Data Access Layer**:
- All DynamoDB access goes through `*_manager.py` modules
- Caching with `@lru_cache` for expensive operations
- No direct table access from business logic

**Fail-Fast Exception Handling**:
- Lower/middle layers let exceptions bubble up
- Top-level handlers catch, log with stack traces, return HTTP status
- No defensive defaults or exception swallowing

### Data Flow

**Real-Time Event Processing**:
1. Resource change in customer account → CloudTrail event
2. EventBridge forwards to QOP account SQS queue
3. Event Processor Lambda triggered
4. Extract ARN, describe resource, compare with inventory
5. If changed: update inventory, evaluate active policies
6. Create/resolve findings based on policy evaluation

**Scheduled Scans**:
1. **Weekly Inventory** (Saturday 00:00 UTC): Full resource scan
2. **Daily Policy Scan** (04:00 UTC): Re-evaluate all resources
3. Both update drift metrics in summary table

**API & UI**:
1. UI makes API calls to Lambda URL
2. Lambda queries DynamoDB tables
3. Returns JSON responses
4. UI renders data with React/Next.js

---

## 🧪 Testing

### E2E Testing with Real Resources

```bash
# Create non-compliant resources (generates findings)
./qop.py --seed-resources non-compliant --account-id 050261919630 --region us-east-1 --profile qop

# Wait 2-3 minutes for CloudTrail events to process

# Verify findings
curl "https://your-api-url/findings?account_id=050261919630"

# Make resources compliant (test remediation)
./qop.py --seed-resources remediate --account-id 050261919630 --region us-east-1 --profile qop

# Cleanup
./qop.py --seed-resources cleanup --account-id 050261919630 --region us-east-1 --profile qop
```

**What it creates:**
- S3 buckets (with/without encryption, versioning, public access)
- IAM users (with/without access keys, MFA)
- IAM password policies (compliant/non-compliant)

### Test Structure

Unit tests should:
- Mock all AWS API calls (use `pytest-mock` or `moto`)
- Test business logic in isolation
- Not require AWS credentials
- Run fast (<1 second per test)

Example:
```python
def test_s3_bucket_public_detected(evaluator, mocker):
    """Test that public bucket is detected as non-compliant"""
    mocker.patch('data_access.findings_manager.FindingsManager')
    
    resource_arn = 'arn:aws:s3:::my-public-bucket'
    config = {
        'PublicAccessBlockConfiguration': {
            'BlockPublicAcls': False  # Public!
        }
    }
    
    result = evaluator.evaluate(resource_arn, config, int(time.time() * 1000))
    
    assert result['compliant'] is False
    assert 'publicly accessible' in result['message']
```

---

## 🔌 Onboarding New Services

To add support for a new AWS service (e.g., RDS):

### 1. Add to SUPPORTED_SERVICES

```python
# lambda/common_utils.py
SUPPORTED_SERVICES = ["s3", "ec2", "iam", "rds"]  # Add 'rds'
```

### 2. Create Service Support Module

```python
# lambda/services/rds_support.py

def extract_arn_from_event(detail: dict) -> Optional[str]:
    """Extract RDS resource ARN from CloudTrail event"""
    resources = detail.get('resources', [])
    if resources:
        return resources[0].get('ARN')
    return None

def describe_resource(arn: str, account_id: str, rds_client=None) -> dict:
    """Describe RDS instance/cluster configuration"""
    # Assume role, create client, describe resource
    return config

def list_resources(account_id: str, rds_client=None) -> dict:
    """List all RDS instances/clusters in account"""
    return {'resources': resources, 'failed_count': failed_count}
```

### 3. Add EventBridge Rules

Update `qrie-infra/onboarding/customer_bootstrap.yaml`:
```yaml
RDSEventRule:
  Type: AWS::Events::Rule
  Properties:
    EventPattern:
      source: [aws.rds]
      detail-type: [AWS API Call via CloudTrail]
      detail:
        eventName: [CreateDBInstance, ModifyDBInstance, DeleteDBInstance]
    Targets:
      - Arn: !Sub 'arn:aws:events:${QopRegion}:${QopAccountId}:event-bus/default'
        RoleArn: !GetAtt EventBridgeRole.Arn
```

### 4. Create Policy Evaluators

```python
# lambda/policies/rds_public_access.py
from policy_definition import PolicyEvaluator

class RDSPublicAccessEvaluator(PolicyEvaluator):
    def evaluate(self, resource_arn: str, config: dict, describe_time_ms: int) -> dict:
        publicly_accessible = config.get('PubliclyAccessible', False)
        
        if publicly_accessible:
            return self.create_finding(
                resource_arn=resource_arn,
                compliant=False,
                message="RDS instance is publicly accessible",
                evidence={'publicly_accessible': True},
                describe_time_ms=describe_time_ms
            )
        
        return self.resolve_finding(
            resource_arn=resource_arn,
            message="RDS instance is not publicly accessible"
        )
```

### 5. Add Tests

```python
# tests/unit/test_rds_public_access_evaluator.py
def test_public_rds_detected(evaluator, mocker):
    mocker.patch('data_access.findings_manager.FindingsManager')
    config = {'PubliclyAccessible': True}
    result = evaluator.evaluate('arn:aws:rds:...', config, int(time.time() * 1000))
    assert result['compliant'] is False

# tests/e2e/test_rds_e2e.py
def test_rds_public_instance_e2e(test_account_id):
    # Create public RDS instance, wait, verify, cleanup
    pass
```

### 6. Update Documentation

- Add service to supported services list
- Document service-specific notes
- Update UI docs if needed

---

## 🐛 Troubleshooting

### Events Not Processing

1. Check SQS queue has messages:
```bash
aws sqs get-queue-attributes \
  --queue-url $(aws sqs list-queues --region us-east-1 --profile qop | jq -r '.QueueUrls[0]') \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1 --profile qop
```

2. Check Lambda logs:
```bash
./tools/debug/monitor-lambda-logs.sh us-east-1 qop
```

3. Verify EventBridge rules in customer account:
```bash
aws events list-rules --region us-east-1 --profile customer
```

### Inventory Not Updating

1. Check scheduled rules are enabled:
```bash
aws events list-rules --region us-east-1 --profile qop
```

2. Check Lambda execution:
```bash
./tools/debug/monitor-lambda-logs.sh us-east-1 qop
```

3. Verify IAM role trust relationship in customer account

### UI Not Loading

1. Check CloudFront distribution status
2. Verify S3 bucket has files
3. Check API URL in browser console (Network tab)
4. Verify CORS settings on Lambda URL

---

## 🧹 Cleanup

```bash
cd qrie-infra
cdk destroy QrieCore QrieWeb
```

---

## 🔐 Security

- All customer data stays in dedicated QOP accounts
- Cross-account access uses IAM roles with external IDs
- API endpoints use Lambda Function URLs with CORS
- No data leaves customer AWS environments

---

## 📚 Documentation

- **[Infrastructure Guide](qrie-infra/README.md)**: CDK stacks, Lambda functions, DynamoDB setup
- **[UI Guide](qrie-ui/README.md)**: Next.js application, API integration, deployment
- **[API Documentation](qrie-infra/qrie_apis.md)**: API endpoints and schemas
- **[Custom Domain Setup](tools/deploy/CUSTOM-DOMAIN.md)**: SSL certificates and DNS
- **[Changelogs](changelog/)**: Feature implementation details

---

## 📈 Roadmap

- ✅ MVP: Real-time event processing, inventory generation, policy evaluation, anti-entropy
- 🚧 Advanced scoping and risk scoring
- 📋 Additional compliance frameworks (HIPAA, CIS, CMMC)
- 🔔 Alerting and ticketing integrations
- 💰 Cost monitoring features

---

**Questions?** Contact the qrie team or file an issue in the repository.
