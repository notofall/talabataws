#!/usr/bin/env python3
"""
Frontend Delivery Tracker Testing
Tests the delivery tracker frontend functionality including login redirect and dashboard access
"""

import requests
import sys
import json
from datetime import datetime

class FrontendDeliveryTrackerTester:
    def __init__(self, base_url="https://postgres-migrate-7.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def test_frontend_accessibility(self):
        """Test that the frontend is accessible"""
        try:
            response = requests.get(self.base_url, timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            self.log_test("Frontend Accessibility", success, details)
            return success
        except Exception as e:
            self.log_test("Frontend Accessibility", False, f"Exception: {str(e)}")
            return False

    def test_login_page_accessibility(self):
        """Test that the login page is accessible"""
        try:
            response = requests.get(f"{self.base_url}/login", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            self.log_test("Login Page Accessibility", success, details)
            return success
        except Exception as e:
            self.log_test("Login Page Accessibility", False, f"Exception: {str(e)}")
            return False

    def test_register_page_accessibility(self):
        """Test that the register page is accessible"""
        try:
            response = requests.get(f"{self.base_url}/register", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            self.log_test("Register Page Accessibility", success, details)
            return success
        except Exception as e:
            self.log_test("Register Page Accessibility", False, f"Exception: {str(e)}")
            return False

    def test_delivery_tracker_dashboard_accessibility(self):
        """Test that the delivery tracker dashboard route exists (will redirect to login if not authenticated)"""
        try:
            response = requests.get(f"{self.base_url}/delivery-tracker", timeout=10, allow_redirects=False)
            # Should either return 200 (if authenticated) or redirect to login
            success = response.status_code in [200, 302, 301]
            details = f"Status: {response.status_code}"
            self.log_test("Delivery Tracker Dashboard Route", success, details)
            return success
        except Exception as e:
            self.log_test("Delivery Tracker Dashboard Route", False, f"Exception: {str(e)}")
            return False

    def test_api_login_with_delivery_tracker(self):
        """Test API login with delivery tracker credentials"""
        try:
            login_data = {
                "email": "tracker1@test.com",
                "password": "123456"
            }
            
            response = requests.post(f"{self.base_url}/api/auth/login", json=login_data, timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                user_role = data.get('user', {}).get('role', '')
                if user_role == 'delivery_tracker':
                    details = f"Login successful, role: {user_role}"
                else:
                    success = False
                    details = f"Wrong role returned: {user_role}, expected: delivery_tracker"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:100]}"
            
            self.log_test("API Login with Delivery Tracker", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("API Login with Delivery Tracker", False, f"Exception: {str(e)}")
            return False, {}

    def test_delivery_tracker_api_endpoints(self, token):
        """Test delivery tracker specific API endpoints"""
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        
        # Test stats endpoint
        try:
            response = requests.get(f"{self.base_url}/api/delivery-tracker/stats", headers=headers, timeout=10)
            success = response.status_code == 200
            details = f"Stats API - Status: {response.status_code}"
            if success:
                data = response.json()
                expected_fields = ['pending_delivery', 'shipped', 'partially_delivered', 'delivered', 'awaiting_shipment']
                missing_fields = [f for f in expected_fields if f not in data]
                if missing_fields:
                    success = False
                    details += f", Missing fields: {missing_fields}"
                else:
                    details += f", All fields present: {list(data.keys())}"
            self.log_test("Delivery Tracker Stats API", success, details)
        except Exception as e:
            self.log_test("Delivery Tracker Stats API", False, f"Exception: {str(e)}")
        
        # Test orders endpoint
        try:
            response = requests.get(f"{self.base_url}/api/delivery-tracker/orders", headers=headers, timeout=10)
            success = response.status_code == 200
            details = f"Orders API - Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Orders count: {len(data) if isinstance(data, list) else 'Not a list'}"
            self.log_test("Delivery Tracker Orders API", success, details)
        except Exception as e:
            self.log_test("Delivery Tracker Orders API", False, f"Exception: {str(e)}")

    def run_frontend_tests(self):
        """Run all frontend delivery tracker tests"""
        print("\n🌐 Starting Frontend Delivery Tracker Tests...")
        
        # Test basic accessibility
        print("\n📱 Testing Frontend Accessibility...")
        if not self.test_frontend_accessibility():
            print("❌ Frontend not accessible, stopping tests")
            return False
        
        # Test page accessibility
        print("\n📄 Testing Page Accessibility...")
        self.test_login_page_accessibility()
        self.test_register_page_accessibility()
        self.test_delivery_tracker_dashboard_accessibility()
        
        # Test API integration
        print("\n🔌 Testing API Integration...")
        login_success, login_data = self.test_api_login_with_delivery_tracker()
        
        if login_success and login_data.get('access_token'):
            token = login_data['access_token']
            print("\n📊 Testing Delivery Tracker API Endpoints...")
            self.test_delivery_tracker_api_endpoints(token)
        else:
            print("❌ Cannot test API endpoints without valid login")
        
        print("\n🎉 Frontend delivery tracker tests completed!")
        return True

def main():
    print("🚀 Starting Frontend Delivery Tracker Tests")
    print("=" * 70)
    
    tester = FrontendDeliveryTrackerTester()
    
    # Run frontend tests
    success = tester.run_frontend_tests()
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {tester.tests_run}")
    print(f"Passed: {tester.tests_passed}")
    print(f"Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "0%")
    
    # Print failed tests
    failed_tests = [t for t in tester.test_results if not t['success']]
    if failed_tests:
        print("\n❌ FAILED TESTS:")
        for test in failed_tests:
            print(f"  - {test['test']}: {test['details']}")
    
    # Return appropriate exit code
    return 0 if success and tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())