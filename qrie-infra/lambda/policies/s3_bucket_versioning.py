"""
S3 Bucket Versioning Policy
Detects S3 buckets without versioning enabled
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_definition import PolicyDefinition

# Policy Definition
S3BucketVersioningDisabled = PolicyDefinition(
    policy_id="S3BucketVersioningDisabled",
    description="Detects S3 buckets without versioning enabled, which could lead to data loss",
    service="s3",
    category="data_protection",
    severity=60,
    remediation="""
## Remediation Steps

1. **Enable versioning**: Turn on S3 bucket versioning to protect against accidental deletion
2. **Configure lifecycle policies**: Set up policies to manage old versions
3. **Enable MFA Delete**: Require MFA for permanent deletion of versions
4. **Monitor version usage**: Track storage costs from multiple versions

## AWS CLI Commands
```bash
# Enable versioning
aws s3api put-bucket-versioning --bucket BUCKET_NAME --versioning-configuration Status=Enabled

# Enable MFA Delete (requires root account)
aws s3api put-bucket-versioning --bucket BUCKET_NAME --versioning-configuration Status=Enabled,MfaDelete=Enabled --mfa "SERIAL_NUMBER TOKEN"
```
""",
    evaluation_module="s3_bucket_versioning"
)
