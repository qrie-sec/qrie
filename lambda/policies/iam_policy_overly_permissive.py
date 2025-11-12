"""
IAM Policy Overly Permissive Policy
Detects IAM policies with wildcard permissions (Action: *, Resource: *)
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_definition import PolicyDefinition

# Policy Definition
IAMPolicyOverlyPermissive = PolicyDefinition(
    policy_id="IAMPolicyOverlyPermissive",
    description="Detects IAM policies with overly permissive permissions using wildcards (Action: *, Resource: *), violating principle of least privilege",
    service="iam",
    category="access_control",
    severity=80,
    remediation="""
## Remediation Steps

1. **Identify overly permissive policies**: Find policies with Action: * and Resource: *
2. **Apply least privilege**: Grant only necessary permissions
3. **Use managed policies**: Prefer AWS managed policies when appropriate
4. **Scope resources**: Specify exact resource ARNs instead of wildcards
5. **Regular audits**: Review and tighten permissions periodically

## Common Overly Permissive Patterns
- `"Action": "*"` - All actions allowed
- `"Resource": "*"` - All resources accessible
- `"Effect": "Allow", "Action": "*", "Resource": "*"` - Full admin access
- `"Action": "s3:*"` - All S3 actions (may be too broad)

## AWS CLI Commands
```bash
# List all customer-managed policies
aws iam list-policies --scope Local --query 'Policies[*].[PolicyName,Arn]' --output table

# Get policy document
aws iam get-policy --policy-arn POLICY_ARN
aws iam get-policy-version --policy-arn POLICY_ARN --version-id VERSION_ID

# Find policies with wildcard permissions
aws iam list-policies --scope Local --query 'Policies[*].Arn' --output text | while read arn; do
  version=$(aws iam get-policy --policy-arn "$arn" --query 'Policy.DefaultVersionId' --output text)
  doc=$(aws iam get-policy-version --policy-arn "$arn" --version-id "$version" --query 'PolicyVersion.Document')
  if echo "$doc" | grep -q '"Action":"\\*"'; then
    echo "Overly permissive policy: $arn"
  fi
done
```

## Example: Tighten S3 Policy
```json
// ❌ BAD - Overly permissive
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "s3:*",
    "Resource": "*"
  }]
}

// ✅ GOOD - Least privilege
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "s3:GetObject",
      "s3:PutObject"
    ],
    "Resource": "arn:aws:s3:::my-specific-bucket/*"
  }]
}
```

## IAM Access Analyzer
```bash
# Create IAM Access Analyzer
aws accessanalyzer create-analyzer --analyzer-name my-analyzer --type ACCOUNT

# List findings
aws accessanalyzer list-findings --analyzer-arn ANALYZER_ARN --filter '{"status":{"eq":["ACTIVE"]}}'
```

## References
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [Principle of Least Privilege](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#grant-least-privilege)
- [CIS AWS Foundations Benchmark 1.16](https://www.cisecurity.org/benchmark/amazon_web_services)
""",
    evaluation_module="iam_policy_overly_permissive"
)
