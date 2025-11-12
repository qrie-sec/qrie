"""
PolicyManager - Single authority for all policy operations.
Handles both static policy definitions and launched policy management.
"""
import os
import boto3
import datetime
import importlib
import importlib.util
import inspect
from pathlib import Path
from typing import List, Dict, Optional
from functools import lru_cache
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from policy_definition import PolicyDefinition, Policy, ScopeConfig
from common_utils import get_policies_table
from common.logger import error

class PolicyManager:
    """Manages all policy data access operations with caching"""
    
    def __init__(self):
        self.table = get_policies_table()
    
    # ============================================================================
    # STATIC POLICY OPERATIONS
    # ============================================================================
    
    @lru_cache(maxsize=32)
    def get_available_policies(self) -> List[PolicyDefinition]:
        """Discover all available policies using introspection"""
        policies = []
        policies_dir = Path(__file__).parent.parent / 'policies'
        
        if not policies_dir.exists():
            return policies
        
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
                        policies.append(obj)
                        
            except Exception as e:
                error(f"Error loading policy module {module_name}: {str(e)}")
                continue
        
        return policies

    @lru_cache(maxsize=64)
    def get_policy_definition(self, policy_id: str) -> Optional[PolicyDefinition]:
        """Get a specific policy definition by ID"""
        for policy in self.get_available_policies():
            if policy.policy_id == policy_id:
                return policy
        return None

    @lru_cache(maxsize=32)
    def get_policy_evaluator_class(self, policy_id: str):
        """Get the evaluator class for a policy"""
        policy_def = self.get_policy_definition(policy_id)
        if not policy_def:
            raise ValueError(f"Policy {policy_id} not found")
        
        module_path = f"policies.{policy_def.evaluation_module}"
        try:
            module = importlib.import_module(module_path)
            
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (hasattr(obj, 'evaluate') and 
                    name.endswith('Evaluator') and 
                    obj.__module__ == module.__name__):
                    return obj
            
            raise ValueError(f"No evaluator class found in {module_path}")
            
        except ImportError as e:
            raise ValueError(f"Could not import evaluation module {module_path}: {str(e)}")

    def create_policy_evaluator(self, policy_id: str, launched_policy: Policy):
        """Create a policy evaluator instance with launched policy configuration"""
        policy_def = self.get_policy_definition(policy_id)
        if not policy_def:
            raise ValueError(f"Policy {policy_id} not found")
        
        evaluator_class = self.get_policy_evaluator_class(policy_id)
        severity = launched_policy.severity or policy_def.severity
        
        return evaluator_class(policy_id, severity, launched_policy.scope)

    def get_policies_by_service(self, service: str) -> List[PolicyDefinition]:
        """Get all available policies for a specific service"""
        return [p for p in self.get_available_policies() if p.service == service]

    def get_policies_by_category(self, category: str) -> List[PolicyDefinition]:
        """Get all available policies for a specific category"""
        return [p for p in self.get_available_policies() if p.category == category]
    
    # ============================================================================
    # LAUNCHED POLICY OPERATIONS
    # ============================================================================
    
    def launch_policy(self, policy_id: str, scope: ScopeConfig, severity: Optional[int] = None, 
                     remediation: Optional[str] = None) -> None:
        """Launch a policy with customer configuration"""
        
        # Validate policy exists
        policy_def = self.get_policy_definition(policy_id)
        if not policy_def:
            raise ValueError(f"Policy {policy_id} not found")
        
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        item = {
            'PolicyId': policy_id,
            'Status': 'active',
            'Scope': self._serialize_scope(scope),
            'CreatedAt': now,
            'UpdatedAt': now
        }
        
        # Add optional overrides if specified
        if severity is not None:
            item['Severity'] = severity
        if remediation is not None:
            item['Remediation'] = remediation
        
        self.table.put_item(Item=item)
        
        # Clear cache for this policy
        self._clear_policy_cache(policy_id)

    def update_launched_policy(self, policy_id: str, **kwargs) -> bool:
        """Update a launched policy"""
        update_expression_parts = []
        expression_values = {}
        
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        update_expression_parts.append("UpdatedAt = :updated_at")
        expression_values[':updated_at'] = now
        
        if 'status' in kwargs:
            update_expression_parts.append("#status = :status")
            expression_values[':status'] = kwargs['status']
        
        if 'severity' in kwargs:
            update_expression_parts.append("Severity = :severity")
            expression_values[':severity'] = kwargs['severity']
        
        if 'remediation' in kwargs:
            update_expression_parts.append("Remediation = :remediation")
            expression_values[':remediation'] = kwargs['remediation']
        
        if 'scope' in kwargs:
            update_expression_parts.append("#scope = :scope")
            expression_values[':scope'] = self._serialize_scope(kwargs['scope'])
        
        update_expression = "SET " + ", ".join(update_expression_parts)
        
        update_params = {
            'Key': {'PolicyId': policy_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values
        }
        
        # Add attribute names for reserved keywords
        attribute_names = {}
        if 'status' in kwargs:
            attribute_names['#status'] = 'Status'
        if 'scope' in kwargs:
            attribute_names['#scope'] = 'Scope'
        
        if attribute_names:
            update_params['ExpressionAttributeNames'] = attribute_names
        
        try:
            # Add condition to ensure the item exists
            update_params['ConditionExpression'] = 'attribute_exists(PolicyId)'
            self.table.update_item(**update_params)
            
            # Clear cache for this policy
            self._clear_policy_cache(policy_id)
            return True
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            # Policy doesn't exist
            return False

    def delete_launched_policy(self, policy_id: str) -> None:
        """Delete a launched policy"""
        self.table.delete_item(Key={'PolicyId': policy_id})
        self._clear_policy_cache(policy_id)
    
    # ============================================================================
    # READ OPERATIONS WITH CACHING
    # ============================================================================
    
    @lru_cache(maxsize=64)
    def get_launched_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a launched policy by ID (cached)"""
        response = self.table.get_item(Key={'PolicyId': policy_id})
        if 'Item' not in response:
            return None
        
        return self._deserialize_launched_policy(response['Item'])

    @lru_cache(maxsize=32)
    def list_launched_policies(self, status_filter: Optional[str] = None) -> List[Policy]:
        """List all launched policies (cached by status)"""
        response = self.table.scan()
        policies = [self._deserialize_launched_policy(item) for item in response.get('Items', [])]
        
        if status_filter:
            policies = [p for p in policies if p.status == status_filter]
        
        return policies

    def get_active_policies_for_service(self, service: str) -> List[Policy]:
        """Get all active launched policies for a specific service"""
        active_policies = self.list_launched_policies(status_filter='active')
        
        service_policies = []
        for policy in active_policies:
            policy_def = self.get_policy_definition(policy.policy_id)
            if policy_def and policy_def.service == service:
                service_policies.append(policy)
        
        return service_policies
    
    @lru_cache(maxsize=128)
    def get_applicable_policies(self, service: str, account_id: str) -> List[Dict]:
        """Get all active launched policies applicable to a service and account (cached)"""
        launched_policies = [p for p in self.list_launched_policies('active')]
        applicable = []
        
        for launched_policy in launched_policies:
            # Get the static policy definition
            policy_def = self.get_policy_definition(launched_policy.policy_id)
            if not policy_def:
                continue
            
            # Check if policy applies to this service
            if policy_def.service != service:
                continue
            
            # Check if policy applies to this account
            from scoping import should_evaluate_resource
            if should_evaluate_resource(account_id, f"arn:aws:*:*:{account_id}:*", launched_policy.scope):
                # Combine static definition with launched configuration
                applicable.append({
                    'policy_id': policy_def.policy_id,
                    'description': policy_def.description,
                    'service': policy_def.service,
                    'category': policy_def.category,
                    'evaluation_module': policy_def.evaluation_module,
                    'remediation': launched_policy.remediation or policy_def.remediation,
                    'severity': launched_policy.severity or policy_def.severity,
                    'scope': launched_policy.scope,
                    'status': launched_policy.status,
                    'created_at': launched_policy.created_at,
                    'updated_at': launched_policy.updated_at
                })
        
        return applicable
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def _serialize_scope(self, scope: ScopeConfig) -> Dict:
        """Convert ScopeConfig to DynamoDB item"""
        return {
            'IncludeAccounts': scope.include_accounts or [],
            'ExcludeAccounts': scope.exclude_accounts or [],
            'IncludeTags': scope.include_tags or {},
            'ExcludeTags': scope.exclude_tags or {},
            'IncludeOuPaths': scope.include_ou_paths or [],
            'ExcludeOuPaths': scope.exclude_ou_paths or []
        }

    def _deserialize_scope(self, scope_dict: Dict) -> ScopeConfig:
        """Convert DynamoDB item to ScopeConfig"""
        return ScopeConfig(
            include_accounts=scope_dict.get('IncludeAccounts') or None,
            exclude_accounts=scope_dict.get('ExcludeAccounts') or None,
            include_tags=scope_dict.get('IncludeTags') or None,
            exclude_tags=scope_dict.get('ExcludeTags') or None,
            include_ou_paths=scope_dict.get('IncludeOuPaths') or None,
            exclude_ou_paths=scope_dict.get('ExcludeOuPaths') or None
        )

    def _deserialize_launched_policy(self, item: Dict) -> Policy:
        """Convert DynamoDB item to Policy"""
        # Get the base policy definition to fill in missing fields
        policy_def = self.get_policy_definition(item['PolicyId'])
        if not policy_def:
            raise ValueError(f"Policy definition not found for {item['PolicyId']}")
        
        return Policy(
            policy_id=item['PolicyId'],
            description=policy_def.description,
            service=policy_def.service,
            category=policy_def.category,
            severity=int(item.get('Severity', policy_def.severity)) if item.get('Severity') is not None else policy_def.severity,
            remediation=item.get('Remediation', policy_def.remediation),
            evaluation_module=policy_def.evaluation_module,
            scope=self._deserialize_scope(item['Scope']),
            status=item['Status'],
            created_at=item['CreatedAt'],
            updated_at=item['UpdatedAt']
        )
    
    def _clear_policy_cache(self, policy_id: str) -> None:
        """Clear cached data for a specific policy"""
        # Clear specific policy cache
        self.get_launched_policy.cache_clear()
        # Clear list cache since it might include this policy
        self.list_launched_policies.cache_clear()
        # Clear applicable policies cache since it depends on launched policies
        self.get_applicable_policies.cache_clear()
