"""
IAM Root Account Active Policy
Detects active usage of AWS root account
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_definition import PolicyDefinition

# Policy Definition
IAMRootAccountActive = PolicyDefinition(
    policy_id="IAMRootAccountActive",
    description="Detects active usage of AWS root account, which should only be used for account and service management tasks",
    service="iam",
    category="access_control",
    severity=95,
    remediation="""
## Remediation Steps

1. **Stop using root account**: Create IAM users/roles for daily operations
2. **Remove access keys**: Delete root account access keys if they exist
3. **Enable MFA**: Enable MFA on root account
4. **Secure credentials**: Store root credentials in secure location
5. **Monitor usage**: Set up CloudWatch alarms for root account activity

## Root Account Best Practices
- **Never use for daily tasks**: Create IAM admin users instead
- **No access keys**: Root account should not have programmatic access
- **MFA required**: Always enable MFA on root account
- **Limited use cases**: Only for account/billing management

## AWS CLI Commands
```bash
# List root account access keys (run as root)
aws iam list-access-keys

# Delete root account access keys (if any exist)
aws iam delete-access-key --access-key-id ACCESS_KEY_ID

# Enable MFA on root account (must use console)
# Cannot be done via CLI - use AWS Console

# Create IAM admin user as alternative
aws iam create-user --user-name admin-user
aws iam attach-user-policy --user-name admin-user --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
aws iam create-login-profile --user-name admin-user --password 'SECURE_PASSWORD' --password-reset-required
```

## CloudWatch Alarm for Root Usage
```bash
# Create SNS topic for alerts
aws sns create-topic --name root-account-usage-alerts

# Create CloudWatch alarm
aws cloudwatch put-metric-alarm --alarm-name root-account-usage \\
  --alarm-description "Alert on root account usage" \\
  --metric-name RootAccountUsage \\
  --namespace AWS/CloudTrail \\
  --statistic Sum \\
  --period 300 \\
  --threshold 1 \\
  --comparison-operator GreaterThanOrEqualToThreshold \\
  --evaluation-periods 1 \\
  --alarm-actions arn:aws:sns:REGION:ACCOUNT:root-account-usage-alerts
```

## References
- [AWS Root Account Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html)
- [CIS AWS Foundations Benchmark 1.7, 1.12](https://www.cisecurity.org/benchmark/amazon_web_services)
""",
    evaluation_module="iam_root_account_active"
)
