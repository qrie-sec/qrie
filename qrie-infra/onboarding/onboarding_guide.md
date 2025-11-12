# Onboarding to Qrie

# Before you onboard:

1. **Say hi:** You contact Qrie and see a short demo.
2. **Paperwork:** We sign a simple order form.
3. **We deploy QOP:** Qrie deploys your **per-region QOP stacks**, producing the **SQS Queue ARN** for each region + the UI URL(s). (Queue URL/ARN and table names are also surfaced in stack outputs.)
4. **You connect events:** Your engineers “Launch Stack” in any regions you use (or run the CloudShell steps below). This forwards selected EC2/S3/IAM CloudTrail write-events to your QOP SQS.
5. **We verify:** We confirm events are arriving and the UI shows live inventory/findings.
6. **That’s it:** You now have a dedicated Qrie instance per region; offboarding = disable the rules + we revoke the viewer role.

# Step 1

---

## ▶️ **CloudShell Copy/Paste (multi-region)**

This is for folks who prefer CLI and want to **repeat for multiple regions** fast. No coding experience needed. You need to have elevated/admin permissions into these accounts. You can broaden or restrict what gets forwarded to your Qrie On Prem account for policy-evaluation since the forwarded services and event list are exposed as parameters in the script you’ll run (below).

**Before you start:**

- Open the **AWS console** in the account you want to connect.
- In the top search bar, type **“CloudShell”** and open it.
- In the top-right of CloudShell, **set the Region** to one you use (e.g., us-east-2).

**Run these commands:**

```bash
# 1) Download the template
curl -fsSL -o qrie-customer-bootstrap.yaml \
  https://<your-public-template-host>/customer_bootstrap.yaml

# 2) Set your QOP SQS ARN for THIS region
QOP_QUEUE_ARN="arn:aws:sqs:us-east-2:<QOP_ACCOUNT_ID>:<your-qrie-queue>"

# 3) Deploy (creates role + EC2/S3/IAM rules -> your QOP SQS)
aws cloudformation deploy \
  --region us-east-2 \
  --stack-name QrieForwardToQOP \
  --template-file qrie-customer-bootstrap.yaml \
  --parameter-overrides QopQueueArn="$QOP_QUEUE_ARN" RuleNamePrefix="qrie-forward" \
  --capabilities CAPABILITY_NAMED_IAM

```

**Repeat** step 3 for any additional regions you use (change `--region` and set the matching `QOP_QUEUE_ARN`).

**Verify:** still in CloudShell, send a test event:

```bash
aws events put-events --region us-east-2 --entries '[
  {"Source":"qrie.demo","DetailType":"TestEvent","Detail":"{\"hello\":\"world\"}"}
]'

```

We’ll confirm receipt in your QOP queue from our side.

# Step 2

---

## ☑ Verify (customer side)

1. **Confirm stack is CREATE_COMPLETE** in each region.
2. **Send a test event** (run in one of the regions you deployed):

```bash
aws events put-events --region us-east-2 --entries '[
  {"Source":"qrie.demo","DetailType":"TestEvent","Detail":"{\"hello\":\"world\"}"}
]'

```

1. **Done.** Qrie’s QOP queue accepts only the rules you just created (prefix `qrie-forward-*` in that region), so the queue is not public.

> If you want an extra-strict posture later, share the three Rule ARNs from the stack Outputs and Qrie can allowlist those exact ARNs on the QOP SQS policy.
> 

ℹ️ In your **QOP region**, Qrie engineers deploy:

- **DynamoDB tables** `qrie_resources` and `qrie_findings`.
- **SQS + DLQ** for event ingress (per region), with a **resource policy** that only accepts EventBridge sends matching our rule prefix (and optionally your Org ID).
- **Lambdas**: inventory (scheduled), policy scanner, and event processor (SQS trigger).
- **Cognito Identity Pool** to let the browser read the findings/resources (read-only).
- **Web stack**: CloudFront + OAC + private S3 bucket to host your per-region UI.

## FAQs

**Q: What does the stack create on your accounts?**

A: It creates the following artifacts for every account (per region) - 

- `QrieEventsToSqs-<acct>-<region>` role, trusted by EventBridge, with `sqs:SendMessage` to your QOP queue.
- `qrie-forward-ec2-<region>` rule for **EC2** write APIs.
- `qrie-forward-s3-<region>` rule for **S3** write APIs.
- `qrie-forward-iam-<region>` rule for **IAM** write APIs.
- Stack **Outputs** include the Role ARN and each Rule ARN (handy if you/ Qrie later choose to lock SQS by exact ARNs).

Q: What is in ‘Qrie On Prem’ or ‘QOP’ account?

A: For each customer, Qrie provisions a **dedicated AWS account** (per region) that hosts your Qrie instance—compute is Qrie-managed, your data stays inside your instance. Concretely, per region we run:

- **Event ingress:** an SQS queue (with DLQ) that only accepts messages from EventBridge rules we or you create; policy is locked to your Org ID or a rule name prefix (no public access).
- **Inventory & findings store:** DynamoDB tables `qrie_resources` and `qrie_findings`.
- **Processing:** three Lambdas (inventory on a schedule, event processor consuming SQS, policy scanner).
- **Browser access:** Cognito Identity Pool with read-only IAM roles so the UI can read your tables directly (no API needed for MVP).
- **UI hosting:** CloudFront + private S3 (Origin Access Control) for your regional UI.

**Q: Is the QOP SQS open to the internet?**

A: No. The policy only allows the **EventBridge service** and only for **rules** with our prefix in the customer account/region (and optionally by Org ID).

**Q: Can we add more services later?**

A: Yes—update the bootstrap stack to include additional rule blocks (e.g., `rds.amazonaws.com`) with the eventName list you want; the QOP SQS policy already matches on the **rule prefix**.

**Q: We run in 10+ regions—how do we scale?**

A: Use the CloudShell loop above, or deploy the template via **StackSets** across your accounts/regions; nothing changes on Qrie’s side (each QOP region is isolated).