#!/usr/bin/env python3
"""
Specific Backend API Tests for Review Request Scenarios
Tests the exact flows mentioned in the review request
"""

import requests
import json

class SpecificAPITester:
    def __init__(self, base_url="https://mattrack-12.preview.emergentagent.com"):
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

    def test_api_call(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Test a specific API call"""
        url = f"{self.base_url}/api/{endpoint}"
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=default_headers)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}, Expected: {expected_status}"
            
            if not success:
                try:
                    error_detail = response.json().get('detail', 'No detail')
                    details += f", Error: {error_detail}"
                except:
                    details += f", Response: {response.text[:200]}"

            self.log_test(name, success, details)
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_specific_scenarios(self):
        """Test the specific scenarios from the review request"""
        print("🎯 Testing Specific Review Request Scenarios")
        print("=" * 60)
        
        # Test 1: Login as supervisor
        print("\n1️⃣ Testing Supervisor Login (supervisor1@test.com / 123456)")
        success, response = self.test_api_call(
            "Supervisor Login",
            "POST",
            "auth/login",
            200,
            data={"email": "supervisor1@test.com", "password": "123456"}
        )
        
        if not success:
            print("❌ Cannot proceed without supervisor login")
            return False
            
        supervisor_token = response.get('access_token')
        supervisor_headers = {'Authorization': f'Bearer {supervisor_token}'}
        
        # Test 2: Get engineers for the supervisor
        print("\n2️⃣ Getting Engineers List for Supervisor")
        success, engineers = self.test_api_call(
            "Get Engineers for Supervisor",
            "GET",
            "users/engineers",
            200,
            headers=supervisor_headers
        )
        
        if not success or not engineers:
            print("❌ Cannot get engineers list")
            return False
            
        engineer_id = engineers[0]['id'] if engineers else None
        if not engineer_id:
            print("❌ No engineer found")
            return False
            
        # Test 3: Create new material request with multiple items
        print("\n3️⃣ Creating Material Request with Multiple Items")
        multi_item_request = {
            "items": [
                {
                    "name": "حديد تسليح 16مم",
                    "quantity": 200,
                    "unit": "طن"
                },
                {
                    "name": "أسمنت مقاوم",
                    "quantity": 100,
                    "unit": "كيس"
                },
                {
                    "name": "رمل خشن",
                    "quantity": 30,
                    "unit": "متر مكعب"
                },
                {
                    "name": "حصى مدرج",
                    "quantity": 25,
                    "unit": "متر مكعب"
                }
            ],
            "project_name": "مشروع المجمع التجاري الجديد",
            "reason": "مطلوب لصب الأساسات والأعمدة في المرحلة الأولى",
            "engineer_id": engineer_id
        }
        
        success, request_response = self.test_api_call(
            "Create Multi-Item Material Request",
            "POST",
            "requests",
            200,
            data=multi_item_request,
            headers=supervisor_headers
        )
        
        if not success:
            print("❌ Failed to create material request")
            return False
            
        request_id = request_response.get('id')
        
        # Test 4: Login as engineer
        print("\n4️⃣ Testing Engineer Login (engineer1@test.com / 123456)")
        success, response = self.test_api_call(
            "Engineer Login",
            "POST",
            "auth/login",
            200,
            data={"email": "engineer1@test.com", "password": "123456"}
        )
        
        if not success:
            print("❌ Engineer login failed")
            return False
            
        engineer_token = response.get('access_token')
        engineer_headers = {'Authorization': f'Bearer {engineer_token}'}
        
        # Test 5: Engineer approves the request
        print("\n5️⃣ Engineer Approving the Request")
        success, _ = self.test_api_call(
            "Engineer Approve Request",
            "PUT",
            f"requests/{request_id}/approve",
            200,
            headers=engineer_headers
        )
        
        if not success:
            print("❌ Failed to approve request")
            return False
            
        # Test 6: Login as procurement manager
        print("\n6️⃣ Testing Procurement Manager Login (manager1@test.com / 123456)")
        success, response = self.test_api_call(
            "Procurement Manager Login",
            "POST",
            "auth/login",
            200,
            data={"email": "manager1@test.com", "password": "123456"}
        )
        
        if not success:
            print("❌ Procurement manager login failed")
            return False
            
        manager_token = response.get('access_token')
        manager_headers = {'Authorization': f'Bearer {manager_token}'}
        
        # Test 7: Create purchase order
        print("\n7️⃣ Creating Purchase Order")
        purchase_order_data = {
            "request_id": request_id,
            "supplier_name": "شركة مواد البناء المتقدمة",
            "notes": "تسليم على دفعتين - الحديد أولاً ثم باقي المواد خلال أسبوع"
        }
        
        success, po_response = self.test_api_call(
            "Create Purchase Order",
            "POST",
            "purchase-orders",
            200,
            data=purchase_order_data,
            headers=manager_headers
        )
        
        if not success:
            print("❌ Failed to create purchase order")
            return False
            
        # Test 8: Verify all API endpoints mentioned in review request
        print("\n8️⃣ Testing All Specified API Endpoints")
        
        # Test GET /api/requests
        self.test_api_call(
            "GET /api/requests",
            "GET",
            "requests",
            200,
            headers=supervisor_headers
        )
        
        # Test GET /api/purchase-orders
        self.test_api_call(
            "GET /api/purchase-orders",
            "GET",
            "purchase-orders",
            200,
            headers=manager_headers
        )
        
        print("\n🎉 All specific scenarios completed successfully!")
        return True

def main():
    print("🚀 Starting Specific Backend API Tests for Review Request")
    print("=" * 70)
    
    tester = SpecificAPITester()
    
    # Run specific scenario tests
    scenario_success = tester.test_specific_scenarios()
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 SPECIFIC TEST SUMMARY")
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
    else:
        print("\n✅ ALL TESTS PASSED!")
    
    return 0 if scenario_success and tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    exit(main())