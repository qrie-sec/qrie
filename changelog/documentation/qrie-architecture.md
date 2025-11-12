# Qrie Architecture & Repository Structure

## Repository Structure (Mono-repo)

```
qrie/                          # Root mono-repository
├── README.md                  # Main project documentation
├── qop.py                     # Main orchestrator script
├── .gitignore                 # Global gitignore
├── ARCHITECTURE.md            # This file
├── CHANGELOG.md               # Version history
│
├── tools/                     # Shared tooling & scripts
│   ├── deploy/                # Deployment scripts
│   ├── data/                  # Data seeding & migration
│   └── test/                  # Cross-component testing
│
├── docs/                      # Documentation
│   ├── deployment/            # Deployment guides
│   ├── api/                   # API documentation
│   └── development/           # Development setup
│
├── qrie-infra/               # Backend infrastructure & services
│   ├── lambda/               # AWS Lambda functions
│   │   ├── api/              # API handlers
│   │   ├── data_access/      # Data access layer
│   │   ├── event_processor/  # Event processing
│   │   └── common/           # Shared utilities
│   ├── stacks/               # CDK infrastructure definitions
│   ├── tests/                # Backend tests
│   ├── requirements.txt      # Python dependencies
│   └── cdk.json              # CDK configuration
│
├── qrie-ui/                  # Frontend web application
│   ├── app/                  # Next.js app directory
│   ├── components/           # Reusable UI components
│   ├── lib/                  # Frontend utilities
│   ├── public/               # Static assets
│   ├── package.json          # Node.js dependencies
│   └── next.config.mjs       # Next.js configuration
│
└── tools/                    # Development & maintenance scripts
    ├── dev_setup.sh          # Initial development setup
    ├── deploy/               # Deployment scripts & custom domain setup
    ├── debug/                # Debugging and monitoring tools
    ├── data/                 # Data seeding & migration
    └── test/                 # Cross-component testing
```

## Why Mono-repo?

### ✅ Advantages for Qrie:

1. **Unified Development Experience**
   - Single `git clone` gets everything
   - `qop.py` orchestrates all components
   - Shared configuration and tooling

2. **Atomic Cross-Component Changes**
   - API changes + UI updates in single commit
   - Infrastructure changes + code updates together
   - Consistent versioning across all components

3. **Simplified CI/CD**
   - Single pipeline builds/tests/deploys everything
   - No complex cross-repo dependency management
   - Easier to ensure compatibility

4. **Shared Tooling & Standards**
   - Common linting, formatting, testing tools
   - Shared documentation and processes
   - Unified dependency management

### 🔧 Best Practices:

1. **Clear Module Boundaries**
   - Each subdirectory is a distinct module
   - Well-defined interfaces between components
   - Independent build/test capabilities

2. **Selective CI/CD**
   - Detect changed components
   - Only rebuild/redeploy what changed
   - Use path-based triggers in CI

3. **Component Independence**
   - Each component can be developed/tested independently
   - Clear dependency direction (UI → API → Infrastructure)
   - Avoid circular dependencies

## Development Workflow

### Initial Setup
```bash
git clone https://github.com/company/qrie.git
cd qrie
./tools/dev_setup.sh  # Sets up all components
```

### Component Development
```bash
# Work on infrastructure
cd qrie-infra
source .venv/bin/activate
# ... make changes ...

# Work on UI
cd qrie-ui
npm install
npm run dev
# ... make changes ...

# Test everything together
cd ..
./qop.py --full-deploy --region us-east-1 --profile dev
```

### Release Process
```bash
# Tag release
git tag v1.2.3
git push origin v1.2.3

# Deploy to production
./qop.py --full-deploy --region us-east-1 --profile prod
```

## Alternative: Multi-repo Consideration

If the team grows significantly or components need independent release cycles, consider splitting into:

- `qrie-infrastructure` - CDK stacks and Lambda code
- `qrie-ui` - Frontend application
- `qrie-tools` - Shared tooling and deployment scripts

However, this is **not recommended** at current scale.
