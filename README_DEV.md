# qrie Developer Guide

**Last Updated**: 2025-11-05

This guide covers architecture, code layout, testing, deployment, and operational procedures for qrie developers.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Code Layout](#code-layout)
3. [Local Development & Unit Testing](#local-development--unit-testing)
4. [Setting Up QOP Account](#setting-up-qop-account)
5. [Setting Up Test/Subject Account](#setting-up-testsubject-account)
6. [E2E Testing](#e2e-testing)
7. [Onboarding New Services](#onboarding-new-services)
8. [Customer Operations](#customer-operations)

---

## Architecture

### **System Overview**

qrie is a Cloud Security Posture Management (CSPM) solution that provides:
- **Real-time drift detection** via CloudTrail events
- **Scheduled compliance scans** (weekly inventory, daily policy evaluation)
- **Multi-account monitoring** from a centralized QOP (Qrie On-Premises) account
- **Policy-based security findings** with remediation guidance

### **Key Components**

```
┌─────────────────────────────────────────────────────────────┐
│                     Customer AWS Accounts                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │  Account A │  │  Account B │  │  Account C │           │
│  │            │  │            │  │            │           │
│  │ CloudTrail │  │ CloudTrail │  │ CloudTrail │           │
│  │     ↓      │  │     ↓      │  │     ↓      │           │
│  │ EventBridge│  │ EventBridge│  │ EventBridge│           │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘           │
│        │                │                │                   │
│        └────────────────┴────────────────┘                   │
│                         │                                     │
└─────────────────────────┼─────────────────────────────────────┘
                          │ (Cross-account EventBridge)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    QOP Account (us-east-1)                   │
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │ EventBridge  │────────→│  SQS Queue   │                 │
│  │    Rules     │         │              │                 │
│  └──────────────┘         └──────┬───────┘                 │
│                                   │                          │
│                                   ↓                          │
│  ┌──────────────────────────────────────────────┐          │
│  │         Lambda Functions                      │          │
│  │  ┌────────────────┐  ┌────────────────┐     │          │
│  │  │ Event Processor│  │ Inventory Gen  │     │          │
│  │  │ (Real-time)    │  │ (Scheduled)    │     │          │
│  │  └────────┬───────┘  └────────┬───────┘     │          │
│  │           │                    │              │          │
│  │           └────────┬───────────┘              │          │
│  │                    ↓                          │          │
│  │          ┌────────────────┐                  │          │
│  │          │ Policy Scanner │                  │          │
│  │          │  (Evaluates)   │                  │          │
│  │          └────────┬───────┘                  │          │
│  └───────────────────┼──────────────────────────┘          │
│                      │                                       │
│                      ↓                                       │
│  ┌──────────────────────────────────────────────┐          │
│  │            DynamoDB Tables                    │          │
│  │  • qrie_resources  (inventory)               │          │
│  │  • qrie_findings   (security issues)         │          │
│  │  • qrie_policies   (active policies)         │          │
│  │  • qrie_accounts   (monitored accounts)      │          │
│  │  • qrie_summary    (cached metrics)          │          │
│  └──────────────────────────────────────────────┘          │
│                      ↑                                       │
│                      │                                       │
│  ┌──────────────────┴───────────────────────────┐          │
│  │         API Lambda (Lambda URL)              │          │
│  │  • GET /resources, /findings, /policies      │          │
│  │  • POST /policies/launch                     │          │
│  │  • PUT /policies/update                      │          │
│  └──────────────────┬───────────────────────────┘          │
│                     │                                        │
└─────────────────────┼────────────────────────────────────────┘
                      │ (HTTPS)
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                  UI (CloudFront + S3)                        │
│  • Dashboard  • Findings  • Inventory  • Management  • Docs │
└─────────────────────────────────────────────────────────────┘
```

### **Data Flow**

**Real-Time Event Processing**:
1. Resource change in customer account → CloudTrail event
2. EventBridge forwards to QOP account SQS queue
3. Event Processor Lambda triggered
4. Extract ARN, describe resource, compare with inventory
5. If changed: update inventory, evaluate active policies
6. Create/resolve findings based on policy evaluation

**Scheduled Scans**:
1. **Weekly Inventory** (Saturday 00:00 UTC): Full resource scan across all accounts
2. **Daily Policy Scan** (04:00 UTC): Re-evaluate all resources against active policies
3. Both update drift metrics in summary table

**API & UI**:
1. UI makes API calls to Lambda URL
2. Lambda queries DynamoDB tables
3. Returns JSON responses
4. UI renders data with React/Next.js

---

## Code Layout

### **Mono-Repo Structure**

```
qrie/
├── qop.py                          # Main orchestrator CLI
├── README.md                       # User-facing documentation
├── README_DEV.md                   # This file (developer guide)
│
├── qrie-infra/                     # Backend & infrastructure
│   ├── app.py                      # CDK app entry point
│   ├── stacks/
│   │   ├── core_stack.py           # Lambda, DynamoDB, EventBridge
│   │   └── web_stack.py            # CloudFront, S3, UI hosting
│   │
│   ├── lambda/                     # Lambda function code
│   │   ├── common_utils.py         # Shared utilities (ARN parsing, tables)
│   │   ├── policy_definition.py   # Policy data models
│   │   │
│   │   ├── common/                 # Shared modules
│   │   │   └── logger.py           # Structured logging
│   │   │
│   │   ├── services/               # Service-specific support
│   │   │   ├── __init__.py         # Service registry
│   │   │   ├── s3_support.py       # S3 ARN extraction, describe, list
│   │   │   ├── ec2_support.py      # EC2 support (TODO)
│   │   │   └── iam_support.py      # IAM support (TODO)
│   │   │
│   │   ├── api/                    # API handlers
│   │   │   ├── api_handler.py      # Main router
│   │   │   ├── resources_api.py    # Inventory endpoints
│   │   │   ├── findings_api.py     # Findings endpoints
│   │   │   ├── policies_api.py     # Policy management
│   │   │   └── dashboard_api.py    # Summary/dashboard
│   │   │
│   │   ├── data_access/            # Data access layer
│   │   │   ├── inventory_manager.py
│   │   │   ├── findings_manager.py
│   │   │   ├── policy_manager.py
│   │   │   └── dashboard_manager.py
│   │   │
│   │   ├── event_processor/        # Real-time event processing
│   │   │   └── event_handler.py
│   │   │
│   │   ├── inventory_generator/    # Scheduled inventory scans
│   │   │   ├── inventory_handler.py
│   │   │   ├── s3_inventory.py     # Legacy (being deprecated)
│   │   │   ├── ec2_inventory.py    # Legacy (being deprecated)
│   │   │   └── iam_inventory.py    # Legacy (being deprecated)
│   │   │
│   │   ├── scan_processor/         # Policy evaluation
│   │   │   └── scan_handler.py
│   │   │
│   │   └── policies/               # Policy evaluators
│   │       ├── s3_bucket_public.py
│   │       ├── iam_access_key_rotation.py
│   │       └── ...
│   │
│   ├── tests/
│   │   ├── unit/                   # Unit tests
│   │   └── e2e/                    # End-to-end tests
│   │
│   └── README.md                   # Infrastructure-specific docs
│
├── qrie-ui/                        # Frontend application
│   ├── app/                        # Next.js app router
│   │   ├── page.tsx                # Dashboard
│   │   ├── findings/
│   │   ├── inventory/
│   │   ├── management/
│   │   └── docs/                   # Documentation pages
│   │
│   ├── components/                 # React components
│   │   ├── ui/                     # shadcn/ui components
│   │   └── dashboard-layout.tsx
│   │
│   ├── lib/
│   │   ├── api.ts                  # API client
│   │   └── types.ts                # TypeScript types
│   │
│   └── README.md                   # UI-specific docs
│
├── tools/                          # Operational tools
│   ├── debug/
│   │   └── monitor-logs.sh         # Log monitoring script
│   ├── deploy/
│   │   └── setup-custom-domain.sh
│   └── data/
│       └── seed_data.py            # Test data generation
│
└── changelog/                      # Change documentation
    └── *.md                        # Feature changelogs
```

### **Key Design Patterns**

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

---

## Local Development & Unit Testing

### **Prerequisites**

- Python 3.12+
- Node.js 18+ (for UI)
- pnpm (for UI package management)
- AWS CLI configured with profiles
- Virtual environment

### **Setup**

```bash
# Clone repository
cd ~/dev/qrie

# Set up Python virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
cd qrie-infra
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Test dependencies

# Install UI dependencies
cd ../qrie-ui
pnpm install
```

### **Running Unit Tests**

```bash
# From qrie root
./qop.py --test-unit

# Or directly with pytest
cd qrie-infra
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_s3_bucket_public_evaluator.py -v

# Run with coverage
pytest tests/unit/ --cov=lambda --cov-report=html
open htmlcov/index.html
```

### **Test Structure**

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

### **Local UI Development**

```bash
cd qrie-ui

# Start dev server (uses .env.local for API URL)
pnpm dev

# Open http://localhost:3000
```

**Note**: Update `.env.local` to point to your deployed API URL or use mock data.

---

## Setting Up QOP Account

The QOP (Qrie On-Premises) account hosts the qrie infrastructure.

### **Prerequisites**

- AWS account dedicated for qrie (recommended: separate from production)
- AWS CLI configured with admin credentials
- Profile name: `qop` (or customize in commands)

### **1. Core Stack Deployment**

Deploy Lambda functions, DynamoDB tables, EventBridge rules, SQS queue:

```bash
cd qrie
source .venv/bin/activate

# Build Lambda packages
./qop.py --build --region us-east-1

# Deploy core infrastructure
./qop.py --deploy-core --region us-east-1 --profile qop
```

**What gets deployed**:
- **Lambda Functions**:
  - `qrie_api_handler` (Lambda URL for API)
  - `qrie_event_processor` (processes CloudTrail events)
  - `qrie_inventory_generator` (scheduled inventory scans)
  - `qrie_policy_scanner` (evaluates policies)
- **DynamoDB Tables**:
  - `qrie_resources` (inventory)
  - `qrie_findings` (security findings)
  - `qrie_policies` (active policies)
  - `qrie_accounts` (monitored accounts)
  - `qrie_summary` (cached metrics)
- **EventBridge Rules**:
  - Weekly inventory scan (Saturday 00:00 UTC)
  - Daily policy scan (04:00 UTC)
- **SQS Queue**: `qrie-events-queue` (receives CloudTrail events)

**Verify deployment**:
```bash
./qop.py --info --region us-east-1 --profile qop
```

### **2. UI Stack Deployment**

Deploy CloudFront distribution and S3 bucket for UI hosting:

```bash
# Deploy UI infrastructure
./qop.py --deploy-ui --region us-east-1 --profile qop
```

**What gets deployed**:
- **S3 Bucket**: Hosts Next.js static files
- **CloudFront Distribution**: CDN with custom domain support
- **SSL Certificate** (if custom domain configured)

**Access UI**:
- CloudFront URL shown in deployment output
- Example: `https://d1234567890abc.cloudfront.net`

### **3. Custom Domain (Optional)**

```bash
# Set up custom domain (requires DNS access)
./tools/deploy/setup-custom-domain.sh us-east-1.customer.qrie.com us-east-1 qop
```

See `tools/deploy/CUSTOM-DOMAIN.md` for details.

### **4. Initialize Data**

Add initial accounts to monitor:

```bash
# Manually add to qrie_accounts table
aws dynamodb put-item \
  --table-name qrie_accounts \
  --item '{
    "account_id": {"S": "123456789012"},
    "account_name": {"S": "Production"},
    "status": {"S": "active"}
  }' \
  --region us-east-1 \
  --profile qop
```

---

## Setting Up Test/Subject Account

Customer accounts (test or production) need EventBridge rules to forward CloudTrail events to the QOP account.

### **Prerequisites**

- AWS account to be monitored
- AWS CLI configured with admin credentials
- Profile name: `test` or `foxd` (or customize)
- QOP account ID and region

### **1. Deploy EventBridge Rules**

Deploy the CloudFormation template that creates:
- EventBridge rules for S3, EC2, IAM events
- Cross-account EventBridge target to QOP account

```bash
# From customer account
aws cloudformation deploy \
  --template-file tools/onboarding/eventbridge-rules.yaml \
  --stack-name qrie-eventbridge-rules \
  --parameter-overrides \
    QopAccountId=514183524884 \
    QopRegion=us-east-1 \
  --region us-east-1 \
  --profile test
```

**What gets deployed**:
- EventBridge rules matching CloudTrail events:
  - S3: `CreateBucket`, `PutBucket*`, `DeleteBucket`
  - EC2: `RunInstances`, `TerminateInstances`, `ModifyInstanceAttribute`
  - IAM: `CreateUser`, `DeleteUser`, `PutUserPolicy`
- Cross-account event bus target pointing to QOP account

### **2. Create IAM Role for Cross-Account Access**

qrie needs to assume a role in customer accounts to describe resources:

```bash
aws cloudformation deploy \
  --template-file tools/onboarding/iam-role.yaml \
  --stack-name qrie-inventory-role \
  --parameter-overrides \
    QopAccountId=514183524884 \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1 \
  --profile test
```

**What gets created**:
- IAM Role: `QrieInventoryRole`
- Trust policy allowing QOP account to assume role
- Permissions: `ReadOnlyAccess` (AWS managed policy)

### **3. Add Account to qrie_accounts Table**

```bash
aws dynamodb put-item \
  --table-name qrie_accounts \
  --item '{
    "account_id": {"S": "050261919630"},
    "account_name": {"S": "Test Account"},
    "status": {"S": "active"},
    "onboarded_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}
  }' \
  --region us-east-1 \
  --profile qop
```

### **4. Run Initial Inventory Scan**

Generate baseline inventory for the new account:

```bash
./qop.py --scan-account \
  --account-id 050261919630 \
  --region us-east-1 \
  --profile qop
```

**Duration**: 5-15 minutes depending on resource count

**What happens**:
- Scans all supported services (S3, EC2, IAM)
- Stores inventory in `qrie_resources` table
- Evaluates all active policies
- Creates findings for non-compliant resources

---

## E2E Testing

End-to-end tests verify the complete flow from event to finding using **real AWS resources**.

### **Prerequisites**

- QOP account deployed
- Test account configured with EventBridge rules
- Test account added to `qrie_accounts` table

### **Seed Resources - Real AWS Resources**

The `--seed-resources` command creates real AWS resources for comprehensive E2E testing:

```bash
# Create non-compliant resources (generates findings)
./qop.py --seed-resources non-compliant --account-id 050261919630 --region us-east-1 --profile qop

# Wait 2-3 minutes for CloudTrail events to process

# Verify findings in UI or via API
curl "https://your-api-url/findings?account_id=050261919630"

# Make resources compliant (test remediation)
./qop.py --seed-resources remediate --account-id 050261919630 --region us-east-1 --profile qop

# Cleanup resources and purge findings
./qop.py --seed-resources cleanup --account-id 050261919630 --region us-east-1 --profile qop
```

**What it creates:**
- S3 buckets (with/without encryption, versioning, public access)
- IAM users (with/without access keys, MFA)
- IAM password policies (compliant/non-compliant)

**Automatic setup:**
- Registers account in `qrie_accounts` table
- Launches all 11 policies with default scope
- Tags resources with `qrie-test=true`

**See comprehensive guide:** [tools/test/SEED_RESOURCES_GUIDE.md](tools/test/SEED_RESOURCES_GUIDE.md)

### **Automated E2E Tests (pytest)**

```bash
# From qrie root
cd qrie-infra

# Run all E2E tests
pytest tests/e2e/ -v --region us-east-1 --profile qop

# Run specific service tests
pytest tests/e2e/test_s3_e2e.py -v
```

### **E2E Test Flow**

1. **Setup**: Create test resource in customer account
2. **Trigger**: Wait for CloudTrail event → EventBridge → SQS → Lambda
3. **Verify**: Check inventory updated, findings created
4. **Cleanup**: Delete test resource

Example:
```python
def test_s3_public_bucket_e2e(test_account_id):
    """E2E test for S3 public bucket detection"""
    # Create public bucket
    bucket_name = f"qrie-test-{int(time.time())}"
    s3_client.create_bucket(Bucket=bucket_name)
    
    # Wait for event processing (up to 60 seconds)
    time.sleep(60)
    
    # Verify inventory updated
    inventory = get_inventory_for_bucket(bucket_name)
    assert inventory is not None
    
    # Verify finding created
    findings = get_findings_for_bucket(bucket_name)
    assert len(findings) > 0
    assert findings[0]['Policy'] == 'S3BucketPublic'
    
    # Cleanup
    s3_client.delete_bucket(Bucket=bucket_name)
```

---

## Onboarding New Services

To add support for a new AWS service (e.g., RDS, Lambda, ECS):

### **1. Add to SUPPORTED_SERVICES**

```python
# lambda/common_utils.py
SUPPORTED_SERVICES = ["s3", "ec2", "iam", "rds"]  # Add 'rds'
```

### **2. Create Service Support Module**

```python
# lambda/services/rds_support.py

def extract_arn_from_event(detail: dict) -> Optional[str]:
    """Extract RDS resource ARN from CloudTrail event"""
    # Check resources array
    resources = detail.get('resources', [])
    if resources:
        return resources[0].get('ARN')
    
    # Construct from requestParameters if needed
    # ...
    return None

def describe_resource(arn: str, account_id: str, rds_client=None) -> dict:
    """Describe RDS instance/cluster configuration"""
    # Assume role, create client, describe resource
    # ...
    return config

def list_resources(account_id: str, rds_client=None) -> List[Dict]:
    """List all RDS instances/clusters in account"""
    # Assume role, list resources, describe each
    # ...
    return resources
```

### **3. Add EventBridge Rules**

Update `tools/onboarding/eventbridge-rules.yaml`:
```yaml
RDSEventRule:
  Type: AWS::Events::Rule
  Properties:
    EventPattern:
      source:
        - aws.rds
      detail-type:
        - AWS API Call via CloudTrail
      detail:
        eventName:
          - CreateDBInstance
          - ModifyDBInstance
          - DeleteDBInstance
    Targets:
      - Arn: !Sub 'arn:aws:events:${QopRegion}:${QopAccountId}:event-bus/default'
        RoleArn: !GetAtt EventBridgeRole.Arn
```

### **4. Create Policy Evaluators**

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

### **5. Add Unit Tests**

```python
# tests/unit/test_rds_public_access_evaluator.py
def test_public_rds_detected(evaluator, mocker):
    mocker.patch('data_access.findings_manager.FindingsManager')
    
    config = {'PubliclyAccessible': True}
    result = evaluator.evaluate('arn:aws:rds:...', config, int(time.time() * 1000))
    
    assert result['compliant'] is False
```

### **6. Add E2E Tests**

```python
# tests/e2e/test_rds_e2e.py
def test_rds_public_instance_e2e(test_account_id):
    # Create public RDS instance
    # Wait for event processing
    # Verify inventory and findings
    # Cleanup
    pass
```

### **7. Update Documentation**

- Add service to `README.md` supported services list
- Document service-specific notes in this file
- Update `qrie-ui/app/docs/` if needed

---

## Customer Operations

### **Onboarding New Customer**

**1. QOP Setup** (one-time per region):
```bash
./qop.py --deploy-core --region us-east-1 --profile qop
./qop.py --deploy-ui --region us-east-1 --profile qop
```

**2. Customer Account Setup** (per account):
```bash
# In customer account
aws cloudformation deploy \
  --template-file tools/onboarding/eventbridge-rules.yaml \
  --stack-name qrie-eventbridge-rules \
  --parameter-overrides QopAccountId=<QOP_ACCOUNT_ID> QopRegion=us-east-1 \
  --region us-east-1 \
  --profile customer

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

**5. Launch Policies**:
- Navigate to UI → Management page
- Launch desired policies (start with high-severity: S3BucketPublic, IAMAccessKeyRotation)

### **Monitoring Operations**

**View Logs**:
```bash
# Monitor event processor
./tools/debug/monitor-logs.sh event us-east-1 qop

# Monitor API
./tools/debug/monitor-logs.sh api us-east-1 qop

# Monitor inventory generator
./tools/debug/monitor-logs.sh inventory us-east-1 qop
```

**Check Deployment Info**:
```bash
./qop.py --info --region us-east-1 --profile qop
```

**Manual Scans**:
```bash
# Full inventory scan
./qop.py --generate-inventory --region us-east-1 --profile qop

# Specific account scan
./qop.py --scan-account --account-id 123456789012 --region us-east-1 --profile qop
```

---

## Troubleshooting

### **Events Not Processing**

1. Check SQS queue has messages:
```bash
aws sqs get-queue-attributes \
  --queue-url $(aws sqs list-queues --region us-east-1 --profile qop | jq -r '.QueueUrls[0]') \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1 \
  --profile qop
```

2. Check Lambda logs for errors:
```bash
./tools/debug/monitor-logs.sh event us-east-1 qop
```

3. Verify EventBridge rules in customer account:
```bash
aws events list-rules --region us-east-1 --profile customer
```

### **Inventory Not Updating**

1. Check scheduled rules are enabled:
```bash
aws events list-rules --region us-east-1 --profile qop
```

2. Check Lambda execution:
```bash
./tools/debug/monitor-logs.sh inventory us-east-1 qop
```

3. Verify IAM role trust relationship in customer account

### **UI Not Loading**

1. Check CloudFront distribution status
2. Verify S3 bucket has files
3. Check API URL in browser console (Network tab)
4. Verify CORS settings on Lambda URL

---

## Additional Resources

- **Main README**: `README.md` - User-facing documentation
- **Infrastructure README**: `qrie-infra/README.md` - CDK and Lambda details
- **UI README**: `qrie-ui/README.md` - Frontend development
- **API Documentation**: `qrie-infra/qrie_apis.md` - API endpoints
- **Changelogs**: `changelog/*.md` - Feature implementation details
- **Custom Domain Setup**: `tools/deploy/CUSTOM-DOMAIN.md`

---

**Questions?** Contact the qrie team or file an issue in the repository.
