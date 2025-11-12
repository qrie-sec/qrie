#!/usr/bin/env python3
"""
Seed data script for qrie API testing
Populates DynamoDB tables with realistic test data
"""
import boto3
import os
import sys
import importlib.util
import inspect
from pathlib import Path

# Add lambda directory to path for imports
lambda_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'qrie-infra', 'lambda')
sys.path.append(lambda_dir)

from generate_historical_findings import generate_historical_findings

def get_table_names():
    """Get table names from environment or use defaults"""
    return {
        'accounts': os.getenv('ACCOUNTS_TABLE', 'qrie_accounts'),
        'resources': os.getenv('RESOURCES_TABLE', 'qrie_resources'),
        'findings': os.getenv('FINDINGS_TABLE', 'qrie_findings'), 
        'policies': os.getenv('POLICIES_TABLE', 'qrie_policies')
    }

def load_policy_definitions():
    """Load all policy definitions from the policies directory"""
    from policy_definition import PolicyDefinition
    
    policies_dir = Path(lambda_dir) / 'policies'
    policy_definitions = {}
    
    if not policies_dir.exists():
        print(f"Warning: Policies directory not found at {policies_dir}")
        return policy_definitions
    
    for policy_file in policies_dir.glob('*.py'):
        if policy_file.name.startswith('__'):
            continue
            
        module_name = policy_file.stem
        try:
            spec = importlib.util.spec_from_file_location(module_name, policy_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            for name, obj in inspect.getmembers(module):
                if isinstance(obj, PolicyDefinition):
                    policy_definitions[obj.policy_id] = obj
                    
        except Exception as e:
            print(f"Warning: Error loading policy module {module_name}: {str(e)}")
            continue
    
    return policy_definitions

def generate_bulk_resources(accounts, count_per_service=30):
    """Generate bulk resources for pagination testing"""
    resources = []
    services = ['s3', 'ec2', 'rds', 'lambda', 'dynamodb']
    
    for account in accounts:
        for service in services:
            for i in range(count_per_service):
                if service == 's3':
                    resources.append({
                        'AccountService': f'{account}_s3',
                        'ARN': f'arn:aws:s3:::bucket-{account}-{i:03d}',
                        'LastSeenAt': '2024-01-15T10:30:00Z',
                        'Configuration': {
                            'bucket_policy': {'public_read': i % 5 == 0},
                            'versioning': {'enabled': i % 3 == 0},
                            'encryption': {'enabled': i % 2 == 0}
                        }
                    })
                elif service == 'ec2':
                    resources.append({
                        'AccountService': f'{account}_ec2',
                        'ARN': f'arn:aws:ec2:us-east-1:{account}:instance/i-{i:016x}',
                        'LastSeenAt': '2024-01-15T10:30:00Z',
                        'Configuration': {
                            'instance_type': 't3.medium',
                            'security_groups': [f'sg-{i:08x}'],
                            'public_ip': f'54.{i % 256}.{(i // 256) % 256}.{i % 100}' if i % 4 == 0 else None,
                            'ebs_volumes': [
                                {'volume_id': f'vol-{i:08x}', 'encrypted': i % 2 == 0, 'size': 20}
                            ]
                        }
                    })
                elif service == 'rds':
                    resources.append({
                        'AccountService': f'{account}_rds',
                        'ARN': f'arn:aws:rds:us-east-1:{account}:db:database-{i:03d}',
                        'LastSeenAt': '2024-01-15T10:30:00Z',
                        'Configuration': {
                            'engine': 'postgres' if i % 2 == 0 else 'mysql',
                            'version': '14.9' if i % 2 == 0 else '8.0',
                            'publicly_accessible': i % 10 == 0,
                            'encrypted': i % 3 != 0,
                            'backup_retention': 7 if i % 2 == 0 else 1
                        }
                    })
                elif service == 'lambda':
                    resources.append({
                        'AccountService': f'{account}_lambda',
                        'ARN': f'arn:aws:lambda:us-east-1:{account}:function:function-{i:03d}',
                        'LastSeenAt': '2024-01-15T10:30:00Z',
                        'Configuration': {
                            'runtime': 'python3.11' if i % 2 == 0 else 'nodejs18.x',
                            'memory': 128 * (1 + i % 8),
                            'timeout': 30,
                            'vpc_config': {'vpc_id': f'vpc-{i:08x}'} if i % 5 == 0 else None
                        }
                    })
                elif service == 'dynamodb':
                    resources.append({
                        'AccountService': f'{account}_dynamodb',
                        'ARN': f'arn:aws:dynamodb:us-east-1:{account}:table/table-{i:03d}',
                        'LastSeenAt': '2024-01-15T10:30:00Z',
                        'Configuration': {
                            'billing_mode': 'PAY_PER_REQUEST' if i % 2 == 0 else 'PROVISIONED',
                            'encryption': {'enabled': i % 3 != 0},
                            'point_in_time_recovery': i % 4 == 0
                        }
                    })
    
    return resources

def create_seed_data():
    """Create comprehensive seed data for testing"""
    
    # Load actual policy definitions
    policy_defs = load_policy_definitions()
    print(f"✓ Loaded {len(policy_defs)} policy definitions")
    
    # Test accounts - expanded for pagination testing
    accounts = [
        "123456789012",  # Production account
        "987654321098",  # Staging account  
        "555666777888",  # Development account
        "111222333444",  # QA account
        "999888777666",  # DR account
    ]
    
    # Generate bulk resources for pagination testing (5 accounts × 5 services × 30 resources = 750 resources)
    print(f"\n📦 Generating bulk resources for pagination testing...")
    resources = generate_bulk_resources(accounts, count_per_service=30)
    print(f"✓ Generated {len(resources)} resources")
    
    # Add some specific test resources
    resources.extend([
        # S3 Buckets
        {
            'AccountService': '123456789012_s3',
            'ARN': 'arn:aws:s3:::prod-app-data',
            'LastSeenAt': '2024-01-15T10:30:00Z',
            'Configuration': {
                'bucket_policy': {'public_read': True},
                'versioning': {'enabled': False},
                'encryption': {'enabled': True, 'kms_key': 'aws/s3'}
            }
        },
        {
            'AccountService': '123456789012_s3',
            'ARN': 'arn:aws:s3:::prod-logs-bucket',
            'LastSeenAt': '2024-01-15T10:30:00Z',
            'Configuration': {
                'bucket_policy': {'public_read': False},
                'versioning': {'enabled': True},
                'encryption': {'enabled': True, 'kms_key': 'arn:aws:kms:us-east-1:123456789012:key/12345'}
            }
        },
        {
            'AccountService': '987654321098_s3',
            'ARN': 'arn:aws:s3:::staging-app-data',
            'LastSeenAt': '2024-01-15T10:30:00Z',
            'Configuration': {
                'bucket_policy': {'public_read': False},
                'versioning': {'enabled': False},
                'encryption': {'enabled': False}
            }
        },
        
        # EC2 Instances
        {
            'AccountService': '123456789012_ec2',
            'ARN': 'arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0',
            'LastSeenAt': '2024-01-15T10:30:00Z',
            'Configuration': {
                'instance_type': 't3.medium',
                'security_groups': ['sg-12345678'],
                'public_ip': '54.123.45.67',
                'ebs_volumes': [
                    {'volume_id': 'vol-12345', 'encrypted': False, 'size': 20},
                    {'volume_id': 'vol-67890', 'encrypted': True, 'size': 100}
                ]
            }
        },
        {
            'AccountService': '123456789012_ec2',
            'ARN': 'arn:aws:ec2:us-east-1:123456789012:instance/i-abcdef1234567890',
            'LastSeenAt': '2024-01-15T10:30:00Z',
            'Configuration': {
                'instance_type': 't3.large',
                'security_groups': ['sg-87654321'],
                'public_ip': None,
                'ebs_volumes': [
                    {'volume_id': 'vol-abc123', 'encrypted': True, 'size': 50}
                ]
            }
        },
        
        # RDS Instances
        {
            'AccountService': '123456789012_rds',
            'ARN': 'arn:aws:rds:us-east-1:123456789012:db:prod-database',
            'LastSeenAt': '2024-01-15T10:30:00Z',
            'Configuration': {
                'engine': 'postgres',
                'version': '14.9',
                'publicly_accessible': False,
                'encrypted': True,
                'backup_retention': 7
            }
        }
    ])
    
    # Sample launched policies - using actual policy definitions
    policies = []
    
    # Helper function to create launched policy from definition
    def create_launched_policy(policy_id, status='active', scope=None, severity_override=None, created_at='2024-01-15T10:30:00Z'):
        if policy_id not in policy_defs:
            print(f"Warning: Policy {policy_id} not found in definitions, skipping")
            return None
        
        policy_def = policy_defs[policy_id]
        default_scope = {
            'IncludeAccounts': [],
            'ExcludeAccounts': [],
            'IncludeTags': {},
            'ExcludeTags': {},
            'IncludeOuPaths': [],
            'ExcludeOuPaths': []
        }
        
        return {
            'PolicyId': policy_def.policy_id,
            'Status': status,
            'Scope': scope if scope else default_scope,
            'Severity': severity_override if severity_override else policy_def.severity,
            'Remediation': policy_def.remediation,
            'CreatedAt': created_at,
            'UpdatedAt': created_at
        }
    
    # S3 Policies
    policy = create_launched_policy(
        'S3BucketPublic',
        status='active',
        scope={
            'IncludeAccounts': ['123456789012', '987654321098'],
            'ExcludeAccounts': [],
            'IncludeTags': {'Environment': ['prod']},
            'ExcludeTags': {},
            'IncludeOuPaths': [],
            'ExcludeOuPaths': []
        },
        created_at='2024-01-15T10:30:00Z'
    )
    if policy:
        policies.append(policy)
    
    policy = create_launched_policy(
        'S3BucketVersioningDisabled',
        status='active',
        scope={
            'IncludeAccounts': [],
            'ExcludeAccounts': ['555666777888'],
            'IncludeTags': {},
            'ExcludeTags': {'SkipCompliance': ['true']},
            'IncludeOuPaths': [],
            'ExcludeOuPaths': []
        },
        created_at='2024-01-10T09:00:00Z'
    )
    if policy:
        policies.append(policy)
    
    policy = create_launched_policy(
        'S3BucketEncryptionDisabled',
        status='active',
        scope={
            'IncludeAccounts': ['123456789012', '987654321098'],
            'ExcludeAccounts': [],
            'IncludeTags': {},
            'ExcludeTags': {},
            'IncludeOuPaths': [],
            'ExcludeOuPaths': []
        },
        created_at='2024-01-15T10:30:00Z'
    )
    if policy:
        policies.append(policy)
    
    # EC2 Policies
    policy = create_launched_policy(
        'EC2UnencryptedEBS',
        status='active',
        scope={
            'IncludeAccounts': ['123456789012'],
            'ExcludeAccounts': [],
            'IncludeTags': {},
            'ExcludeTags': {},
            'IncludeOuPaths': [],
            'ExcludeOuPaths': []
        },
        created_at='2024-01-12T14:20:00Z'
    )
    if policy:
        policies.append(policy)
    
    # RDS Policies
    policy = create_launched_policy(
        'RDSPublicAccess',
        status='suspended',
        created_at='2024-01-08T11:15:00Z'
    )
    if policy:
        policies.append(policy)
    
    # IAM Policies
    policy = create_launched_policy(
        'IAMRootAccountActive',
        status='active',
        created_at='2024-01-10T09:00:00Z'
    )
    if policy:
        policies.append(policy)
    
    policy = create_launched_policy(
        'IAMUserMfaDisabled',
        status='active',
        scope={
            'IncludeAccounts': ['123456789012'],
            'ExcludeAccounts': [],
            'IncludeTags': {},
            'ExcludeTags': {},
            'IncludeOuPaths': [],
            'ExcludeOuPaths': []
        },
        created_at='2024-01-12T14:20:00Z'
    )
    if policy:
        policies.append(policy)
    
    print(f"✓ Created {len(policies)} launched policies from definitions")
    for p in policies:
        print(f"  - {p['PolicyId']} ({p['Status']}, severity={p['Severity']})")
    
    # Generate historical findings spanning 8 weeks
    print("\n🔍 Generating historical findings (8 weeks)...")
    findings = generate_historical_findings()
    
    # Add a few manual findings for specific test cases
    findings.extend([
        # S3 Public Bucket findings
        {
            'ARN': 'arn:aws:s3:::prod-app-data',
            'Policy': 'S3BucketPublic',
            'AccountService': '123456789012_s3',
            'Severity': 90,
            'State': 'ACTIVE',
            'FirstSeen': '2024-01-15T10:30:00Z',
            'LastEvaluated': '2024-01-20T08:15:00Z',
            'Evidence': {
                'bucket_policy': {'public_read': True},
                'policy_statement': {
                    'Effect': 'Allow',
                    'Principal': '*',
                    'Action': 's3:GetObject'
                }
            }
        },
        
        # S3 Versioning findings
        {
            'ARN': 'arn:aws:s3:::prod-app-data',
            'Policy': 'S3BucketVersioningDisabled',
            'AccountService': '123456789012_s3',
            'Severity': 60,
            'State': 'ACTIVE',
            'FirstSeen': '2024-01-15T10:30:00Z',
            'LastEvaluated': '2024-01-20T08:15:00Z',
            'Evidence': {
                'versioning': {'enabled': False},
                'mfa_delete': False
            }
        },
        {
            'ARN': 'arn:aws:s3:::staging-app-data',
            'Policy': 'S3BucketVersioningDisabled',
            'AccountService': '987654321098_s3',
            'Severity': 60,
            'State': 'ACTIVE',
            'FirstSeen': '2024-01-15T10:30:00Z',
            'LastEvaluated': '2024-01-20T08:15:00Z',
            'Evidence': {
                'versioning': {'enabled': False},
                'mfa_delete': False
            }
        },
        
        # EBS Encryption findings
        {
            'ARN': 'arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0',
            'Policy': 'EC2UnencryptedEBS',
            'AccountService': '123456789012_ec2',
            'Severity': 70,
            'State': 'ACTIVE',
            'FirstSeen': '2024-01-15T10:30:00Z',
            'LastEvaluated': '2024-01-20T08:15:00Z',
            'Evidence': {
                'unencrypted_volumes': [
                    {'volume_id': 'vol-12345', 'encrypted': False, 'size': 20}
                ],
                'total_volumes': 2,
                'unencrypted_count': 1
            }
        },
        
        # S3 Encryption findings
        {
            'ARN': 'arn:aws:s3:::staging-app-data',
            'Policy': 'S3BucketEncryptionDisabled',
            'AccountService': '987654321098_s3',
            'Severity': 90,
            'State': 'ACTIVE',
            'FirstSeen': '2024-01-15T10:30:00Z',
            'LastEvaluated': '2024-01-20T08:15:00Z',
            'Evidence': {
                'encryption': {'enabled': False},
                'default_encryption': None
            }
        },
        
        # IAM findings (simulated - would need actual IAM resources)
        {
            'ARN': 'arn:aws:iam::123456789012:root',
            'Policy': 'IAMRootAccountActive',
            'AccountService': '123456789012_iam',
            'Severity': 95,
            'State': 'ACTIVE',
            'FirstSeen': '2024-01-10T09:00:00Z',
            'LastEvaluated': '2024-01-20T08:15:00Z',
            'Evidence': {
                'last_activity': '2024-01-19T15:30:00Z',
                'activity_type': 'ConsoleLogin',
                'access_keys_exist': False
            }
        },
        {
            'ARN': 'arn:aws:iam::123456789012:user/john.doe',
            'Policy': 'IAMUserMfaDisabled',
            'AccountService': '123456789012_iam',
            'Severity': 85,
            'State': 'ACTIVE',
            'FirstSeen': '2024-01-12T14:20:00Z',
            'LastEvaluated': '2024-01-20T08:15:00Z',
            'Evidence': {
                'user_name': 'john.doe',
                'console_access': True,
                'mfa_enabled': False,
                'password_last_used': '2024-01-19T10:00:00Z'
            }
        },
        
        # Resolved finding example
        {
            'ARN': 'arn:aws:s3:::old-public-bucket',
            'Policy': 'S3BucketPublic',
            'AccountService': '123456789012_s3',
            'Severity': 90,
            'State': 'RESOLVED',
            'FirstSeen': '2024-01-10T14:20:00Z',
            'LastEvaluated': '2024-01-18T09:30:00Z',
            'Evidence': {
                'bucket_policy': {'public_read': False},
                'resolution_date': '2024-01-18T09:30:00Z',
                'resolved_by': 'security-team'
            }
        }
    ])
    
    return {
        'resources': resources,
        'policies': policies,
        'findings': findings,
        'accounts': accounts
    }

def populate_tables(region='us-east-1'):
    """Populate DynamoDB tables with seed data"""
    
    print("🚀 Starting seed data population...")
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table_names = get_table_names()
    
    # Get seed data
    seed_data = create_seed_data()
    
    try:
        # Populate Accounts table
        print(f"👥 Populating {table_names.get('accounts', 'qrie_accounts')} table...")
        accounts_table = dynamodb.Table(table_names.get('accounts', 'qrie_accounts'))
        
        for account_id in seed_data['accounts']:
            accounts_table.put_item(Item={
                'AccountId': account_id,
                'ou': 'Production' if account_id == '123456789012' else 'Staging' if account_id == '987654321098' else 'Development'
            })
            print(f"  ✅ Added account: {account_id}")
        
        # Populate Resources table
        print(f"📦 Populating {table_names['resources']} table...")
        resources_table = dynamodb.Table(table_names['resources'])
        
        for resource in seed_data['resources']:
            resources_table.put_item(Item=resource)
            print(f"  ✅ Added resource: {resource['ARN']}")
        
        # Populate Policies table
        print(f"📋 Populating {table_names['policies']} table...")
        policies_table = dynamodb.Table(table_names['policies'])
        
        for policy in seed_data['policies']:
            policies_table.put_item(Item=policy)
            print(f"  ✅ Added policy: {policy['PolicyId']} ({policy['Status']})")
        
        # Populate Findings table
        print(f"🔍 Populating {table_names['findings']} table...")
        findings_table = dynamodb.Table(table_names['findings'])
        
        for finding in seed_data['findings']:
            findings_table.put_item(Item=finding)
            print(f"  ✅ Added finding: {finding['Policy']} -> {finding['ARN']} ({finding['State']})")
        
        print("\n🎉 Seed data population completed successfully!")
        
        # Print summary
        print("\n📊 Summary:")
        print(f"  • Resources: {len(seed_data['resources'])}")
        print(f"  • Policies: {len(seed_data['policies'])}")
        print(f"  • Findings: {len(seed_data['findings'])}")
        print(f"  • Test Accounts: {len(seed_data['accounts'])}")
        
        print("\n🔗 Test Accounts:")
        for account in seed_data['accounts']:
            print(f"  • {account}")
            
    except Exception as e:
        print(f"❌ Error populating tables: {str(e)}")
        raise

def purge_tables(region='us-east-1', skip_confirm=False):
    """Purge all data from tables (destructive operation)"""
    
    print("⚠️  WARNING: This will DELETE ALL DATA from the following tables:")
    
    table_names = get_table_names()
    print(f"  • {table_names.get('accounts', 'qrie_accounts')} (accounts)")
    print(f"  • {table_names['resources']} (resources)")
    print(f"  • {table_names['policies']} (launched policies)")
    print(f"  • {table_names['findings']} (findings)")
    print(f"  • qrie_summary (cached summaries)")
    
    if not skip_confirm:
        response = input("\n❓ Are you sure you want to purge ALL data? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Purge cancelled")
            return False
    
    print("\n🧹 Purging all data...")
    
    dynamodb = boto3.resource('dynamodb', region_name=region)
    
    try:
        # Clear Accounts table
        print(f"\n📋 Purging {table_names.get('accounts', 'qrie_accounts')}...")
        accounts_table = dynamodb.Table(table_names.get('accounts', 'qrie_accounts'))
        scan = accounts_table.scan()
        count = len(scan['Items'])
        with accounts_table.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={'AccountId': item['AccountId']})
        print(f"  ✅ Deleted {count} accounts")
        
        # Clear Resources table
        print(f"\n📦 Purging {table_names['resources']}...")
        resources_table = dynamodb.Table(table_names['resources'])
        scan = resources_table.scan()
        count = len(scan['Items'])
        with resources_table.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={
                    'AccountService': item['AccountService'],
                    'ARN': item['ARN']
                })
        print(f"  ✅ Deleted {count} resources")
        
        # Clear Policies table
        print(f"\n📋 Purging {table_names['policies']}...")
        policies_table = dynamodb.Table(table_names['policies'])
        scan = policies_table.scan()
        count = len(scan['Items'])
        with policies_table.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={'PolicyId': item['PolicyId']})
        print(f"  ✅ Deleted {count} launched policies")
        
        # Clear Findings table
        print(f"\n🔍 Purging {table_names['findings']}...")
        findings_table = dynamodb.Table(table_names['findings'])
        scan = findings_table.scan()
        count = len(scan['Items'])
        with findings_table.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={
                    'ARN': item['ARN'],
                    'Policy': item['Policy']
                })
        print(f"  ✅ Deleted {count} findings")
        
        # Clear Summary table (cached data)
        print(f"\n📊 Purging qrie_summary (cached summaries)...")
        try:
            summary_table = dynamodb.Table('qrie_summary')
            scan = summary_table.scan()
            count = len(scan['Items'])
            with summary_table.batch_writer() as batch:
                for item in scan['Items']:
                    batch.delete_item(Key={'Type': item['Type']})
            print(f"  ✅ Deleted {count} cached summaries")
        except Exception as e:
            print(f"  ⚠️  Summary table not found or error: {str(e)}")
        
        print("\n✅ All data purged successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error purging tables: {str(e)}")
        raise

