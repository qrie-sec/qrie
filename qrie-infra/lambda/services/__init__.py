"""
Service registry for dynamic service support.

This module provides a centralized way to access service-specific implementations
for inventory generation, event processing, and resource description.

To onboard a new service:
1. Create services/<service>_support.py with required functions:
   - extract_arn_from_event(detail: dict) -> Optional[str]
   - describe_resource(arn: str, account_id: str, client=None) -> dict
   - list_resources(account_id: str, client=None) -> List[Dict]
2. Add service name to SUPPORTED_SERVICES list below
3. Add EventBridge rules in tools/onboarding/eventbridge-rules.yaml
4. Create policy evaluators in lambda/policies/
5. Add unit tests in tests/unit/
6. Add E2E tests in tests/e2e/test_<service>_e2e.py
7. Update README_DEV.md with service-specific notes
"""
import importlib
import os
import glob
from typing import Optional, Dict, List, Callable

# Supported services for inventory and policy evaluation
# Each service must have a corresponding <service>_support.py module
SUPPORTED_SERVICES = ["s3", "ec2", "iam"]


class ServiceRegistry:
    """
    Registry for service-specific implementations.
    Dynamically loads service support modules.
    """
    
    _modules = {}
    
    @classmethod
    def _get_module(cls, service: str):
        """Get or load service support module"""
        if service not in cls._modules:
            if service not in SUPPORTED_SERVICES:
                raise ValueError(f"Unsupported service: {service}. Supported: {SUPPORTED_SERVICES}")
            
            try:
                module = importlib.import_module(f"services.{service}_support")
                cls._modules[service] = module
            except ImportError as e:
                raise ImportError(f"Service support module not found for {service}: {str(e)}")
        
        return cls._modules[service]
    
    @classmethod
    def extract_arn_from_event(cls, service: str, detail: dict) -> Optional[str]:
        """
        Extract resource ARN from CloudTrail event detail.
        
        Args:
            service: Service name (s3, ec2, iam)
            detail: CloudTrail event detail dict
            
        Returns:
            Resource ARN or None if cannot be extracted
        """
        module = cls._get_module(service)
        return module.extract_arn_from_event(detail)
    
    @classmethod
    def describe_resource(cls, service: str, arn: str, account_id: str, client=None) -> dict:
        """
        Describe resource configuration.
        
        Args:
            service: Service name (s3, ec2, iam)
            arn: Resource ARN
            account_id: AWS account ID
            client: Optional pre-configured AWS client
            
        Returns:
            Resource configuration dict
        """
        module = cls._get_module(service)
        return module.describe_resource(arn, account_id, client)
    
    @classmethod
    def list_resources(cls, service: str, account_id: str, client=None) -> List[Dict]:
        """
        List all resources for a service in an account.
        
        Args:
            service: Service name (s3, ec2, iam)
            account_id: AWS account ID
            client: Optional pre-configured AWS client
            
        Returns:
            List of resource configuration dicts
        """
        module = cls._get_module(service)
        return module.list_resources(account_id, client)


# Convenience functions for direct access
def extract_arn_from_event(service: str, detail: dict) -> Optional[str]:
    """Extract ARN from CloudTrail event detail"""
    return ServiceRegistry.extract_arn_from_event(service, detail)

def describe_resource(service: str, arn: str, account_id: str, client=None) -> dict:
    """Describe resource configuration"""
    return ServiceRegistry.describe_resource(service, arn, account_id, client)

def list_resources(service: str, account_id: str, client=None) -> List[Dict]:
    """List all resources for a service"""
    return ServiceRegistry.list_resources(service, account_id, client)
