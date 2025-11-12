"""
IAM User MFA Disabled Policy
Detects IAM users with console access but without MFA enabled
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_definition import PolicyDefinition

# Policy Definition
IAMUserMfaDisabled = PolicyDefinition(
    policy_id="IAMUserMfaDisabled",
    description="Detects IAM users with console password but without multi-factor authentication (MFA) enabled, increasing risk of account compromise",
    service="iam",
    category="access_control",
    severity=85,
    remediation="""
## Remediation Steps

1. **Enable MFA for all users**: Require MFA for console access
2. **Choose MFA type**:
   - Virtual MFA (Google Authenticator, Authy, etc.)
   - Hardware MFA device
   - U2F security key
3. **Enforce with IAM policy**: Deny actions without MFA
4. **Monitor compliance**: Regular audits of MFA status

## AWS CLI Commands
```bash
# List users without MFA
aws iam get-credential-report
aws iam list-users --query 'Users[*].[UserName,Arn]' --output table

# Check MFA status for specific user
aws iam list-mfa-devices --user-name USERNAME

# Enable virtual MFA device (requires QR code scan)
aws iam create-virtual-mfa-device --virtual-mfa-device-name USERNAME-mfa --outfile QRCode.png --bootstrap-method QRCodePNG
aws iam enable-mfa-device --user-name USERNAME --serial-number arn:aws:iam::ACCOUNT:mfa/USERNAME-mfa --authentication-code-1 CODE1 --authentication-code-2 CODE2
```

## IAM Policy to Enforce MFA
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyAllExceptListedIfNoMFA",
      "Effect": "Deny",
      "NotAction": [
        "iam:CreateVirtualMFADevice",
        "iam:EnableMFADevice",
        "iam:GetUser",
        "iam:ListMFADevices",
        "iam:ListVirtualMFADevices",
        "iam:ResyncMFADevice",
        "sts:GetSessionToken"
      ],
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
}
```

## Bulk Enable MFA Script
```bash
#!/bin/bash
# List all users without MFA
for user in $(aws iam list-users --query 'Users[*].UserName' --output text); do
  mfa_devices=$(aws iam list-mfa-devices --user-name "$user" --query 'MFADevices' --output text)
  if [ -z "$mfa_devices" ]; then
    echo "User $user does not have MFA enabled"
  fi
done
```

## References
- [AWS MFA Documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa.html)
- [CIS AWS Foundations Benchmark 1.10, 1.11](https://www.cisecurity.org/benchmark/amazon_web_services)
""",
    evaluation_module="iam_user_mfa_disabled"
)
