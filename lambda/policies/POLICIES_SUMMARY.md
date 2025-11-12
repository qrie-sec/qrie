# Qrie Security Policies - Summary

## Overview
This directory contains security policy definitions for AWS resource compliance checking. Each policy follows the non-compliant state naming convention and includes detailed remediation guidance.

## Policy Naming Convention
Policy names describe the **BAD state** being detected:
- Format: `{Service}{NonCompliantCondition}`
- Example: `S3BucketEncryptionDisabled` (bucket IS missing encryption)

See [POLICY_NAMING.md](../../POLICY_NAMING.md) for full guidelines.

## Current Policies

### S3 Bucket Security (4 policies)

| Policy ID | Severity | Category | Description |
|-----------|----------|----------|-------------|
| `S3BucketPublic` | 90 | access_control | Detects buckets with public read access |
| `S3BucketVersioningDisabled` | 60 | data_protection | Detects buckets without versioning enabled |
| `S3BucketEncryptionDisabled` | 90 | encryption | Detects buckets without default encryption |
| `S3BucketMfaDeleteDisabled` | 70 | data_protection | Detects versioned buckets without MFA delete |

### IAM Security (5 policies)

| Policy ID | Severity | Category | Description |
|-----------|----------|----------|-------------|
| `IAMRootAccountActive` | 95 | access_control | Detects active root account usage |
| `IAMUserMfaDisabled` | 85 | access_control | Detects console users without MFA |
| `IAMPolicyOverlyPermissive` | 80 | access_control | Detects policies with wildcard permissions |
| `IAMAccessKeyUnused` | 60 | access_control | Detects access keys unused for 90+ days |
| `IAMAccessKeyNotRotated` | 70 | access_control | Detects access keys older than 90 days |

### EC2 Security (1 policy)

| Policy ID | Severity | Category | Description |
|-----------|----------|----------|-------------|
| `EC2UnencryptedEBS` | 85 | encryption | Detects EC2 instances with unencrypted EBS volumes |

### RDS Security (1 policy)

| Policy ID | Severity | Category | Description |
|-----------|----------|----------|-------------|
| `RDSPublicAccess` | 90 | access_control | Detects RDS instances with public accessibility |

## Total: 11 Policies

## Severity Levels

- **90-100 (Critical)**: Immediate security risk, data exposure
- **70-89 (High)**: Significant security gap, compliance violation
- **50-69 (Medium)**: Security best practice violation
- **30-49 (Low)**: Minor configuration issue
- **0-29 (Info)**: Informational finding

## Categories

- **access_control**: IAM, permissions, public access
- **encryption**: Data at rest/transit encryption
- **data_protection**: Versioning, backups, MFA delete
- **network_security**: Security groups, VPC, network ACLs
- **logging**: CloudTrail, VPC Flow Logs, access logging
- **monitoring**: CloudWatch, GuardDuty, Security Hub

## Policy Structure

Each policy file contains:
```python
PolicyDefinition(
    policy_id="ServiceNonCompliantCondition",
    description="Clear description of what's being detected",
    service="aws_service",
    category="security_category",
    severity=0-100,
    remediation="Detailed markdown with steps, CLI commands, references",
    evaluation_module="module_name"
)
```

## Adding New Policies

1. Create policy file: `{service}_{condition}.py`
2. Follow naming convention: `{Service}{NonCompliantCondition}`
3. Include comprehensive remediation guidance
4. Add AWS CLI commands and examples
5. Reference CIS benchmarks where applicable
6. Update this summary file

## CIS Benchmark Coverage

Current policies map to these CIS AWS Foundations Benchmark controls:

- **1.3, 1.4**: IAM access key rotation and usage
- **1.7, 1.12**: Root account protection
- **1.10, 1.11**: IAM user MFA
- **1.16**: IAM policy permissions
- **2.1.1**: S3 encryption
- **2.1.3**: S3 MFA delete

## References

- [AWS Security Best Practices](https://docs.aws.amazon.com/security/)
- [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
- [AWS Well-Architected Framework - Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
