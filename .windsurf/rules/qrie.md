---
trigger: always_on
---

---

qrie is a CSPM that allows customers to deploy a non-SaaS on-prem solution, where we spin up and provide access to a dedicated AWS account (qrie-on-prem or QOP account) that stores security and compliance policies, hosts the real-time policy enforcement engine (currently a lambda, in future on ECS-Fargate), and stores an inventory of all resources (qrie_resources) and security findings in DynamoDB (qrie_findings). Customers get a dedicated UI hosted on the QOP account to monitor their findings. This stack (including the UI) is isolated per-AWS region.

For onboarding, customers follow the steps outlined in https://www.qrie.io/onboarding. Basically, qrie engineers set up a dedicated AWS account (a.k.a qrie On Prem or QOP account) with policies, enforcement engine, findings storage and UI. Customers have to execute an onboarding script on their AWS accounts to set up EventBridge rules that forward CloudTrail management events that modify resource configurations into their dedicated QOP account.

## API Architecture

The qrie UI is served by a single Lambda URL handler (api_handler.py) that routes requests to domain-specific modules:
- **Resources**: resources_api.py + inventory_manager.py - handles inventory and account data
- **Findings**: findings_api.py + findings_manager.py - handles security findings
- **Policies**: policies_api.py + policy_manager.py - handles policy management (launch/update/delete)
- **Dashboard**: dashboard_api.py + dashboard_manager.py - aggregates summary data with 1-hour caching

Key endpoints:
- `/resources`, `/accounts`, `/services` - inventory data
- `/findings` - security findings with filtering
- `/policies` - unified policy query (status=active|available|all)
- `POST /policies` - launch new policy
- `PUT /policies/{policy_id}` - update policy metadata
- `DELETE /policies/{policy_id}` - delete policy and purge findings
- `/summary/dashboard`, `/summary/resources`, `/summary/findings` - aggregated summaries

## For MVP, we are shipping:
- Automated bootstrapping and inventory scans
- Basic policies across compliance verticals (IAM, S3, EC2)
- Policy management (launch/update/delete with automatic scanning)
- Dashboard with 1-hour cached summaries
- Clean UI for findings exploration and remediation

## Post MVP, we will focus on:
- Completing compliance verticals - HIPAA, CIS/NIST, CMMC, PCI
- Selective application of policies based on Organizations, Applications and tags
- Cost monitoring
- Risk Scoring with historical trends
- Alerting and Ticketing
- Customer Defined Policies

## Data Abstractions

- **Policy Definition** (code-based): Static definitions with policy_id, description, service, category, severity, remediation, evaluation_module
- **Launched Policy** (DynamoDB): Active policies with PolicyId, Status (active/suspended), Scope (targeting config), optional severity/remediation overrides, CreatedAt, UpdatedAt
- **Findings** (DynamoDB): Schema - 'ARN', 'Policy', 'AccountService (e.g. 123412341234_ec2)', 'Severity (0-100)', 'State (ACTIVE, RESOLVED)', 'FirstSeen', 'LastEvaluated', 'Evidence (JSON snippet of the offending configuration)'
- **Inventory** (DynamoDB): Schema - "AccountService", "ARN", "LastSeenAt", "Configuration"

## Data Storage

- **qrie_policies** (DynamoDB): Launched policy configurations with scope and status
- **qrie_findings** (DynamoDB): Security findings with ARN+Policy composite key, AccountService GSI
- **qrie_resources** (DynamoDB): Resource inventory with AccountService+ARN composite key
- **qrie_summary** (DynamoDB): Cached dashboard summaries with 1-hour TTL and distributed locking

## Implementation Status

**✅ MVP Implemented:**
- Real-time event processing from CloudTrail for immediate drift detection
- Inventory generation with full configuration capture across all services
- Policy evaluation scanning off existing inventory (bootstrap and scheduled)
- Anti-entropy via scheduled scans (weekly inventory, daily policy) on top of event-driven system
- Resource inventory and findings APIs with pagination and filtering
- Policy management (launch/update/delete with automatic scanning)
- Dashboard summaries with 1-hour caching and lazy refresh
- Clean UI for findings exploration with remediation steps

**🚧 Post-MVP Planned:**
- Advanced risk scoring with historical trends
- Time-based dashboard metrics with longer retention
- Selective policy application by tags/OUs
- Cost monitoring integration
- Alerting and ticketing systems
- Customer-defined policies