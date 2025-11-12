"""
IAM Access Key Not Rotated Policy
Detects IAM access keys that haven't been rotated in 90+ days
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_definition import PolicyDefinition

# Policy Definition
IAMAccessKeyNotRotated = PolicyDefinition(
    policy_id="IAMAccessKeyNotRotated",
    description="Detects IAM access keys older than 90 days that should be rotated to reduce risk of key compromise",
    service="iam",
    category="access_control",
    severity=70,
    remediation="""
## Remediation Steps

1. **Identify old keys**: Find keys created more than 90 days ago
2. **Plan rotation**: Schedule rotation with minimal disruption
3. **Create new key**: Generate new access key for user
4. **Update applications**: Update all systems using the old key
5. **Test thoroughly**: Verify new key works in all environments
6. **Deactivate old key**: Mark old key as inactive
7. **Monitor and delete**: After grace period, delete old key

## Rotation Schedule
- **Best practice**: Rotate every 90 days
- **Minimum**: Rotate every 180 days
- **High-security**: Rotate every 30-45 days

## AWS CLI Commands
```bash
# List access keys with creation date
aws iam list-users --query 'Users[*].UserName' --output text | while read user; do
  echo "User: $user"
  aws iam list-access-keys --user-name "$user" --query 'AccessKeyMetadata[*].[AccessKeyId,CreateDate,Status]' --output table
done

# Find keys older than 90 days
THRESHOLD_DATE=$(date -d '90 days ago' +%Y-%m-%d)
aws iam list-users --query 'Users[*].UserName' --output text | while read user; do
  aws iam list-access-keys --user-name "$user" --query "AccessKeyMetadata[?CreateDate<'$THRESHOLD_DATE'].[UserName,AccessKeyId,CreateDate]" --output table
done

# Rotate access key (step by step)
# Step 1: Create new key
aws iam create-access-key --user-name USERNAME

# Step 2: Update application configs with new key
# (Manual step)

# Step 3: Test new key
aws sts get-caller-identity

# Step 4: Deactivate old key
aws iam update-access-key --user-name USERNAME --access-key-id OLD_KEY_ID --status Inactive

# Step 5: Delete old key after grace period
aws iam delete-access-key --user-name USERNAME --access-key-id OLD_KEY_ID
```

## Automated Rotation Script
```bash
#!/bin/bash
# Automated key rotation with rollback capability

USER_NAME="$1"
OLD_KEY_ID="$2"

if [ -z "$USER_NAME" ] || [ -z "$OLD_KEY_ID" ]; then
  echo "Usage: $0 <username> <old-key-id>"
  exit 1
fi

# Create new key
echo "Creating new access key..."
NEW_KEY=$(aws iam create-access-key --user-name "$USER_NAME")
NEW_KEY_ID=$(echo $NEW_KEY | jq -r '.AccessKey.AccessKeyId')
NEW_SECRET=$(echo $NEW_KEY | jq -r '.AccessKey.SecretAccessKey')

echo "New Key ID: $NEW_KEY_ID"
echo "New Secret: $NEW_SECRET"
echo ""
echo "IMPORTANT: Update your applications with the new credentials"
echo "Press Enter when ready to deactivate old key..."
read

# Deactivate old key
echo "Deactivating old key..."
aws iam update-access-key --user-name "$USER_NAME" --access-key-id "$OLD_KEY_ID" --status Inactive

echo ""
echo "Old key deactivated. Monitor for 30 days before deletion."
echo "To rollback: aws iam update-access-key --user-name $USER_NAME --access-key-id $OLD_KEY_ID --status Active"
echo "To delete old key: aws iam delete-access-key --user-name $USER_NAME --access-key-id $OLD_KEY_ID"
```

## Key Rotation Checklist
- [ ] Identify all systems using the access key
- [ ] Create new access key
- [ ] Update primary application/service
- [ ] Update backup/DR systems
- [ ] Update CI/CD pipelines
- [ ] Update monitoring/logging systems
- [ ] Test all integrations
- [ ] Deactivate old key
- [ ] Monitor for 30 days
- [ ] Delete old key

## References
- [AWS Access Key Best Practices](https://docs.aws.amazon.com/general/latest/gr/aws-access-keys-best-practices.html)
- [CIS AWS Foundations Benchmark 1.4](https://www.cisecurity.org/benchmark/amazon_web_services)
""",
    evaluation_module="iam_access_key_rotated"
)
