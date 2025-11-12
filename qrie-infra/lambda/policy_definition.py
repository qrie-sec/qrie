"""
Policy definition framework for qrie CSPM.
Core abstractions for policies, scoping, and evaluation.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Literal, Any
from abc import ABC, abstractmethod

@dataclass
class ScopeConfig:
    include_accounts: Optional[List[str]] = None
    exclude_accounts: Optional[List[str]] = None
    include_tags: Optional[Dict[str, List[str]]] = None  # {"Environment": ["prod", "staging"]}
    exclude_tags: Optional[Dict[str, List[str]]] = None
    include_ou_paths: Optional[List[str]] = None  # ["/Production/", "/Security/"]
    exclude_ou_paths: Optional[List[str]] = None

class PolicyEvaluator(ABC):
    """Abstract base class for policy evaluation functions"""
    
    def __init__(self, policy_id: str, severity: int, scope: ScopeConfig):
        """Initialize evaluator with policy metadata"""
        self.policy_id = policy_id
        self.severity = severity
        self.scope = scope
    
    @abstractmethod
    def evaluate(self, resource_arn: str, config: Dict[str, Any], describe_time_ms: int) -> Dict[str, Any]:
        """
        Evaluate a resource configuration against this policy.
        
        Args:
            resource_arn: AWS ARN of the resource (contains account ID)
            config: Resource configuration dict (from inventory or AWS API)
            describe_time_ms: Timestamp (milliseconds) when config was captured (REQUIRED)
            
        Returns:
            {
                'compliant': bool,
                'evidence': Dict[str, Any],  # Details about the evaluation
                'message': str,  # Human-readable explanation
                'finding_id': Optional[str],  # ID of created/updated finding
                'scoped': bool  # Whether resource was in scope
            }
        """
        pass
    
    def _should_evaluate(self, account_id: str, resource_arn: str) -> bool:
        """Check if resource should be evaluated based on scope"""
        # Import here to avoid circular dependencies
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from scoping import should_evaluate_resource
        
        return should_evaluate_resource(account_id, resource_arn, self.scope)
    
    def _persist_finding(self, resource_arn: str, account_service: str, compliant: bool, 
                        evidence: Dict[str, Any], describe_time_ms: int) -> Optional[str]:
        """
        Persist finding to findings database.
        
        Args:
            resource_arn: AWS ARN of the resource
            account_service: Account and service (e.g., "123456789012_s3")
            compliant: Whether resource is compliant
            evidence: Evidence dictionary from evaluation
            describe_time_ms: Timestamp (milliseconds) when config was captured (REQUIRED)
            
        Returns:
            Finding ID if non-compliant finding was created/updated, None if compliant
        """
        # Import here to avoid circular dependencies
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from data_access.findings_manager import FindingsManager
        findings_manager = FindingsManager()
        
        if compliant:
            # Resource is compliant - close any existing finding
            findings_manager.close_finding(resource_arn, self.policy_id)
            return None
        else:
            # Resource is non-compliant - create/update finding
            findings_manager.put_finding(
                resource_arn=resource_arn,
                policy_id=self.policy_id,
                account_service=account_service,
                severity=self.severity,  # Already an int (0-100)
                state='ACTIVE',
                evidence=evidence,
                describe_time_ms=describe_time_ms
            )
            return f"{resource_arn}#{self.policy_id}"  # Return a finding identifier

@dataclass
class PolicyDefinition:
    """Static policy definition with metadata"""
    policy_id: str  # Renamed from 'id' for consistency
    description: str
    service: str  # s3, ec2, iam, etc.
    category: str  # security, compliance, cost, etc.
    severity: int  # 0-100 (can be overridden by customer)
    remediation: str  # markdown with remediation steps
    evaluation_module: str  # explicit module name for evaluator

@dataclass
class Policy:
    """Active policy configuration (PolicyDefinition + scope + timestamps)"""
    # All fields from PolicyDefinition
    policy_id: str
    description: str
    service: str
    category: str
    severity: int  # Can be overridden from PolicyDefinition default
    remediation: str  # Can be overridden from PolicyDefinition default
    evaluation_module: str
    
    # Policy-specific fields
    scope: ScopeConfig
    status: str = "active"  # active, inactive, paused
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
