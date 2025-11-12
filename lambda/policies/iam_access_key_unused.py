"""
IAM Access Key Unused Policy
Detects IAM access keys that haven't been used recently
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_definition import PolicyDefinition

# Policy Definition
IAMAccessKeyUnused = PolicyDefinition(
    policy_id="IAMAccessKeyUnused",
    description="Detects IAM access keys that haven't been used in 90+ days, which should be deactivated or deleted to reduce attack surface",
    service="iam",
    category="access_control",
    severity=60,
    remediation="""
## Remediation Steps

1. **Identify unused keys**: Check last used date for all access keys
2. **Verify with owner**: Confirm key is no longer needed
3. **Deactivate first**: Deactivate key and monitor for issues
4. **Delete after grace period**: Delete key after 30-day grace period
5. **Rotate active keys**: Regularly rotate keys that are still in use

## Recommended Thresholds
- **Warning**: Keys unused for 45+ days
- **Critical**: Keys unused for 90+ days
- **Action**: Deactivate keys unused for 120+ days

## AWS CLI Commands
```bash
# Generate credential report
aws iam generate-credential-report
sleep 5
aws iam get-credential-report --query 'Content' --output text | base64 -d > credential-report.csv

# List all access keys with last used date
aws iam list-users --query 'Users[*].UserName' --output text | while read user; do
  aws iam list-access-keys --user-name "$user" --query 'AccessKeyMetadata[*].[UserName,AccessKeyId,Status,CreateDate]' --output table
  aws iam get-access-key-last-used --access-key-id ACCESS_KEY_ID
done

# Deactivate unused access key
aws iam update-access-key --user-name USERNAME --access-key-id ACCESS_KEY_ID --status Inactive

# Delete access key (after grace period)
aws iam delete-access-key --user-name USERNAME --access-key-id ACCESS_KEY_ID
```

## Automated Cleanup Script
```bash
#!/bin/bash
# Find and deactivate access keys unused for 90+ days

THRESHOLD_DAYS=90
CURRENT_DATE=$(date +%s)

aws iam list-users --query 'Users[*].UserName' --output text | while read user; do
  aws iam list-access-keys --user-name "$user" --query 'AccessKeyMetadata[*].AccessKeyId' --output text | while read key_id; do
    last_used=$(aws iam get-access-key-last-used --access-key-id "$key_id" --query 'AccessKeyLastUsed.LastUsedDate' --output text)
    
    if [ "$last_used" != "None" ]; then
      last_used_epoch=$(date -d "$last_used" +%s)
      days_unused=$(( ($CURRENT_DATE - $last_used_epoch) / 86400 ))
      
      if [ $days_unused -gt $THRESHOLD_DAYS ]; then
        echo "Deactivating key $key_id for user $user (unused for $days_unused days)"
        aws iam update-access-key --user-name "$user" --access-key-id "$key_id" --status Inactive
      fi
    fi
  done
done
```

## Key Rotation Best Practices
```bash
# Rotate access keys (create new, test, delete old)
# 1. Create new key
NEW_KEY=$(aws iam create-access-key --user-name USERNAME)

# 2. Update applications with new key
# (Manual step - update configs, environment variables, etc.)

# 3. Test new key
export AWS_ACCESS_KEY_ID=$(echo $NEW_KEY | jq -r '.AccessKey.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo $NEW_KEY | jq -r '.AccessKey.SecretAccessKey')
aws sts get-caller-identity

# 4. Deactivate old key
aws iam update-access-key --user-name USERNAME --access-key-id OLD_KEY_ID --status Inactive

# 5. After grace period, delete old key
aws iam delete-access-key --user-name USERNAME --access-key-id OLD_KEY_ID
```

## References
- [AWS Access Key Rotation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_RotateAccessKey)
- [CIS AWS Foundations Benchmark 1.3, 1.4](https://www.cisecurity.org/benchmark/amazon_web_services)
""",
    evaluation_module="iam_access_key_unused"
)
