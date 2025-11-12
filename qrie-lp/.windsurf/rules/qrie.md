---
trigger: always_on
---

qrie is a CSPM that allows customers to deploy an non-SaaS on-prem solution, where we spin up and provide access to a dedicated AWS account that stores security and compliance policies, hosts the real-time policy enforcement engine, and stores security findings. Customers get a dedicated UI to monitor their findings. This stack (including the UI) is isolated per-AWS region. 

For onboarding, customers follow the steps outlined in https://www.qrie.io/onboarding. Basically, qrie engineers set up a dedicated AWS account (a.k.a qrie On Prem or QOP account) with policies, enforcement engine, findings storage and UI. Customers have to execute an onboarding script on their AWS accounts to set up EventBridge rules that forward Cloudtrail management events that modify resource configurations into their dedicated QOP account.

For MVP, we are shipping automated bootstrapping, inventory scans and basic policies across some important compliance verticals. We are also shipping a basic and clean UI to explore findings and remediation steps.

Post MVP, we will focus on completing compliance verticals - HIPAA, CIS/NIST, CMMC, PCI. We will also roll out -
 * Selective application of policies based on Organizations, Applications and tags
 * Cost monitoring
 * Risk Scoring
 * Alerting and Ticketing
 * Customer Defined Policies