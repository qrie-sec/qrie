#!/usr/bin/env python3
"""
QOP (Qrie On-Premises) - Main orchestrator script

Usage:
    ./qop.py --build [--region REGION]
    ./qop.py --test-unit
    ./qop.py --deploy-core --region REGION [--profile PROFILE]
    ./qop.py --deploy-ui --region REGION [--profile PROFILE]
    ./qop.py --info --region REGION [--profile PROFILE]
    ./qop.py --test-integ --region REGION [--profile PROFILE]
    ./qop.py --test-api --region REGION [--profile PROFILE]
    ./qop.py --full-deploy --region REGION [--profile PROFILE]

Custom Domain Setup:
    To use a custom domain (e.g., us-east-1.customer.qrie.com):
    1. Set up DNS delegation for your domain
    2. Deploy with: cdk deploy QrieWeb -c ui_domain=us-east-1.customer.qrie.com
    3. Create DNS CNAME record pointing to the CloudFront distribution

Commands:
    --build         Build all components (infra + UI)
    --test-unit     Run unit tests
    --deploy-core   Deploy core infrastructure (QrieCore + QrieWeb stacks)
    --deploy-ui     Deploy UI to S3 + CloudFront
    --info          Show deployment information (URLs, stack status, etc.)
    --test-integ    Run integration tests
    --test-api      Run API endpoint tests
    --full-deploy   Complete deployment pipeline (build -> test -> deploy -> test)

Required:
    --region        AWS region (no defaults)

Optional:
    --profile       AWS profile (defaults to default)
    --skip-confirm  Skip confirmation prompts
    --dry-run       Show what would be done without executing
"""

