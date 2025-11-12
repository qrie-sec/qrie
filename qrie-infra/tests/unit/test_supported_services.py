"""
Unit tests for SUPPORTED_SERVICES validation.

These tests ensure that:
1. Every service in SUPPORTED_SERVICES has a corresponding support module
2. Every support module in services/ is listed in SUPPORTED_SERVICES
"""
import os
import sys
import glob
import pytest

# Add lambda directory to path
lambda_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'lambda')
sys.path.insert(0, lambda_dir)

from services import SUPPORTED_SERVICES


def test_all_supported_services_have_modules():
    """Test that every service in SUPPORTED_SERVICES has a corresponding support module"""
    services_dir = os.path.join(lambda_dir, 'services')
    
    for service in SUPPORTED_SERVICES:
        module_path = os.path.join(services_dir, f'{service}_support.py')
        assert os.path.exists(module_path), \
            f"Service '{service}' in SUPPORTED_SERVICES but no module found at {module_path}"


def test_all_service_modules_are_in_supported_services():
    """Test that every <service>_support.py module is listed in SUPPORTED_SERVICES"""
    services_dir = os.path.join(lambda_dir, 'services')
    
    # Find all *_support.py files
    support_files = glob.glob(os.path.join(services_dir, '*_support.py'))
    
    for support_file in support_files:
        # Extract service name from filename (e.g., 's3_support.py' -> 's3')
        filename = os.path.basename(support_file)
        service = filename.replace('_support.py', '')
        
        assert service in SUPPORTED_SERVICES, \
            f"Found support module '{filename}' but '{service}' not in SUPPORTED_SERVICES"


def test_service_modules_have_required_functions():
    """Test that each service module has the required functions"""
    required_functions = ['extract_arn_from_event', 'describe_resource', 'list_resources']
    
    for service in SUPPORTED_SERVICES:
        # Dynamically import the module
        module_name = f'services.{service}_support'
        module = __import__(module_name, fromlist=[''])
        
        for func_name in required_functions:
            assert hasattr(module, func_name), \
                f"Service module '{service}_support' missing required function '{func_name}'"
            
            # Verify it's callable
            func = getattr(module, func_name)
            assert callable(func), \
                f"'{func_name}' in '{service}_support' is not callable"


def test_supported_services_is_list():
    """Test that SUPPORTED_SERVICES is a list"""
    assert isinstance(SUPPORTED_SERVICES, list), \
        "SUPPORTED_SERVICES must be a list"


def test_supported_services_not_empty():
    """Test that SUPPORTED_SERVICES is not empty"""
    assert len(SUPPORTED_SERVICES) > 0, \
        "SUPPORTED_SERVICES must contain at least one service"


def test_supported_services_no_duplicates():
    """Test that SUPPORTED_SERVICES has no duplicates"""
    assert len(SUPPORTED_SERVICES) == len(set(SUPPORTED_SERVICES)), \
        "SUPPORTED_SERVICES contains duplicate entries"


def test_supported_services_lowercase():
    """Test that all service names are lowercase"""
    for service in SUPPORTED_SERVICES:
        assert service == service.lower(), \
            f"Service name '{service}' must be lowercase"
