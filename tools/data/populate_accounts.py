#!/usr/bin/env python3
"""
Account Populator Script for Qrie MVP

This script manages customer accounts in the qrie_accounts DynamoDB table.
It can add/remove accounts from a CSV file or individual account operations.

Usage:
    python populate_accounts.py --csv accounts.csv --table-name qrie_accounts
    python populate_accounts.py --add-account 123456789012 --table-name qrie_accounts
    python populate_accounts.py --remove-account 123456789012 --table-name qrie_accounts
    python populate_accounts.py --list --table-name qrie_accounts

CSV Format:
    AccountId,AccountName,Environment,Status
    123456789012,prod-account,production,active
    987654321098,dev-account,development,active
"""

import argparse
import csv
import boto3
import sys
from datetime import datetime
from typing import List, Dict, Optional

def get_dynamodb_table(table_name: str):
    """Get DynamoDB table resource"""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        # Test table exists
        table.load()
        return table
    except Exception as e:
        print(f"Error accessing table {table_name}: {e}")
        sys.exit(1)

def add_account(table, account_id: str, account_name: str = None, environment: str = None, status: str = "active"):
    """Add a single account to the table"""
    item = {
        'AccountId': account_id,
        'Status': status,
        'CreatedAt': datetime.utcnow().isoformat() + 'Z',
        'UpdatedAt': datetime.utcnow().isoformat() + 'Z'
    }
    
    if account_name:
        item['AccountName'] = account_name
    if environment:
        item['Environment'] = environment
    
    try:
        table.put_item(Item=item)
        print(f"✅ Added account: {account_id}")
        return True
    except Exception as e:
        print(f"❌ Error adding account {account_id}: {e}")
        return False

def remove_account(table, account_id: str):
    """Remove an account from the table"""
    try:
        table.delete_item(Key={'AccountId': account_id})
        print(f"🗑️  Removed account: {account_id}")
        return True
    except Exception as e:
        print(f"❌ Error removing account {account_id}: {e}")
        return False

def list_accounts(table) -> List[Dict]:
    """List all accounts in the table"""
    try:
        response = table.scan()
        accounts = response.get('Items', [])
        
        if not accounts:
            print("No accounts found in table")
            return []
        
        print(f"\n📋 Found {len(accounts)} accounts:")
        print("-" * 80)
        print(f"{'Account ID':<15} {'Name':<20} {'Environment':<15} {'Status':<10} {'Created':<20}")
        print("-" * 80)
        
        for account in sorted(accounts, key=lambda x: x['AccountId']):
            account_id = account['AccountId']
            name = account.get('AccountName', 'N/A')
            env = account.get('Environment', 'N/A')
            status = account.get('Status', 'N/A')
            created = account.get('CreatedAt', 'N/A')[:19] if account.get('CreatedAt') else 'N/A'
            
            print(f"{account_id:<15} {name:<20} {env:<15} {status:<10} {created:<20}")
        
        return accounts
    except Exception as e:
        print(f"❌ Error listing accounts: {e}")
        return []

def process_csv(table, csv_file: str, dry_run: bool = False):
    """Process accounts from CSV file"""
    try:
        with open(csv_file, 'r') as file:
            reader = csv.DictReader(file)
            
            # Validate CSV headers
            required_headers = ['AccountId']
            if not all(header in reader.fieldnames for header in required_headers):
                print(f"❌ CSV must contain at least: {required_headers}")
                print(f"Found headers: {reader.fieldnames}")
                return False
            
            accounts_to_process = list(reader)
            
            if dry_run:
                print(f"🔍 DRY RUN: Would process {len(accounts_to_process)} accounts:")
                for account in accounts_to_process:
                    print(f"  - {account['AccountId']} ({account.get('AccountName', 'No name')})")
                return True
            
            success_count = 0
            for account in accounts_to_process:
                account_id = account['AccountId'].strip()
                account_name = account.get('AccountName', '').strip() or None
                environment = account.get('Environment', '').strip() or None
                status = account.get('Status', 'active').strip()
                
                if add_account(table, account_id, account_name, environment, status):
                    success_count += 1
            
            print(f"\n✅ Successfully processed {success_count}/{len(accounts_to_process)} accounts")
            return success_count == len(accounts_to_process)
            
    except FileNotFoundError:
        print(f"❌ CSV file not found: {csv_file}")
        return False
    except Exception as e:
        print(f"❌ Error processing CSV: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Manage Qrie customer accounts')
    parser.add_argument('--table-name', required=True, help='DynamoDB table name')
    parser.add_argument('--csv', help='CSV file to import accounts from')
    parser.add_argument('--add-account', help='Add a single account ID')
    parser.add_argument('--remove-account', help='Remove a single account ID')
    parser.add_argument('--list', action='store_true', help='List all accounts')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--account-name', help='Account name (used with --add-account)')
    parser.add_argument('--environment', help='Environment tag (used with --add-account)')
    
    args = parser.parse_args()
    
    # Validate arguments
    actions = [args.csv, args.add_account, args.remove_account, args.list]
    if sum(bool(action) for action in actions) != 1:
        print("❌ Please specify exactly one action: --csv, --add-account, --remove-account, or --list")
        sys.exit(1)
    
    # Get table
    table = get_dynamodb_table(args.table_name)
    
    # Execute action
    if args.csv:
        success = process_csv(table, args.csv, args.dry_run)
        sys.exit(0 if success else 1)
    elif args.add_account:
        success = add_account(table, args.add_account, args.account_name, args.environment)
        sys.exit(0 if success else 1)
    elif args.remove_account:
        success = remove_account(table, args.remove_account)
        sys.exit(0 if success else 1)
    elif args.list:
        list_accounts(table)
        sys.exit(0)

if __name__ == '__main__':
    main()
