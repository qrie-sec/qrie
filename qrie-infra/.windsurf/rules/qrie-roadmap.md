---
trigger: manual
---

# qrie - MVP Roadmap

---
### MVP Checklist
- A cold customer can self-wire events in <30 min; you can onboard a second QOP tenant in <15 min.
- One dedicated QOP account live with: inventory scans, event-driven updates, 10 findings checks, table UI + export, basic alerts.

**MVP Exit Criteria:** At least **3 demos booked** and **1 pilot** starting. {keep building}

**PMF Criteria:** You’re comfortable running 2 paying pilots for 60 days [schedule new customers’ onboarding for after 2 months, like Q2 2026]
---

### Weekly Planning
Aug 11-17: **Design ✅**
Aug 18-24: Bootstrapping 
Aug 25-31: Lambda, Inventory and Findings Schema, Policies
Sep 01-07: UI
Sep 08-14: UI
Sep 15-21: Vacation SFO

### Tasks Planning

---
QOP (UI, Backend, x-account) infra

- [x]  **CDK** Infra ****for **QOP backend** (DDB table, basic IAM structure, S3 bucket for logs) [Done: 8/19]
- [x]  **CDK** Infra for **QOP UI** (S3, CloudFront) [Done: 8/21]
- [x]  **Cross account** bootstrapping script
    - [x]  Tighten queue policies etc.
    - [x]  Test the events flowing in
    - [x]  Test that **event flow in and** trigger lambda

---

- Lambda Engine
    - [ ]  Design the inventory schema (see what Wiz does, evaluate GraphDB), implement (S3, EC2, IAM) and test.
    - [ ]  Design the policy language, findings table, implement and test.
    - [ ]  Policy Evaluation Lambda

ETA: 9/12

---

- QOP - UI / Dashboards
    - [ ]  Display inventory
    - [ ]  Display Findings Table local data
    - [ ]  DDB Connection
    - [ ]  Search, Filter, and Export Findings
    
ETA: 9/15
---
- Vacation 9/16-23
---
- Testing 
    - [ ]  Test the deployment in another account.
    - [ ]  Do full dry run: bootstrap → scan → view findings in UI as “customer.”
    - [ ]  QA - Bug fixes and backlog
    - [ ]  File a provisional patent

ETA: 9/30

---

- Update Landing Page, Documentation
    - “Dedicated Qrie Instance” messaging.
    - Screenshots of UI with seeded findings.
    - Early adopter interest form.
- Investor and Customer Engagement
    - [ ]  Post teaser on X, LinkedIn tag security folks.
    - [ ]  Prospects
    - [ ]  Start booking first customer demos for next week.
    - [ ]  Contracts and pricing

ETA: 10/15

---

- Implement more policies, remediation steps - HIPAA vertical
    - [ ]  S3 public name heuristic,
    - [ ]  EC2 without tags,
    - [ ]  IAM users without MFA
- [ ]  Request Caching (configurable window)
- Harden Internal Runbooks
    - Runbooks Onboarding
        - Tighten QOP SQS policy with `aws:SourceArn` to that rule
        - ExternalId on viewer role trust; DDB tables set to `RETAIN`.
    - Offboarding Runbook
        - Disable customer EventBridge rule
        - Remove their principal from `QrieCustomerViewer` trust (optionally require `ExternalId`).

---

# Post MVP Roadmap

| **Policy Expansion & Early Cost Scoring** | • Expand to 80 managed policies (+60 new) covering CIS, PCI, NIST, HIPAA, CMMC.
• Add basic cost score to findings (unused resources, underutilized compute) to compete with Trusted Advisor. |
| --- | --- |
| **AI Risk Scoring** | • Basic AI Risk Scoring: severity ranking, moving from ‘Inventory’ to ‘Insights’
 |
| **Automated Multi-Account Onboarding** | • Script automating onboarding multi-account customer environments |
| **HIPAA Vertical Compliance Pack** | • Deliver all checks with remediation steps
• Generate Compliance Reports |
| **CIS / NIST Compliance Pack**  | • Deliver all checks with remediation steps
• Generate Compliance Reports |
| **CMMC Compliance Pack** | • Deliver all checks with remediation steps
• Generate Compliance Reports |
| **PCI Compliance Pack** | • Deliver all checks with remediation steps
• Generate Compliance Reports |
| **Account Groups / Tagging** | • Tag resources/accounts by service/environment.
• Apply policies selectively based on tags. |
| **Customer-Defined Policies** | • Build-your-own policies in UI (Python/YAML DSL).  
• AI Assisted policy development and remediation-steps recommendations
• Policy validation sandbox
• Package managed policies as **signed, encrypted artifacts** (e.g., zip in S3 with KMS). Decrypt at runtime with a **license-provisioned data key**; verify **signature**; keep keys local in the customer account. |
| **UX Improvements** | • Enhanced dashboard with filters, trends, and saved searches. |
| **Ticketing** | • Integrations with Jira, ServiceNow, GitHub Issues.
• Assign findings in UI with audit trail. |
| **AI driven Remediation** | *<brainstorming pending>* |
| **Alerting** | • Basic alert config in SSM (sev thresholds, channel endpoints).
• Slack (Webhook) + email (SES) for HIGH findings. |
| QOP Data Collection | • Cost guardrails (CloudWatch dashboard; daily cost notification).
• Events, Scans, Findings Aggregate based billings. |
