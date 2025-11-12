"""
EC2 Unencrypted EBS Policy
Detects EC2 instances with unencrypted EBS volumes
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_definition import PolicyDefinition

# Policy Definition
EC2UnencryptedEBS = PolicyDefinition(
    policy_id="EC2UnencryptedEBS",
    description="Detects EC2 instances with unencrypted EBS volumes that could expose sensitive data",
    service="ec2",
    category="encryption",
    severity=70,
    remediation="""
## Remediation Steps

1. **Create encrypted snapshots**: Take snapshots of unencrypted volumes
2. **Create encrypted volumes**: Create new volumes from encrypted snapshots
3. **Stop instance**: Stop the EC2 instance safely
4. **Replace volumes**: Detach unencrypted volumes and attach encrypted ones
5. **Start instance**: Restart the instance with encrypted volumes
6. **Enable default encryption**: Configure default EBS encryption for the region

## AWS CLI Commands
```bash
# Enable default EBS encryption
aws ec2 enable-ebs-encryption-by-default --region us-east-1

# Create encrypted snapshot
aws ec2 copy-snapshot --source-region us-east-1 --source-snapshot-id snap-12345 --description "Encrypted copy" --encrypted

# Create encrypted volume from snapshot
aws ec2 create-volume --size 20 --snapshot-id snap-67890 --volume-type gp3 --encrypted --availability-zone us-east-1a
```
""",
    evaluation_module="ec2_unencrypted_ebs"
)
