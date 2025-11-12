"""
S3 Bucket MFA Delete Disabled Policy
Detects S3 buckets without MFA delete protection enabled
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_definition import PolicyDefinition

# Policy Definition
S3BucketMfaDeleteDisabled = PolicyDefinition(
    policy_id="S3BucketMfaDeleteDisabled",
    description="Detects S3 buckets with versioning enabled but without MFA delete protection, allowing accidental or malicious deletion",
    service="s3",
    category="data_protection",
    severity=70,
    remediation="""
## Remediation Steps

1. **Verify versioning is enabled**: MFA delete requires versioning
2. **Enable MFA delete**: Requires root account credentials and MFA device
3. **Test MFA delete**: Attempt to delete a version to verify protection
4. **Document MFA device**: Keep secure record of MFA device serial number

## Important Notes
- **Root account required**: Only root account can enable MFA delete
- **Cannot use IAM**: IAM users/roles cannot enable MFA delete
- **Versioning required**: Bucket must have versioning enabled first
- **Permanent deletion protection**: Prevents permanent deletion of object versions

## AWS CLI Commands
```bash
# Enable MFA delete (requires root credentials and MFA token)
# Note: This command must be run with root account credentials
aws s3api put-bucket-versioning --bucket BUCKET_NAME \\
  --versioning-configuration Status=Enabled,MFADelete=Enabled \\
  --mfa "arn:aws:iam::ACCOUNT_ID:mfa/root-account-mfa-device XXXXXX"

# Verify MFA delete status
aws s3api get-bucket-versioning --bucket BUCKET_NAME
```

## Console Steps
1. Sign in as root account user
2. Navigate to S3 console → Select bucket → Properties
3. Under "Bucket Versioning", click Edit
4. Enable "Versioning" and "MFA delete"
5. Enter MFA code from your device

## References
- [AWS S3 MFA Delete](https://docs.aws.amazon.com/AmazonS3/latest/userguide/MultiFactorAuthenticationDelete.html)
- [CIS AWS Foundations Benchmark 2.1.3](https://www.cisecurity.org/benchmark/amazon_web_services)
""",
    evaluation_module="s3_bucket_mfa_delete_disabled"
)
