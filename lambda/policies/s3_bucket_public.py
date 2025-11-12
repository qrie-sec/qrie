"""
S3 Bucket Public Access Policy
Detects S3 buckets with public read access
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any
from policy_definition import PolicyDefinition, PolicyEvaluator
from common_utils import get_account_from_arn

# Policy Definition
S3BucketPublic = PolicyDefinition(
    policy_id="S3BucketPublic",
    description="Detects S3 buckets with public read access that could expose sensitive data",
    service="s3",
    category="access_control",
    severity=90,
    remediation="""
## Remediation Steps

1. **Review bucket policy**: Check if public access is intentional
2. **Remove public access**: Update bucket policy to remove public read permissions
3. **Use IAM policies**: Grant access through specific IAM roles/users instead
4. **Enable Block Public Access**: Configure S3 Block Public Access settings
5. **Monitor access**: Set up CloudTrail logging for bucket access

## AWS CLI Commands
```bash
# Remove public access
aws s3api put-bucket-policy --bucket BUCKET_NAME --policy '{
  "Version": "2012-10-17",
  "Statement": []
}'

# Enable Block Public Access
aws s3api put-public-access-block --bucket BUCKET_NAME --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```
""",
    evaluation_module="s3_bucket_public"
)


class S3BucketPublicEvaluator(PolicyEvaluator):
    """Evaluator for S3 bucket public access policy"""
    
    def evaluate(self, resource_arn: str, config: Dict[str, Any], describe_time_ms: int) -> Dict[str, Any]:
        """Check if S3 bucket has public read access"""
        
        # Extract account from ARN
        try:
            account_id = get_account_from_arn(resource_arn)
        except ValueError:
            # S3 ARNs have special format (arn:aws:s3:::bucket-name)
            account_id = 'unknown'
        
        # Check scope
        if not self._should_evaluate(account_id, resource_arn):
            return {
                'scoped': False,
                'compliant': True,
                'message': 'Resource excluded by scope',
                'evidence': {},
                'finding_id': None
            }
        
        # Extract bucket name from ARN or config
        bucket_name = config.get('Name') or resource_arn.split(':::')[-1]
        
        # Check PublicAccessBlockConfiguration
        public_access_block = config.get('PublicAccessBlockConfiguration', {})
        
        # Bucket is public if ANY of these are False
        is_public = (
            not public_access_block.get('BlockPublicAcls', False) or
            not public_access_block.get('IgnorePublicAcls', False) or
            not public_access_block.get('BlockPublicPolicy', False) or
            not public_access_block.get('RestrictPublicBuckets', False)
        )
        
        # Build evidence
        evidence = {
            'bucket_name': bucket_name,
            'public_access_block_configuration': public_access_block,
            'block_public_acls': public_access_block.get('BlockPublicAcls', False),
            'ignore_public_acls': public_access_block.get('IgnorePublicAcls', False),
            'block_public_policy': public_access_block.get('BlockPublicPolicy', False),
            'restrict_public_buckets': public_access_block.get('RestrictPublicBuckets', False)
        }
        
        # Determine compliance
        compliant = not is_public
        message = f"Bucket '{bucket_name}' is {'private' if compliant else 'publicly accessible'}"
        
        # Persist finding
        account_service = f"{account_id}_s3"
        finding_id = self._persist_finding(
            resource_arn=resource_arn,
            account_service=account_service,
            compliant=compliant,
            evidence=evidence,
            describe_time_ms=describe_time_ms
        )
        
        return {
            'scoped': True,
            'compliant': compliant,
            'message': message,
            'evidence': evidence,
            'finding_id': finding_id
        }
