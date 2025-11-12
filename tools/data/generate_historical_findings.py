#!/usr/bin/env python3
"""
Generate historical findings spanning 8 weeks for dashboard testing
"""
from datetime import datetime, timedelta, timezone
import random

def generate_historical_findings():
    """Generate findings with dates spanning 8 weeks - expanded for pagination testing"""
    findings = []
    now = datetime.now(timezone.utc)
    
    # Expanded policy configurations with more accounts and services
    policy_configs = [
        ('S3BucketPublic', '123456789012_s3', 90),
        ('S3BucketVersioningDisabled', '123456789012_s3', 60),
        ('S3BucketEncryptionDisabled', '987654321098_s3', 90),
        ('S3BucketPublic', '987654321098_s3', 90),
        ('S3BucketVersioningDisabled', '555666777888_s3', 60),
        ('S3BucketEncryptionDisabled', '111222333444_s3', 90),
        ('EC2UnencryptedEBS', '123456789012_ec2', 70),
        ('EC2UnencryptedEBS', '987654321098_ec2', 70),
        ('EC2UnencryptedEBS', '555666777888_ec2', 70),
        ('IAMRootAccountActive', '123456789012_iam', 95),
        ('IAMUserMfaDisabled', '123456789012_iam', 85),
        ('IAMUserMfaDisabled', '987654321098_iam', 85),
        ('IAMUserMfaDisabled', '555666777888_iam', 85),
    ]
    
    # Generate findings across 8 weeks - increased count for pagination testing
    for week_offset in range(8):
        week_start = now - timedelta(weeks=week_offset)
        
        # Generate 20-30 new findings per week (was 5-15) to ensure 150+ total findings
        num_findings = random.randint(20, 30)
        
        for i in range(num_findings):
            policy_id, account_service, severity = random.choice(policy_configs)
            
            # Random day within the week
            days_offset = random.randint(0, 6)
            first_seen = week_start - timedelta(days=days_offset)
            
            # 30% chance of being resolved
            is_resolved = random.random() < 0.3
            
            if is_resolved:
                # Resolved 1-7 days after creation
                resolution_days = random.randint(1, 7)
                last_evaluated = first_seen + timedelta(days=resolution_days)
                state = 'RESOLVED'
            else:
                # Still active
                last_evaluated = now
                state = 'ACTIVE'
            
            # Generate unique ARN
            resource_type = account_service.split('_')[1]
            resource_id = f"{resource_type}-{week_offset}-{i}"
            
            if resource_type == 's3':
                arn = f"arn:aws:s3:::bucket-{resource_id}"
            elif resource_type == 'ec2':
                arn = f"arn:aws:ec2:us-east-1:{account_service.split('_')[0]}:instance/i-{resource_id}"
            elif resource_type == 'iam':
                arn = f"arn:aws:iam::{account_service.split('_')[0]}:user/user-{resource_id}"
            else:
                arn = f"arn:aws:{resource_type}:us-east-1:{account_service.split('_')[0]}:resource/{resource_id}"
            
            finding = {
                'ARN': arn,
                'Policy': policy_id,
                'AccountService': account_service,
                'Severity': severity,
                'State': state,
                'FirstSeen': first_seen.isoformat(),
                'LastEvaluated': last_evaluated.isoformat(),
                'Evidence': {
                    'generated': True,
                    'week_offset': week_offset,
                    'finding_index': i
                }
            }
            
            findings.append(finding)
    
    print(f"Generated {len(findings)} historical findings")
    print(f"  Active: {sum(1 for f in findings if f['State'] == 'ACTIVE')}")
    print(f"  Resolved: {sum(1 for f in findings if f['State'] == 'RESOLVED')}")
    
    return findings

if __name__ == '__main__':
    findings = generate_historical_findings()
    for f in findings[:5]:
        print(f"  {f['Policy']} - {f['State']} - {f['FirstSeen'][:10]}")