import argparse
import subprocess
import sys
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Import boto3 only when needed for AWS operations
try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class QOPOrchestrator:
    def __init__(self, region: str, profile: Optional[str] = None, skip_confirm: bool = False, dry_run: bool = False):
        self.region = region
        self.profile = profile
        self.skip_confirm = skip_confirm
        self.dry_run = dry_run
        self.project_root = Path(__file__).parent
        
        # Setup AWS session (only if boto3 is available and region is provided)
        self.aws_session = None
        if BOTO3_AVAILABLE and region:
            session_kwargs = {'region_name': region}
            if profile:
                session_kwargs['profile_name'] = profile
            self.aws_session = boto3.Session(**session_kwargs)
        
    def _print_header(self, title: str):
        """Print formatted header"""
        print(f"\n{'='*60}")
        print(f"🚀 {title}")
        print(f"{'='*60}")
        
    def _print_info(self, message: str):
        """Print info message"""
        print(f"ℹ️  {message}")
        
    def _print_success(self, message: str):
        """Print success message"""
        print(f"✅ {message}")
        
    def _print_error(self, message: str):
        """Print error message"""
        print(f"❌ {message}")
        
    def _print_warning(self, message: str):
        """Print warning message"""
        print(f"⚠️  {message}")
        
    def _confirm_action(self, action: str, details: Dict[str, Any]) -> bool:
        """Confirm action with user"""
        if self.skip_confirm:
            return True
            
        self._print_header(f"CONFIRM: {action}")
        print("📋 Action Details:")
        for key, value in details.items():
            print(f"   • {key}: {value}")
        
        if self.dry_run:
            print("\n🔍 DRY RUN - No changes will be made")
            return True
            
        response = input("\n❓ Proceed? (y/N): ").strip().lower()
        return response in ['y', 'yes']
    
    def _run_command(self, cmd: list, cwd: Optional[Path] = None, capture_output: bool = False, env: Optional[dict] = None) -> subprocess.CompletedProcess:
        """Run command with proper error handling"""
        if self.dry_run:
            print(f"🔍 DRY RUN: Would run: {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            
        self._print_info(f"Running: {' '.join(cmd)}")
        
        # Use provided env or create new one
        if env is None:
            env = os.environ.copy()
        else:
            # Merge with os.environ to preserve system environment
            merged_env = os.environ.copy()
            merged_env.update(env)
            env = merged_env
            
        if self.profile:
            env['AWS_PROFILE'] = self.profile
        if self.region:
            env['AWS_DEFAULT_REGION'] = self.region
        
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd or self.project_root,
                env=env,
                capture_output=capture_output,
                text=True
            )
            
            if result.returncode != 0:
                self._print_error(f"Command failed with exit code {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                if result.stdout:
                    print(f"Output: {result.stdout}")
                sys.exit(1)
                
            return result
        except Exception as e:
            self._print_error(f"Unexpected error: {e}")
            import traceback
            traceback.format_exc()
            sys.exit(1)
    
    def _get_stack_outputs(self, stack_name: str) -> Dict[str, str]:
        """Get CloudFormation stack outputs"""
        if not self.aws_session:
            self._print_error("AWS session not available. Install boto3 or check credentials.")
            return {}
            
        try:
            cf = self.aws_session.client('cloudformation')
            response = cf.describe_stacks(StackName=stack_name)
            
            outputs = {}
            for output in response['Stacks'][0].get('Outputs', []):
                outputs[output['OutputKey']] = output['OutputValue']
            return outputs
        except Exception as e:
            self._print_error(f"Failed to get stack outputs: {e}")
            return {}
    
    def build(self):
        """Build all components"""
        details = {
            "Region": self.region,
            "Components": "Infrastructure (CDK) + UI (Next.js)",
            "Actions": "Install dependencies, compile TypeScript, build UI"
        }
        
        if not self._confirm_action("BUILD", details):
            return
            
        self._print_header("Building Infrastructure")
        
        # Build infrastructure
        infra_path = self.project_root / "qrie-infra"
        
        # Check if virtual environment exists
        venv_path = infra_path / ".venv"
        if not venv_path.exists() and not self.dry_run:
            self._print_info("Creating virtual environment...")
            self._run_command(["python", "-m", "venv", ".venv"], cwd=infra_path)
        
        # Install dependencies using virtual environment
        if venv_path.exists():
            # Use virtual environment
            self._run_command(["bash", "-c", "source .venv/bin/activate && pip install -r requirements.txt"], cwd=infra_path)
        else:
            self._run_command(["pip", "install", "-r", "requirements.txt"], cwd=infra_path)
        
        # Synthesize CDK using virtual environment
        if venv_path.exists():
            # Use virtual environment
            cmd_str = "source .venv/bin/activate && cdk synth"
            if self.region:
                cmd_str += f" -c region={self.region}"
            self._run_command(["bash", "-c", cmd_str], cwd=infra_path)
        else:
            cmd = ["cdk", "synth"]
            if self.region:
                cmd.extend(["-c", f"region={self.region}"])
            self._run_command(cmd, cwd=infra_path)
        
        self._print_header("Building UI")
        
        # Build UI
        ui_path = self.project_root / "qrie-ui"
        # Check if using pnpm or npm
        if (ui_path / "pnpm-lock.yaml").exists():
            self._run_command(["pnpm", "install", "--frozen-lockfile"], cwd=ui_path)
        elif (ui_path / "package-lock.json").exists():
            self._run_command(["npm", "ci"], cwd=ui_path)
        else:
            self._run_command(["npm", "install"], cwd=ui_path)
        # Note: UI build with API URL happens during deploy-ui
        
        self._print_success("Build completed successfully")
    
    def test_unit(self):
        """Run unit tests"""
        details = {
            "Test Type": "Unit tests",
            "Coverage": "Lambda functions, data access layer",
            "Location": "tools/test/"
        }
        
        if not self._confirm_action("UNIT TESTS", details):
            return
            
        self._print_header("Running Unit Tests")
        
        # Run unit tests using virtual environment
        infra_path = self.project_root / "qrie-infra"
        venv_path = infra_path / ".venv"
        test_script = self.project_root / "tools" / "test" / "run_tests.py"
        
        if venv_path.exists():
            venv_python = venv_path / "bin" / "python"
            self._run_command([str(venv_python), str(test_script)])
        else:
            self._run_command([sys.executable, str(test_script)])
        
        self._print_success("Unit tests completed successfully")
    
    def deploy_core(self):
        """Deploy core infrastructure"""
        details = {
            "Region": self.region,
            "Profile": self.profile or "default",
            "Stacks": "QrieCore + QrieWeb",
            "Resources": "DynamoDB tables, Lambda functions, S3 bucket, CloudFront",
            "Prerequisites": "AWS credentials configured, CDK bootstrapped"
        }
        
        if not self._confirm_action("DEPLOY CORE INFRASTRUCTURE", details):
            return
            
        self._print_header("Deploying Core Infrastructure & Web Stack")
        
        infra_path = self.project_root / "qrie-infra"
        venv_path = infra_path / ".venv"
        
        # Deploy with CDK
        if venv_path.exists():
            # Use virtual environment
            cmd_str = "source .venv/bin/activate && cdk deploy QrieCore QrieWeb --require-approval never --outputs-file cdk-outputs.json"
            
            # Add CDK context
            if self.region:
                cmd_str += f" -c region={self.region}"
            
            # Get account ID for context
            if self.aws_session:
                try:
                    sts = self.aws_session.client('sts')
                    account_id = sts.get_caller_identity()['Account']
                    cmd_str += f" -c account={account_id}"
                except Exception as e:
                    self._print_warning(f"Could not get account ID: {e}")
            
            self._run_command(["bash", "-c", cmd_str], cwd=infra_path)
        else:
            cmd = ["cdk", "deploy", "QrieCore", "QrieWeb", "--require-approval", "never", "--outputs-file", "cdk-outputs.json"]
            
            # Add CDK context
            if self.region:
                cmd.extend(["-c", f"region={self.region}"])
            
            # Get account ID for context
            if self.aws_session:
                try:
                    sts = self.aws_session.client('sts')
                    account_id = sts.get_caller_identity()['Account']
                    cmd.extend(["-c", f"account={account_id}"])
                except Exception as e:
                    self._print_warning(f"Could not get account ID: {e}")
            
            self._run_command(cmd, cwd=infra_path)
        
        # Get and display outputs
        outputs = self._get_stack_outputs("QrieCore")
        if outputs:
            print("\n📋 Stack Outputs:")
            for key, value in outputs.items():
                print(f"   • {key}: {value}")
        
        self._print_success("Core infrastructure & web stack deployed successfully")
    
    def deploy_ui(self):
        """Deploy UI to S3 and CloudFront"""
        # First check if core infrastructure exists
        core_outputs = self._get_stack_outputs("QrieCore")
        if not core_outputs:
            self._print_error("QrieCore stack not found. Deploy core infrastructure first.")
            sys.exit(1)
        
        # Check if web infrastructure exists
        web_outputs = self._get_stack_outputs("QrieWeb")
        if not web_outputs:
            self._print_error("QrieWeb stack not found. Deploy core infrastructure first.")
            sys.exit(1)
        
        api_url = core_outputs.get('ApiUrl')
        ui_bucket = web_outputs.get('UiBucketName')
        ui_url = web_outputs.get('UiUrl')
        ui_custom_domain = web_outputs.get('UiCustomDomain')
        ui_distribution_domain = web_outputs.get('UiDistributionDomain')
        
        # Backward compatibility: use UiUrl if available, otherwise construct from UiDistributionDomain
        if not ui_url and ui_distribution_domain:
            ui_url = f"https://{ui_distribution_domain}"
        
        if not api_url or not ui_bucket or not ui_url:
            self._print_error("Required outputs not found in stacks")
            sys.exit(1)
        
        details = {
            "Region": self.region,
            "Profile": self.profile or "default",
            "API URL": api_url,
            "S3 Bucket": ui_bucket,
            "UI URL": ui_url,
            "Prerequisites": "QrieCore and QrieWeb stacks deployed"
        }
        
        if ui_custom_domain:
            details["Custom Domain"] = ui_custom_domain
        
        if not self._confirm_action("DEPLOY UI", details):
            return
            
        self._print_header("Deploying UI")
        
        ui_path = self.project_root / "qrie-ui"
        
        # Build UI with API URL
        build_env = {'NEXT_PUBLIC_API_BASE_URL': api_url}
        
        # Temporarily rename .env.local to prevent it from overriding environment variables
        env_local_path = ui_path / ".env.local"
        env_local_backup = ui_path / ".env.local.backup"
        env_local_existed = False
        
        if env_local_path.exists():
            env_local_existed = True
            env_local_path.rename(env_local_backup)
            self._print_info(f"Temporarily moved .env.local to .env.local.backup")
        
        try:
            self._run_command(["npm", "run", "build"], cwd=ui_path, env=build_env)
        finally:
            # Restore .env.local if it existed
            if env_local_existed and env_local_backup.exists():
                env_local_backup.rename(env_local_path)
                self._print_info(f"Restored .env.local")
        
        # Deploy to S3
        self._run_command([
            "aws", "s3", "sync", "./out", f"s3://{ui_bucket}/", "--delete"
        ], cwd=ui_path)
        
        # Invalidate CloudFront cache
        distribution_id = web_outputs.get('UiDistributionId')
        if distribution_id:
            self._print_info("Invalidating CloudFront cache...")
            try:
                result = self._run_command([
                    "aws", "cloudfront", "create-invalidation",
                    "--distribution-id", distribution_id,
                    "--paths", "/*"
                ], capture_output=True)
                self._print_info("Cache invalidation initiated (takes 1-5 minutes)")
            except Exception as e:
                self._print_warning(f"Cache invalidation failed: {e}")
        
        self._print_success("UI deployed successfully")
        print(f"\n🌐 UI Available at: {ui_url}")
        print(f"📊 Dashboard: {ui_url}")
        print(f"🔍 Findings: {ui_url}/findings")
        print(f"📦 Inventory: {ui_url}/inventory")
        print(f"⚙️  Management: {ui_url}/management")
        
        if distribution_id:
            print(f"\n💡 Cache invalidation in progress - hard refresh browser if needed (Cmd+Shift+R)")
    
    def show_info(self):
        """Show deployment information from CloudFormation stacks"""
        self._print_header("DEPLOYMENT INFORMATION")
        
        # Check QrieCore stack
        core_outputs = self._get_stack_outputs("QrieCore")
        if core_outputs:
            print("🔧 Core Infrastructure (QrieCore):")
            print(f"   • API URL: {core_outputs.get('ApiUrl', 'Not found')}")
            print(f"   • Account ID: {core_outputs.get('QopAccountId', 'Not found')}")
            print(f"   • Resources Table: {core_outputs.get('ResourcesTable', 'Not found')}")
            print(f"   • Findings Table: {core_outputs.get('FindingsTable', 'Not found')}")
            print(f"   • Policies Table: {core_outputs.get('PoliciesTable', 'Not found')}")
            print(f"   • Events Queue: {core_outputs.get('EventsQueueUrl', 'Not found')}")
            print(f"   • Inventory Generator: {core_outputs.get('InventoryGeneratorArn', 'Not found')}")
        else:
            print("❌ QrieCore stack not found")
        
        print()
        
        # Check QrieWeb stack
        web_outputs = self._get_stack_outputs("QrieWeb")
        if web_outputs:
            print("🌐 Web Infrastructure (QrieWeb):")
            ui_url = web_outputs.get('UiUrl')
            ui_distribution_domain = web_outputs.get('UiDistributionDomain')
            ui_custom_domain = web_outputs.get('UiCustomDomain')
            
            # Backward compatibility
            if not ui_url and ui_distribution_domain:
                ui_url = f"https://{ui_distribution_domain}"
            
            print(f"   • UI URL: {ui_url or 'Not found'}")
            print(f"   • CloudFront Domain: {ui_distribution_domain or 'Not found'}")
            print(f"   • CloudFront Distribution ID: {web_outputs.get('UiDistributionId', 'Not found')}")
            print(f"   • S3 Bucket: {web_outputs.get('UiBucketName', 'Not found')}")
            
            if ui_custom_domain:
                print(f"   • Custom Domain: {ui_custom_domain}")
            
            if ui_url:
                print(f"\n🔗 Quick Links:")
                print(f"   • Dashboard: {ui_url}")
                print(f"   • Findings: {ui_url}/findings")
                print(f"   • Inventory: {ui_url}/inventory")
                print(f"   • Management: {ui_url}/management")
        else:
            print("❌ QrieWeb stack not found")
        
        print()
        
        # Show region and profile info
        print("⚙️  Configuration:")
        print(f"   • Region: {self.region}")
        print(f"   • Profile: {self.profile or 'default'}")
        
        # Test API connectivity if available
        if core_outputs and core_outputs.get('ApiUrl'):
            api_url = core_outputs['ApiUrl']
            print(f"\n🧪 API Test Commands:")
            print(f"   curl '{api_url}accounts'")
            print(f"   curl '{api_url}resources'")
            print(f"   curl '{api_url}findings'")
            print(f"   curl '{api_url}policies'")
        
        print(f"\n📊 Stack Status:")
        self._show_stack_status("QrieCore")
        self._show_stack_status("QrieWeb")
    
    def _show_stack_status(self, stack_name: str):
        """Show CloudFormation stack status"""
        if not self.aws_session:
            return
            
        try:
            cf = self.aws_session.client('cloudformation')
            response = cf.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            status = stack['StackStatus']
            created = stack.get('CreationTime', 'Unknown')
            updated = stack.get('LastUpdatedTime', created)
            
            status_icon = "✅" if "COMPLETE" in status else "⚠️" if "PROGRESS" in status else "❌"
            print(f"   • {stack_name}: {status_icon} {status} (Updated: {updated.strftime('%Y-%m-%d %H:%M:%S')})")
            
        except Exception as e:
            print(f"   • {stack_name}: ❌ Not found or error: {e}")
    
    def seed_data(self):
        """Seed test data into deployed infrastructure"""
        details = {
            "Operation": "Seed test data",
            "Target": "DynamoDB tables in deployed infrastructure", 
            "Data": "Sample accounts, resources, findings, and policies",
            "Prerequisites": "QrieCore stack deployed"
        }
        
        if not self._confirm_action("SEED TEST DATA", details):
            return
            
        self._print_header("Seeding Test Data")
        
        # Seed test data
        seed_script = self.project_root / "tools" / "data" / "seed_data.py"
        self._run_command([sys.executable, str(seed_script), "--clear"])
        
        self._print_success("Test data seeded successfully")
    
    def purge_data(self):
        """Purge all data from deployed infrastructure (destructive)"""
        details = {
            "Operation": "⚠️  PURGE ALL DATA (DESTRUCTIVE)",
            "Target": "ALL DynamoDB tables in deployed infrastructure",
            "Tables": "accounts, resources, policies, findings, summary",
            "Warning": "This will DELETE ALL DATA - cannot be undone!",
            "Prerequisites": "QrieCore stack deployed"
        }
        
        if not self._confirm_action("PURGE ALL DATA", details):
            return
            
        self._print_header("Purging All Data")
        
        # Purge all data
        seed_script = self.project_root / "tools" / "data" / "seed_data.py"
        cmd = [sys.executable, str(seed_script), "--purge"]
        if self.skip_confirm:
            cmd.append("--skip-confirm")
        self._run_command(cmd)
        
        self._print_success("All data purged successfully")
    
    def seed_resources(self, mode, account_id):
        """Create/modify/cleanup real AWS resources for E2E testing"""
        mode_descriptions = {
            'non-compliant': 'Create non-compliant resources',
            'compliant': 'Create compliant resources',
            'remediate': 'Make resources compliant',
            'cleanup': 'Delete resources and purge findings'
        }
        
        details = {
            "Operation": f"E2E Testing - {mode_descriptions[mode]}",
            "Account": account_id,
            "Region": self.region,
            "Resources": "S3 buckets, IAM users/policies",
            "Prerequisites": "QrieCore stack deployed, account onboarded"
        }
        
        if mode == 'cleanup':
            details["Warning"] = "This will DELETE resources and PURGE findings!"
        
        if not self._confirm_action(f"SEED RESOURCES ({mode.upper()})", details):
            return
            
        self._print_header(f"E2E Testing - {mode_descriptions[mode]}")
        
        # Run seed_resources script
        seed_script = self.project_root / "tools" / "test" / "seed_resources.py"
        cmd = [
            sys.executable, str(seed_script),
            f"--{mode}",
            "--account-id", account_id,
            "--region", self.region,
            "--profile", self.profile or "default"
        ]
        self._run_command(cmd)
        
        self._print_success(f"E2E testing - {mode} completed successfully")
    
    def test_api(self):
        """Run API endpoint tests"""
        outputs = self._get_stack_outputs("QrieCore")
        api_url = outputs.get('ApiUrl', 'NOT_FOUND')
        
        details = {
            "Test Type": "API endpoint tests",
            "API URL": api_url,
            "Prerequisites": "QrieCore stack deployed, test data seeded"
        }
        
        if not self._confirm_action("API TESTS", details):
            return
            
        self._print_header("Running API Tests")
        
        if api_url == 'NOT_FOUND':
            self._print_error("API URL not found. Deploy core infrastructure first.")
            sys.exit(1)
        
        # Run API tests
        test_script = self.project_root / "tools" / "test" / "test_apis.py"
        self._run_command([sys.executable, str(test_script), api_url])
        
        self._print_success("API tests completed successfully")
    
    def full_deploy(self):
        """Complete deployment pipeline"""
        self._print_header("FULL DEPLOYMENT PIPELINE")
        print("📋 Pipeline: build → test-unit → deploy-core → seed-data → test-api → deploy-ui")
        
        if not self._confirm_action("FULL DEPLOYMENT", {
            "Region": self.region,
            "Profile": self.profile or "default",
            "Pipeline": "Complete end-to-end deployment"
        }):
            return
        
        self.build()
        self.test_unit()
        self.deploy_core()
        self.seed_data()
        self.test_api()
        self.deploy_ui()
        
        self._print_success("🎉 Full deployment completed successfully!")
    
    def generate_inventory(self, account_id=None, service='all'):
        """Generate inventory for all or specific account/service"""
        self._print_header("GENERATE INVENTORY")
        
        # Get core stack outputs for Lambda function name
        core_outputs = self._get_stack_outputs("QrieCore")
        if not core_outputs:
            self._print_error("Core infrastructure not deployed. Run --deploy-core first.")
            sys.exit(1)
        
        details = {
            "Region": self.region,
            "Profile": self.profile or "default",
            "Service": service,
            "Account": account_id or "all",
            "Scan Type": "bootstrap"
        }
        
        if not self._confirm_action("GENERATE INVENTORY", details):
            return
        
        # Prepare Lambda payload
        payload = {
            "service": service,
            "scan_type": "bootstrap"  # Bootstrap scan for manual inventory generation
        }
        if account_id:
            payload["account_id"] = account_id
        
        # Invoke inventory generator Lambda
        print(f"\n🔄 Invoking inventory generator Lambda...")
        cmd = [
            "aws", "lambda", "invoke",
            "--function-name", "qrie_inventory_generator",
            "--payload", json.dumps(payload),
            "--region", self.region,
            "response.json"
        ]
        if self.profile:
            cmd.extend(["--profile", self.profile])
        
        self._run_command(cmd)
        
        # Read and display response
        try:
            with open("response.json", "r") as f:
                response = json.load(f)
                if response.get("statusCode") == 200:
                    body = json.loads(response.get("body", "{}"))
                    print(f"\n✅ Inventory generation completed:")
                    print(f"   - Scan ID: {body.get('scan_id', 'N/A')}")
                    print(f"   - Resources found: {body.get('total_resources', 0)}")
                    print(f"   - Duration: {body.get('scan_duration_ms', 0)}ms")
                else:
                    print(f"\n⚠️  Inventory generation returned status: {response.get('statusCode')}")
        except Exception as e:
            print(f"\n⚠️  Could not parse response: {e}")
        
        self._print_success("Inventory generation completed")
    
    def scan_account(self, account_id, scan_type='bootstrap'):
        """Scan a specific account with all active policies"""
        self._print_header("SCAN ACCOUNT")
        
        # Get core stack outputs for Lambda function name
        core_outputs = self._get_stack_outputs("QrieCore")
        if not core_outputs:
            self._print_error("Core infrastructure not deployed. Run --deploy-core first.")
            sys.exit(1)
        
        details = {
            "Region": self.region,
            "Profile": self.profile or "default",
            "Account": account_id,
            "Scan Type": scan_type
        }
        
        if not self._confirm_action("SCAN ACCOUNT", details):
            return
        
        # First generate inventory for this account
        print(f"\n🔄 Step 1: Generating inventory for account {account_id}...")
        self.generate_inventory(account_id=account_id, service='all')
        
        # Then run policy scan
        print(f"\n🔄 Step 2: Running policy scan for account {account_id}...")
        payload = {
            "scan_type": scan_type
        }
        
        cmd = [
            "aws", "lambda", "invoke",
            "--function-name", "qrie_policy_scanner",
            "--payload", json.dumps(payload),
            "--region", self.region,
            "response.json"
        ]
        if self.profile:
            cmd.extend(["--profile", self.profile])
        
        self._run_command(cmd)
        
        # Read and display response
        try:
            with open("response.json", "r") as f:
                response = json.load(f)
                if response.get("statusCode") == 200:
                    body = response.get("body", {})
                    print(f"\n✅ Policy scan completed:")
                    print(f"   - Scan ID: {body.get('scan_id', 'N/A')}")
                    print(f"   - Resources processed: {body.get('processed_resources', 0)}")
                    print(f"   - Findings created: {body.get('findings_created', 0)}")
                    print(f"   - Findings closed: {body.get('findings_closed', 0)}")
                    print(f"   - Duration: {body.get('scan_duration_ms', 0)}ms")
                else:
                    print(f"\n⚠️  Policy scan returned status: {response.get('statusCode')}")
        except Exception as e:
            print(f"\n⚠️  Could not parse response: {e}")
        
        self._print_success(f"Account {account_id} scan completed")


def main():
    parser = argparse.ArgumentParser(
        description="QOP (Qrie On-Premises) - Main orchestrator script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./qop.py --build --region us-east-1
  ./qop.py --deploy-core --region us-east-1 --profile qop
  ./qop.py --full-deploy --region us-east-1 --profile qop
  ./qop.py --seed-data --region us-east-1 --profile qop
  ./qop.py --purge-data --region us-east-1 --profile qop

Common workflow:
  1. ./qop.py --build --region us-east-1
  2. ./qop.py --test-unit
  3. ./qop.py --deploy-core --region us-east-1 --profile qop
  4. ./qop.py --seed-data --region us-east-1 --profile qop
  5. ./qop.py --test-api --region us-east-1 --profile qop
  6. ./qop.py --deploy-ui --region us-east-1 --profile qop

Data management:
  ./qop.py --seed-data --region us-east-1 --profile qop    # Add test data
  ./qop.py --purge-data --region us-east-1 --profile qop   # Delete all data

E2E Testing (real AWS resources):
  ./qop.py --seed-resources non-compliant --account-id 050261919630 --region us-east-1 --profile qop
  ./qop.py --seed-resources remediate --account-id 050261919630 --region us-east-1 --profile qop
  ./qop.py --seed-resources cleanup --account-id 050261919630 --region us-east-1 --profile qop
        """
    )
    
    # Commands (mutually exclusive)
    commands = parser.add_mutually_exclusive_group(required=True)
    commands.add_argument('--build', action='store_true', help='Build all components')
    commands.add_argument('--test-unit', action='store_true', help='Run unit tests')
    commands.add_argument('--deploy-core', action='store_true', help='Deploy core infrastructure (QrieCore + QrieWeb stacks)')
    commands.add_argument('--deploy-ui', action='store_true', help='Deploy UI')
    commands.add_argument('--seed-data', action='store_true', help='Seed test data')
    commands.add_argument('--purge-data', action='store_true', help='Purge all data (destructive, requires confirmation)')
    commands.add_argument('--seed-resources', choices=['non-compliant', 'compliant', 'remediate', 'cleanup'], 
                         help='E2E testing - create/modify/cleanup real AWS resources')
    commands.add_argument('--test-api', action='store_true', help='Run API tests')
    commands.add_argument('--full-deploy', action='store_true', help='Complete deployment pipeline')
    commands.add_argument('--info', action='store_true', help='Show deployment information')
    commands.add_argument('--generate-inventory', action='store_true', help='Generate inventory (bootstrap scan)')
    commands.add_argument('--scan-account', action='store_true', help='Scan specific account with all active policies')
    
    # Required arguments
    parser.add_argument('--region', required=False, help='AWS region (required for AWS operations)')
    
    # Optional arguments
    parser.add_argument('--profile', help='AWS profile (defaults to default)')
    parser.add_argument('--skip-confirm', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--account-id', help='AWS account ID (for --generate-inventory and --scan-account)')
    parser.add_argument('--service', default='all', help='Service to scan (for --generate-inventory, default: all)')
    parser.add_argument('--scan-type', default='bootstrap', choices=['bootstrap', 'anti-entropy'], 
                       help='Scan type (for --scan-account, default: bootstrap)')
    
    args = parser.parse_args()
    
    # Validate region requirement
    aws_commands = ['deploy_core', 'deploy_ui', 'seed_data', 'purge_data', 'seed_resources', 'test_api', 'full_deploy', 'info', 'generate_inventory', 'scan_account']
    if any(getattr(args, cmd.replace('-', '_'), None) for cmd in aws_commands) and not args.region:
        parser.error("--region is required for AWS operations")
    
    # Validate account-id requirement
    if args.scan_account and not args.account_id:
        parser.error("--account-id is required for --scan-account")
    if args.seed_resources and not args.account_id:
        parser.error("--account-id is required for --seed-resources")
    
    # Create orchestrator
    orchestrator = QOPOrchestrator(
        region=args.region,
        profile=args.profile,
        skip_confirm=args.skip_confirm,
        dry_run=args.dry_run
    )
    
    # Execute command
    try:
        if args.build:
            orchestrator.build()
        elif args.test_unit:
            orchestrator.test_unit()
        elif args.deploy_core:
            orchestrator.deploy_core()
        elif args.deploy_ui:
            orchestrator.deploy_ui()
        elif args.seed_data:
            orchestrator.seed_data()
        elif args.purge_data:
            orchestrator.purge_data()
        elif args.seed_resources:
            orchestrator.seed_resources(mode=args.seed_resources, account_id=args.account_id)
        elif args.test_api:
            orchestrator.test_api()
        elif args.full_deploy:
            orchestrator.full_deploy()
        elif args.info:
            orchestrator.show_info()
        elif args.generate_inventory:
            orchestrator.generate_inventory(account_id=args.account_id, service=args.service)
        elif args.scan_account:
            orchestrator.scan_account(account_id=args.account_id, scan_type=args.scan_type)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
