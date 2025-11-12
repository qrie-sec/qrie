#!/usr/bin/env python3
"""
API Testing Script for qrie APIs
Tests all endpoints with seed data
"""
import requests
import json
import sys
import time
from urllib.parse import urljoin

class APITester:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'qrie-api-tester/1.0'
        })
    
    def test_endpoint(self, endpoint, params=None, expected_status=200, method='GET', body=None):
        """Test a single endpoint"""
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        
        try:
            print(f"🔍 Testing: {method} {endpoint}")
            if params:
                print(f"   Params: {params}")
            if body:
                print(f"   Body: {json.dumps(body, indent=2)[:100]}...")
            
            if method == 'GET':
                response = self.session.get(url, params=params)
            elif method == 'POST':
                response = self.session.post(url, json=body, params=params)
            elif method == 'PUT':
                response = self.session.put(url, json=body, params=params)
            elif method == 'DELETE':
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == expected_status:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"   Result: Array with {len(data)} items")
                        if len(data) > 0:
                            print(f"   Sample: {json.dumps(data[0], indent=2)[:200]}...")
                    elif isinstance(data, dict):
                        print(f"   Result: Object with keys: {list(data.keys())}")
                        if 'findings' in data:
                            print(f"   Findings count: {len(data.get('findings', []))}")
                        elif 'resources' in data:
                            print(f"   Resources count: {len(data.get('resources', []))}")
                    else:
                        print(f"   Result: {str(data)[:100]}...")
                    
                    print("   ✅ SUCCESS")
                    return True, data
                    
                except json.JSONDecodeError:
                    print(f"   Response: {response.text[:200]}...")
                    print("   ✅ SUCCESS (non-JSON)")
                    return True, response.text
            else:
                print(f"   Error: {response.text}")
                print("   ❌ FAILED")
                return False, None
                
        except Exception as e:
            print(f"   Exception: {str(e)}")
            print("   ❌ FAILED")
            return False, None
        
        finally:
            print()
    
    def run_comprehensive_tests(self):
        """Run comprehensive API tests"""
        
        print("🚀 Starting comprehensive API tests...\n")
        
        tests = [
            # Basic endpoints
            ("accounts", None),
            ("services", None),
            ("services", {"supported": "true"}),
            
            # Resources endpoints
            ("resources", None),
            ("resources", {"page_size": "5"}),
            ("resources", {"account": "123456789012"}),
            ("resources", {"account": "123456789012", "page_size": "2"}),
            ("summary/resources", None),
            ("summary/resources", {"account": "123456789012"}),
            
            # Findings endpoints  
            ("findings", None),
            ("findings", {"page_size": "3"}),
            ("findings", {"state": "ACTIVE"}),
            ("findings", {"state": "RESOLVED"}),
            ("findings", {"account": "123456789012"}),
            ("findings", {"policy": "S3BucketPublic"}),
            ("findings", {"state": "ACTIVE", "account": "123456789012"}),
            ("summary/findings", None),
            ("summary/findings", {"account": "123456789012"}),
            
            # Policies endpoints (unified)
            ("policies", None),  # All policies
            ("policies", {"status": "all"}),
            ("policies", {"status": "active"}),
            ("policies", {"status": "available"}),
            ("policies", {"services": "s3"}),
            ("policies", {"services": "s3,ec2"}),
            ("policies", {"status": "active", "services": "s3"}),
            ("policies", {"status": "available", "services": "ec2"}),
            
            # Single policy lookup
            ("policies", {"policy_id": "S3BucketPublic"}),
            ("policies", {"policy_id": "S3BucketVersioningDisabled"}),
            ("policies", {"policy_id": "EC2UnencryptedEBS"}),
            ("policies", {"policy_id": "RDSPublicAccess"}),
            ("policies", {"policy_id": "NonExistentPolicy"}, 404),
            
            # Write operations (POST, PUT, DELETE)
            # Note: These will modify state, use with caution on production data
        ]
        
        # Add write operation tests (commented out by default for safety)
        write_tests = [
            # POST /policies (launch policy)
            ("policies", None, 201, "POST", {"policy_id": "TestPolicy", "scope": {"include_accounts": []}}),
            ("policies", None, 404, "POST", {"policy_id": "NonExistentPolicy"}),
            ("policies", None, 400, "POST", {}),  # Missing policy_id
            
            # PUT /policies/{id} (update policy) - requires existing launched policy
            ("policies/S3BucketPublic", None, 200, "PUT", {"severity": 95}),
            ("policies/S3BucketPublic", None, 200, "PUT", {"remediation": "Updated remediation"}),
            ("policies/NonExistentPolicy", None, 404, "PUT", {"severity": 95}),
            ("policies/S3BucketPublic", None, 400, "PUT", {}),  # No fields provided
            
            # DELETE /policies/{id} (delete policy)
            ("policies/TestPolicy", None, 200, "DELETE", None),
            ("policies/NonExistentPolicy", None, 404, "DELETE", None),
        ]
        
        # Uncomment to include write tests (WARNING: modifies state)
        # tests.extend(write_tests)
        
        passed = 0
        failed = 0
        
        for test in tests:
            endpoint = test[0]
            params = test[1] if len(test) > 1 else None
            expected_status = test[2] if len(test) > 2 else 200
            method = test[3] if len(test) > 3 else 'GET'
            body = test[4] if len(test) > 4 else None
            
            success, _ = self.test_endpoint(endpoint, params, expected_status, method, body)
            if success:
                passed += 1
            else:
                failed += 1
            
            time.sleep(0.1)  # Small delay between requests
        
        print(f"📊 Test Results:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
        
        return failed == 0

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test qrie API endpoints')
    parser.add_argument('base_url', help='Base URL of the API (e.g., https://abc123.execute-api.us-east-1.amazonaws.com)')
    parser.add_argument('--endpoint', help='Test specific endpoint only')
    parser.add_argument('--params', help='Query parameters as JSON string')
    
    args = parser.parse_args()
    
    tester = APITester(args.base_url)
    
    if args.endpoint:
        # Test single endpoint
        params = None
        if args.params:
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError:
                print("❌ Invalid JSON in --params")
                sys.exit(1)
        
        success, _ = tester.test_endpoint(args.endpoint, params)
        sys.exit(0 if success else 1)
    else:
        # Run comprehensive tests
        success = tester.run_comprehensive_tests()
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
