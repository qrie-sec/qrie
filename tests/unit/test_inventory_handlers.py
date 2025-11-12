"""
Unit tests for inventory handler validation.
Ensures all supported services have valid inventory generators.
"""
import pytest
from common_utils import SUPPORTED_SERVICES


class TestInventoryHandlers:
    """Test that all supported services have valid inventory handlers"""
    
    def test_all_supported_services_have_handlers(self):
        """Verify every service in SUPPORTED_SERVICES has a valid handler"""
        # Import inside test to use conftest.py path setup
        import sys
        import os
        
        # Add inventory_generator to path
        lambda_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'lambda')
        inventory_gen_dir = os.path.join(lambda_dir, 'inventory_generator')
        sys.path.insert(0, inventory_gen_dir)
        
        # Verify each service has a handler module
        for service in SUPPORTED_SERVICES:
            if service == 's3':
                from s3_inventory import generate_s3_inventory
                assert generate_s3_inventory is not None, f"s3_inventory module missing for service: {service}"
            elif service == 'ec2':
                from ec2_inventory import generate_ec2_inventory
                assert generate_ec2_inventory is not None, f"ec2_inventory module missing for service: {service}"
            elif service == 'iam':
                from iam_inventory import generate_iam_inventory
                assert generate_iam_inventory is not None, f"iam_inventory module missing for service: {service}"
            else:
                pytest.fail(f"Service {service} in SUPPORTED_SERVICES but no handler module found")
    
    def test_unsupported_service_raises_error(self):
        """Verify that unsupported services raise ValueError"""
        import sys
        import os
        
        # Add inventory_generator to path
        lambda_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'lambda')
        inventory_gen_dir = os.path.join(lambda_dir, 'inventory_generator')
        sys.path.insert(0, inventory_gen_dir)
        
        from inventory_handler import generate_inventory_for_account_service
        
        test_account = "123456789012"
        unsupported_service = "rds"  # Not in SUPPORTED_SERVICES
        
        with pytest.raises(ValueError, match="Unsupported service"):
            generate_inventory_for_account_service(test_account, unsupported_service)
    
    def test_supported_services_list_is_not_empty(self):
        """Verify SUPPORTED_SERVICES is not empty"""
        assert len(SUPPORTED_SERVICES) > 0, "SUPPORTED_SERVICES should not be empty"
    
    def test_supported_services_are_lowercase(self):
        """Verify all services in SUPPORTED_SERVICES are lowercase"""
        for service in SUPPORTED_SERVICES:
            assert service == service.lower(), f"Service {service} should be lowercase"
    
    def test_no_duplicate_services(self):
        """Verify no duplicate services in SUPPORTED_SERVICES"""
        assert len(SUPPORTED_SERVICES) == len(set(SUPPORTED_SERVICES)), \
            "SUPPORTED_SERVICES contains duplicates"