def clear_tables(region='us-east-1'):
    """Clear all data from tables (for testing) - deprecated, use purge_tables"""
    print("⚠️  Note: clear_tables is deprecated, using purge_tables instead")
    return purge_tables(region, skip_confirm=True)

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed qrie database with test data')
    parser.add_argument('--purge', action='store_true', help='Purge all data (destructive, requires confirmation)')
    parser.add_argument('--clear', action='store_true', help='Clear existing data before seeding')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--skip-confirm', action='store_true', help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    try:
        # Purge-only mode
        if args.purge:
            success = purge_tables(args.region, skip_confirm=args.skip_confirm)
            if success:
                print("\n✅ Purge completed successfully!")
            sys.exit(0 if success else 1)
        
        # Seed mode (with optional clear first)
        if args.clear:
            clear_tables(args.region)
        
        populate_tables(args.region)
        
        print("\n🧪 Ready for testing! Try these API calls:")
        print("  curl 'https://YOUR-API-URL/accounts'")
        print("  curl 'https://YOUR-API-URL/resources'")
        print("  curl 'https://YOUR-API-URL/findings'")
        print("  curl 'https://YOUR-API-URL/policies'")
        print("  curl 'https://YOUR-API-URL/policies/active'")
        print("  curl 'https://YOUR-API-URL/policy?id=S3BucketPublic'")
        
    except Exception as e:
        print(f"\n💥 Failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
