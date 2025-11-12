# Qrie Tools

Organized scripts for build, test, deploy, and data operations.

## 📁 Directory Structure

```
tools/
├── dev_setup.sh    # Development environment setup
├── test/           # Unit and integration testing
├── deploy/         # Deployment automation & custom domain setup
├── debug/          # Debugging and monitoring tools
└── data/           # Data seeding and management
```

## 🚀 Main Orchestrator

Use the main `qop.py` script for all operations:

```bash
# Get help
./qop.py -h

# Complete deployment pipeline
./qop.py --full-deploy --region us-east-1 --profile your-profile

# Individual operations
./qop.py --build --region us-east-1
./qop.py --test-unit
./qop.py --deploy-core --region us-east-1 --profile your-profile
./qop.py --deploy-ui --region us-east-1 --profile your-profile
./qop.py --info --region us-east-1 --profile your-profile
./qop.py --test-api --region us-east-1 --profile your-profile
```

## 🧪 Test Scripts

### `test/run_tests.py`
- **Purpose**: Run unit tests with coverage reporting
- **Usage**: Called by `./qop.py --test-unit`
- **Features**: 
  - Coverage reporting (HTML + terminal)
  - Fail under 80% coverage
  - Tests lambda/data_access layer

### `test/test_apis.py`
- **Purpose**: Comprehensive API endpoint testing
- **Usage**: Called by `./qop.py --test-api`
- **Features**:
  - Tests all API endpoints
  - Validates response formats
  - Error handling verification

## 📊 Data Scripts

### `data/seed_data.py`
- **Purpose**: Populate test data for development
- **Usage**: Called by `./qop.py --test-integ`
- **Features**:
  - Sample accounts, resources, findings
  - Clear existing data option
  - Configurable data volumes

### `data/populate_accounts.py`
- **Purpose**: Manage customer accounts in DynamoDB
- **Usage**: Direct script execution
- **Features**:
  - Add/remove accounts
  - CSV import/export
  - Account validation

## 🚀 Deploy Scripts

### `dev_setup.sh`
- **Purpose**: Automated development environment setup
- **Usage**: `./tools/dev_setup.sh`
- **Features**:
  - Python virtual environment setup
  - Node.js dependency installation
  - CDK CLI installation
  - Prerequisites validation

### `deploy/setup-custom-domain.sh`
- **Purpose**: Setup custom domains for UI
- **Usage**: `./tools/deploy/setup-custom-domain.sh <domain> <region> <profile>`
- **Features**:
  - SSL certificate provisioning
  - CloudFront configuration
  - DNS setup instructions

### `deploy/deploy-to-customer.sh`
- **Purpose**: Deploy to customer QOP accounts
- **Usage**: Manual customer deployments
- **Features**:
  - Cross-account role assumption
  - Complete infrastructure + UI deployment
  - Output capture and display

### `deploy/CUSTOM-DOMAIN.md`
- **Purpose**: Comprehensive custom domain setup guide
- **Content**: Step-by-step instructions, troubleshooting, examples

## 🔧 Script Principles

### No Defaults
- All scripts require explicit parameters
- No assumed regions, profiles, or environments
- Fail fast if required parameters missing

### Clear Communication
- Announce what will be done before execution
- Display region, profile, stack names
- Show assumed prerequisites
- Wait for confirmation (unless `--skip-confirm`)

### Error Handling
- Proper exit codes
- Clear error messages
- Cleanup on failure where applicable

## 📋 Common Workflows

### Development Setup
```bash
# Initial setup
./tools/dev_setup.sh

# Build and test
./qop.py --build --region us-east-1
./qop.py --test-unit
./qop.py --deploy-core --region us-east-1 --profile dev
```

### Production Deployment
```bash
./qop.py --full-deploy --region us-east-1 --profile prod
```

### Testing Only
```bash
./qop.py --test-unit
./qop.py --test-api --region us-east-1 --profile dev
```

### Get Deployment Info
```bash
./qop.py --info --region us-east-1 --profile dev
```

### Customer Deployment
```bash
./tools/deploy/deploy-to-customer.sh 123456789012 us-east-1
```

## 🔍 Dry Run Support

Most operations support `--dry-run` to see what would be executed:

```bash
./qop.py --deploy-core --region us-east-1 --profile prod --dry-run
```

## ⚡ Skip Confirmations

For CI/CD environments:

```bash
./qop.py --full-deploy --region us-east-1 --profile prod --skip-confirm
```
