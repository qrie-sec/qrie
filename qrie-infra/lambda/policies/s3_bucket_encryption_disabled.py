"""
S3 Bucket Encryption Disabled Policy
Detects S3 buckets without default encryption enabled
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_definition import PolicyDefinition

# Policy Definition
S3BucketEncryptionDisabled = PolicyDefinition(
    policy_id="S3BucketEncryptionDisabled",
    description="Detects S3 buckets without default server-side encryption enabled, exposing data at rest",
    service="s3",
    category="encryption",
    severity=90,
    remediation="""
## Remediation Steps

1. **Enable default encryption**: Configure SSE-S3 or SSE-KMS encryption
2. **Choose encryption type**: 
   - SSE-S3: AWS-managed keys (simpler)
   - SSE-KMS: Customer-managed keys (more control, audit trail)
3. **Verify existing objects**: Existing objects are NOT automatically encrypted
4. **Update bucket policy**: Optionally deny unencrypted uploads

## AWS CLI Commands
```bash
# Enable SSE-S3 encryption
aws s3api put-bucket-encryption --bucket BUCKET_NAME --server-side-encryption-configuration '{
  "Rules": [{
    "ApplyServerSideEncryptionByDefault": {
      "SSEAlgorithm": "AES256"
    },
    "BucketKeyEnabled": true
  }]
}'

# Enable SSE-KMS encryption
aws s3api put-bucket-encryption --bucket BUCKET_NAME --server-side-encryption-configuration '{
  "Rules": [{
    "ApplyServerSideEncryptionByDefault": {
      "SSEAlgorithm": "aws:kms",
      "KMSMasterKeyID": "arn:aws:kms:REGION:ACCOUNT:key/KEY_ID"
    },
    "BucketKeyEnabled": true
  }]
}'

# Deny unencrypted uploads (bucket policy)
aws s3api put-bucket-policy --bucket BUCKET_NAME --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyUnencryptedObjectUploads",
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::BUCKET_NAME/*",
    "Condition": {
      "StringNotEquals": {
        "s3:x-amz-server-side-encryption": ["AES256", "aws:kms"]
      }
    }
  }]
}'
```

## References
- [AWS S3 Default Encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-bucket-encryption.html)
- [CIS AWS Foundations Benchmark 2.1.1](https://www.cisecurity.org/benchmark/amazon_web_services)
""",
    evaluation_module="s3_bucket_encryption_disabled"
)
