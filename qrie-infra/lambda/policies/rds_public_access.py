"""
RDS Public Access Policy
Detects RDS instances with public accessibility enabled
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_definition import PolicyDefinition

# Policy Definition
RDSPublicAccess = PolicyDefinition(
    policy_id="RDSPublicAccess",
    description="Detects RDS instances with public accessibility enabled, creating security risks",
    service="rds",
    category="access_control",
    severity=95,
    remediation="""
## Remediation Steps

1. **Disable public access**: Modify RDS instance to disable public accessibility
2. **Use VPC security groups**: Configure proper security group rules for private access
3. **Set up VPN/bastion**: Use VPN or bastion host for secure database access
4. **Review subnet groups**: Ensure RDS is in private subnets
5. **Update connection strings**: Update applications to use private endpoints

## AWS CLI Commands
```bash
# Disable public accessibility
aws rds modify-db-instance --db-instance-identifier mydb --no-publicly-accessible --apply-immediately

# Create private subnet group
aws rds create-db-subnet-group --db-subnet-group-name private-subnet-group --db-subnet-group-description "Private subnets" --subnet-ids subnet-12345 subnet-67890

# Modify instance to use private subnet group
aws rds modify-db-instance --db-instance-identifier mydb --db-subnet-group-name private-subnet-group --apply-immediately
```
""",
    evaluation_module="rds_public_access"
)
