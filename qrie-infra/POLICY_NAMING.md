# Policy Naming Convention

## Principle
Policy names describe the **non-compliant state** being detected. When a finding is created for a policy, it means the resource is in the non-compliant state described by the policy name.

## Format
```
{Service}{NonCompliantCondition}
```

## Rules

1. **Service prefix**: Use AWS service name (S3, EC2, RDS, IAM, CloudTrail, etc.)
2. **Condition**: Describe the BAD state being detected
   - Use adjectives: `Unencrypted`, `Public`, `Disabled`, `Weak`, `Missing`, `Open`
   - Use past participles: `Exposed`, `Misconfigured`
   - Be specific: `PublicAccess` (not just `Public` for RDS)
   - Be concise: Avoid redundant words
3. **PascalCase**: No spaces, hyphens, or underscores
4. **No redundant words**: Avoid "Policy", "Check", "Rule", "Detection"

## Examples

### ✅ Good Names

**Encryption:**
- `S3BucketEncryptionDisabled` - Bucket does NOT have encryption
- `EC2UnencryptedEBS` - EBS volume IS unencrypted
- `RDSUnencryptedStorage` - RDS storage IS unencrypted

**Access Control:**
- `S3BucketPublic` - Bucket IS publicly accessible
- `RDSPublicAccess` - Database HAS public access enabled
- `EC2SecurityGroupOpenToWorld` - Security group allows 0.0.0.0/0
- `IAMPolicyTooPermissive` - IAM policy grants excessive permissions

**Data Protection:**
- `S3BucketVersioningDisabled` - Versioning IS NOT enabled
- `RDSBackupDisabled` - Automated backups ARE NOT enabled
- `EBSSnapshotPublic` - Snapshot IS publicly shared

**Logging/Monitoring:**
- `CloudTrailDisabled` - CloudTrail IS NOT enabled
- `VPCFlowLogsDisabled` - VPC Flow Logs ARE NOT enabled
- `S3BucketLoggingDisabled` - Access logging IS NOT enabled

**Configuration:**
- `IAMPasswordPolicyWeak` - Password policy DOES NOT meet requirements
- `EC2IMDSv1Enabled` - Instance Metadata Service v1 IS enabled (insecure)
- `RDSMultiAZDisabled` - Multi-AZ deployment IS NOT enabled

### ❌ Bad Names

- `S3BucketVersioning` - ❌ Unclear (enabled or disabled?)
- `S3BucketPrivate` - ❌ Describes compliant state (confusing)
- `S3-public-bucket-policy` - ❌ Wrong case, redundant words
- `CheckS3Encryption` - ❌ Redundant "Check" prefix
- `S3BucketVersioningEnabled` - ❌ Describes compliant state

## Why This Convention?

1. **Clarity**: Finding = Problem exists
   - "You have 45 findings for S3BucketPublic" = "You have 45 public buckets"
   
2. **Natural language**: Intuitive for users
   - "S3BucketVersioningDisabled: 23 findings" = "23 buckets need versioning enabled"

3. **Industry standard**: Matches AWS Config Rules, Security Hub, Cloud Custodian

4. **Remediation clarity**: The policy name tells you what to fix
   - `EC2UnencryptedEBS` → Enable encryption on EBS volumes

5. **Consistent semantics**: Finding always means "problem detected"

## Creating New Policies

When creating a new policy:

1. **Identify the non-compliant state**: What bad condition are you detecting?
2. **Choose the service**: Which AWS service does this apply to?
3. **Name it**: `{Service}{NonCompliantCondition}`
4. **Write description**: "Detects {resources} {with/without} {condition}"
5. **Test the name**: Does "X findings for {PolicyName}" make sense?

### Example Process

**Scenario**: Detect S3 buckets without MFA Delete enabled

1. Non-compliant state: MFA Delete is disabled
2. Service: S3
3. Name: `S3BucketMFADeleteDisabled`
4. Description: "Detects S3 buckets without MFA Delete enabled"
5. Test: "15 findings for S3BucketMFADeleteDisabled" ✅ Clear!

## File Naming

Policy files should use snake_case and match the policy_id:

```
{service}_{condition}.py

Examples:
- s3_bucket_public.py → policy_id="S3BucketPublic"
- ec2_unencrypted_ebs.py → policy_id="EC2UnencryptedEBS"
- rds_public_access.py → policy_id="RDSPublicAccess"
```

## Migration Notes

When renaming existing policies:

1. Update the `policy_id` in the PolicyDefinition
2. Rename the file to match (snake_case version)
3. Update any references in seed data, tests, and documentation
4. If policies are already launched in production, create a migration script
