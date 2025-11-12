---
trigger: manual
---

- Policy Strategy - Open Policy Risks
    
    Opening up policy logic without thinking through your moat is risky. If you just hand over the “brains” in editable YAML or Python, you risk making Qrie a pretty front-end for something people could run with an open-source engine.
    
    ---
    
    ## 1️⃣ Why this is risky
    
    Policies-as-code isn’t novel; once you make them portable and editable, customers can lift them into OPA, Prowler, ScoutSuite, Cloud Custodian, Steampipe, etc. If the perception is “the core is just a rules engine, the rest is UI,” some security teams will self-host a free tool and abandon your subscription. Also, arbitrary customer code in policy logic increases testing and sandboxing overhead.
    
    ---
    
    ## 2️⃣ Current Open-Source Alternatives (AWS Compliance & Inventory)
    
    These already give people scanning, policies, and reporting for free:
    
    | Tool | Strengths | Weaknesses vs Qrie |
    | --- | --- | --- |
    | **Prowler** | CIS benchmark coverage, multi-cloud, active dev community | CLI only, not real-time, no SaaS/on-prem hybrid |
    | **ScoutSuite** | Multi-cloud, JSON reports, extensible | Batch mode, slow updates, no UI beyond static HTML |
    | **Cloud Custodian** | Extremely flexible policy-as-code, wide AWS service coverage | Steep learning curve, not plug-and-play, no real-time UI |
    | **Steampipe + AWS plugin** | SQL-based queries across AWS resources | Requires local infra, not event-driven |
    | **DefectDojo** | Aggregates findings from other scanners | Needs integration, not an inventory engine |
        
    Once you give editable policies, the *technical function* overlaps with these tools — so your **distribution, UX, speed, and integrations** must carry the differentiation. You can keep differentiation by thinking of “editable policies” as a feature *inside a platform*, not the platform itself.

    - Use a **DSL** that’s easier than raw YAML/Python, with syntax sugar and Qrie-specific functions.
    - “Qrie-flavored” policies depend on Qrie’s *data model* (normalized AWS metadata, historical state diffs) so they’re not easily portable to vanilla OPA/Prowler.
    
    ### **a) Keep the high-value pieces closed**
    
    - **Detection engine** – Real-time EventBridge + findings DB should be proprietary.
    - **Risk scoring AI** – Even if customers can edit rules, your scoring logic and prioritization algorithm remain your secret sauce.
    
    - **Integrations** – Alerts, ticketing, dashboards stay tied to Qrie’s backend.
    
    ### **c) Sell time savings, not raw logic**
    - Weekly content updates, “latest AWS service checks” added automatically.
    - Pre-mapped compliance frameworks.
    - One-click remediation playbooks.
    
    ---
    
    ## 4️⃣ When to open it up
    1. **Internal sandbox first** – Let customers request changes you implement.
    2. **Guided editing** – Expose parameters (“require MFA = true/false”) before full code access.
    3. **Controlled open** – Full custom policies only for enterprise tier, with support contracts.
    
    ---
    
    ### **Qrie Competitive Matrix**
    
    Here’s a **competitive matrix** showing where Qrie can stand out — even if you open up policy logic in Release 7 — versus both commercial CNAPPs and the major open-source tools.
    
    | Capability / Tool | **Qrie (Roadmap)** | Wiz / Orca (Commercial) | Prowler / ScoutSuite / Custodian / Steampipe (Open Source) |
    | --- | --- | --- | --- |
    | **Deployment Model** | On-prem by default, SaaS trial option, hybrid possible | SaaS only | Self-host CLI / scripts |
    | **Initial Setup** | Automated bootstrapping via CloudFormation/CDK | Agentless but requires granting SaaS external access | Manual IAM + CLI install |
    | **AWS Coverage** | Full inventory Stage 1, 20+ policies Stage 3, 80 policies by Release 4 | Broad multi-cloud coverage | AWS-only (some multi-cloud), but uneven service depth |
    | **Real-Time Detection** | EventBridge-driven detection | Yes | Mostly batch scans (no near-real-time) |
    | **Policy Management** | Curated, updated, vertical-specific packs (HIPAA, PCI, FedRAMP) that customers can tweak but can’t fully copy without losing ongoing updates. Additionally, editable in Qrie-DSL with validation sandbox; vertical packs (HIPAA, CMMC) | Prebuilt policies + some customization | Fully editable YAML/Python; no curated content updates |
    | **AI Features** | Early risk scoring Stage 3, AI remediation Release 10 | Risk prioritization + posture recommendations | None (manual rule authoring) |
    | **Cost Visibility** | Basic cost score by Release 4 | Deep cost optimization (esp. Wiz) | Minimal / none |
    | **Integrations** | (Future) Slack/email alerts, ticketing | Rich integrations | Manual / user-built |
    | **Compliance Packs** | Managed, updated, vertical-specific (cannot be fully replicated without subscription) | CIS, PCI, HIPAA, etc. | CIS, custom scripts — community maintained |
    | **Data Control** | Customer-owned DDB, on-prem execution | SaaS-hosted findings | Local execution possible, but no managed UI |
    | **UI/UX** | Web app with real-time dashboard, export, search | Polished enterprise UI | HTML reports / CLI output |
    

    Additionally 
    - qrie will scale to 10000s of accounts.
    - qrie will be much cheaper than Wiz.
    - qrie has 'no multi-tenancy'. Your Qrie runs in its own AWS account.
    - qrie has 'contractual data retention'. Agree to purge all findings within X days if contract ends.



    ### **Key Differentiators vs Open Source**
    
    Even if policies are editable:
    - **Real-time detection** (EventBridge) — Prowler/Custodian aren’t live.
    - **Curated compliance packs** — updated, vertical-specific content keeps subscription value.
    - **Integrated risk scoring AI** — OSS doesn’t bundle analytics or prioritization.
    - **On-prem packaging** — deployable in regulated environments with license validation.
    - **Automated onboarding** — OSS needs more manual AWS setup.
    
    ---
    
    ### **Moat Levers Map**
    
    Here’s the **Moat Levers Map** for Qrie, broken into **what to open** and **what to keep closed** so Release 7 policy editing doesn’t turn Qrie into “Prowler with a nice UI.”
    
    ## **1️⃣ What to Open (to drive adoption & flexibility)**
    
    These are safe to open because they **depend on Qrie’s proprietary engine/data model** and don’t give away the core value.
    
    | Component | Why Safe to Open | Notes |
    | --- | --- | --- |
    | **Policy DSL syntax & examples** | Lowers learning curve, drives engagement | Make DSL depend on Qrie’s **normalized AWS resource schema**, so it’s not portable to generic OSS without a translation layer. |
    | **Parameter tuning** | Let customers toggle thresholds (`require_mfa: true`, `max_inactive_days: 90`) | Expose via UI forms first, then DSL later. |
    | **Custom policy creation sandbox** | Keeps experimentation inside Qrie’s runtime | Use **non-exportable** environment for execution. |
    | **Non-sensitive API adapters** | For integrating their own data into checks | E.g., let them call `get_tag(key)` but not raw boto3 directly. |
    
    ## **2️⃣ What to Keep Closed (moat protectors)**
    
    These are where your **real differentiation** lives — keep them proprietary, even for customers.
    
    | Component | Why Closed | Protection Mechanism |
    | --- | --- | --- |
    | **Detection Engine** (EventBridge triggers → Findings DB pipeline) | Real-time architecture is a differentiator vs OSS batch scanners | No source distribution; ship as compiled Lambda package or container image. |
    | **Normalized AWS Resource Model** | Converts AWS API chaos into a stable schema for policies | Keep transformation logic proprietary; policies reference schema, not raw AWS calls. |
    | **Risk Scoring Algorithm (AI)** | AI prioritization is high-value & hard to replicate | Keep model weights closed; expose only ranked results. |
    | **Compliance Packs** (HIPAA, CMMC, PCI, etc.) | Ongoing updates keep subscription sticky | Ship as signed, encrypted content; DSL can *reference* but not copy the logic. |
    | **Remediation Playbooks** | Saves ops time; high enterprise value | Only run via Qrie’s agent; don’t export steps as raw scripts. |
    | **Multi-account orchestration** | Smooth onboarding is a moat | Keep account-discovery logic inside proprietary onboarding flow. |
    
    ---
    
    ## **3️⃣ Guardrails to Prevent OSS Cannibalization**
    
    - **Qrie-DSL coupling** – DSL keywords are *Qrie-specific functions* (e.g., `is_public_s3_bucket()`), so they require Qrie’s backend to resolve.
    - **Policy signing** – All policies (including customer-written ones) are stored signed & encrypted; execution only in licensed environments.
    - **Vertical pack entitlements** – Even if the DSL is open, vertical compliance packs are licensed and updated regularly.
    - **Runtime sandboxing** – Customer policies run in an isolated runtime you control, preventing direct export or reverse engineering.
    
    ---
    
    ## **4️⃣ Visual Mental Model**
    
    Think of Qrie as **“open kitchen, closed recipes.”**
    
    - Customers can cook (write/edit policies).
    - They use your oven (detection engine) and pantry (normalized resource model).
    - But the *house specials* (AI scoring, compliance packs, remediation) are only on your menu.
    
    ---
