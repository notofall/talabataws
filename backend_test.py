#!/usr/bin/env python3
"""
Backend API Testing for Arabic RTL Material Request Management System
Tests all CRUD operations, authentication, and workflow
"""

import requests
import sys
import json
from datetime import datetime

class MaterialRequestAPITester:
    def __init__(self, base_url="https://mattrack-12.preview.emergentagent.com"):
        self.base_url = base_url
        self.supervisor_token = None
        self.engineer_token = None
        self.manager_token = None
        self.printer_token = None  # Added printer token
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

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
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
                    details += f", Response: {response.text[:100]}"

            self.log_test(name, success, details)
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health"""
        success, _ = self.run_test("Health Check", "GET", "health", 200)
        return success

    def test_login(self, email, password, role_name):
        """Test login and get token"""
        success, response = self.run_test(
            f"Login {role_name}",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        
        if success and 'access_token' in response:
            return response['access_token']
        return None

    def test_dashboard_stats(self, token, role_name):
        """Test dashboard stats endpoint"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Dashboard Stats - {role_name}",
            "GET",
            "dashboard/stats",
            200,
            headers=headers
        )
        return success

    def test_get_engineers(self, token):
        """Test getting engineers list"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Get Engineers List",
            "GET",
            "users/engineers",
            200,
            headers=headers
        )
        return success, response if success else []

    def test_create_material_request(self, token, engineer_id):
        """Test creating material request with multiple items"""
        headers = {'Authorization': f'Bearer {token}'}
        request_data = {
            "items": [
                {
                    "name": "حديد تسليح 12مم",
                    "quantity": 100,
                    "unit": "طن"
                },
                {
                    "name": "أسمنت بورتلاندي",
                    "quantity": 50,
                    "unit": "كيس"
                },
                {
                    "name": "رمل ناعم",
                    "quantity": 20,
                    "unit": "متر مكعب"
                }
            ],
            "project_name": "مشروع برج السلام",
            "reason": "مطلوب للأساسات والخرسانة",
            "engineer_id": engineer_id
        }
        
        success, response = self.run_test(
            "Create Material Request (Multi-Item)",
            "POST",
            "requests",
            200,
            data=request_data,
            headers=headers
        )
        return success, response.get('id') if success else None

    def test_get_requests(self, token, role_name):
        """Test getting requests"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Get Requests - {role_name}",
            "GET",
            "requests",
            200,
            headers=headers
        )
        return success, response if success else []

    def test_approve_request(self, token, request_id):
        """Test approving request"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Approve Request",
            "PUT",
            f"requests/{request_id}/approve",
            200,
            headers=headers
        )
        return success

    def test_create_purchase_order_with_selected_items(self, token, request_id, selected_items):
        """Test creating purchase order with selected items only"""
        headers = {'Authorization': f'Bearer {token}'}
        order_data = {
            "request_id": request_id,
            "supplier_name": "شركة الحديد الوطنية",
            "selected_items": selected_items,
            "notes": "تسليم خلال أسبوع"
        }
        
        success, response = self.run_test(
            f"Create Purchase Order with Selected Items {selected_items}",
            "POST",
            "purchase-orders",
            200,
            data=order_data,
            headers=headers
        )
        return success, response.get('id') if success else None

    def test_approve_purchase_order(self, token, order_id):
        """Test approving purchase order"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Approve Purchase Order",
            "PUT",
            f"purchase-orders/{order_id}/approve",
            200,
            headers=headers
        )
        return success

    def test_print_purchase_order(self, token, order_id):
        """Test marking purchase order as printed"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Mark Purchase Order as Printed",
            "PUT",
            f"purchase-orders/{order_id}/print",
            200,
            headers=headers
        )
        return success

    def test_get_remaining_items(self, token, request_id):
        """Test getting remaining items for a request"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Get Remaining Items",
            "GET",
            f"requests/{request_id}/remaining-items",
            200,
            headers=headers
        )
        return success, response if success else {}

    def test_create_purchase_order(self, token, request_id):
        """Test creating purchase order (legacy method - now creates with all items)"""
        headers = {'Authorization': f'Bearer {token}'}
        order_data = {
            "request_id": request_id,
            "supplier_name": "شركة الحديد الوطنية",
            "selected_items": [0, 1, 2],  # Select all items by default
            "notes": "تسليم خلال أسبوع"
        }
        
        success, response = self.run_test(
            "Create Purchase Order (All Items)",
            "POST",
            "purchase-orders",
            200,
            data=order_data,
            headers=headers
        )
        return success, response.get('id') if success else None

    def test_get_purchase_orders(self, token):
        """Test getting purchase orders"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Get Purchase Orders",
            "GET",
            "purchase-orders",
            200,
            headers=headers
        )
        return success

    def run_new_features_test(self):
        """Test new features: Multiple POs, Approval Workflow, Printer Role"""
        print("\n🆕 Starting New Features Test...")
        
        # 1. Health check
        if not self.test_health_check():
            print("❌ Health check failed, stopping tests")
            return False

        # 2. Login all users including printer
        print("\n📝 Testing Authentication (Including Printer)...")
        self.supervisor_token = self.test_login("supervisor1@test.com", "123456", "Supervisor")
        self.engineer_token = self.test_login("engineer1@test.com", "123456", "Engineer")
        self.manager_token = self.test_login("manager1@test.com", "123456", "Procurement Manager")
        self.printer_token = self.test_login("printer1@test.com", "123456", "Printer")

        if not all([self.supervisor_token, self.engineer_token, self.manager_token, self.printer_token]):
            print("❌ Authentication failed for one or more users")
            return False

        # 3. Get engineers list
        print("\n👥 Getting Engineer ID...")
        success, engineers = self.test_get_engineers(self.supervisor_token)
        if not success or not engineers:
            print("❌ Failed to get engineers list")
            return False

        engineer_id = None
        if isinstance(engineers, list) and len(engineers) > 0:
            engineer_id = engineers[0].get('id')

        if not engineer_id:
            print("❌ No engineer ID found")
            return False

        # 4. Create material request with multiple items
        print("\n📋 Creating Material Request with Multiple Items...")
        success, request_id = self.test_create_material_request(self.supervisor_token, engineer_id)
        if not success or not request_id:
            print("❌ Failed to create material request")
            return False

        # 5. Approve request
        print("\n✅ Approving Request...")
        if not self.test_approve_request(self.engineer_token, request_id):
            print("❌ Failed to approve request")
            return False

        # 6. Test remaining items endpoint
        print("\n📄 Testing Remaining Items Endpoint...")
        success, remaining_data = self.test_get_remaining_items(self.manager_token, request_id)
        if not success:
            print("❌ Failed to get remaining items")
            return False

        # 7. Create first PO with selected items (items 0 and 1)
        print("\n🛒 Creating First PO with Selected Items [0, 1]...")
        success, order_id_1 = self.test_create_purchase_order_with_selected_items(
            self.manager_token, request_id, [0, 1]
        )
        if not success or not order_id_1:
            print("❌ Failed to create first purchase order")
            return False

        # 8. Check remaining items after first PO
        print("\n📄 Checking Remaining Items After First PO...")
        success, remaining_data = self.test_get_remaining_items(self.manager_token, request_id)
        if success:
            remaining_items = remaining_data.get('remaining_items', [])
            print(f"   Remaining items count: {len(remaining_items)}")

        # 9. Create second PO with remaining item (item 2)
        print("\n🛒 Creating Second PO with Remaining Item [2]...")
        success, order_id_2 = self.test_create_purchase_order_with_selected_items(
            self.manager_token, request_id, [2]
        )
        if not success or not order_id_2:
            print("❌ Failed to create second purchase order")
            return False

        # 10. Test PO approval workflow
        print("\n✅ Testing PO Approval Workflow...")
        if not self.test_approve_purchase_order(self.manager_token, order_id_1):
            print("❌ Failed to approve first purchase order")
            return False

        if not self.test_approve_purchase_order(self.manager_token, order_id_2):
            print("❌ Failed to approve second purchase order")
            return False

        # 11. Test printer role - get POs
        print("\n🖨️ Testing Printer Role - Get Approved POs...")
        success = self.test_get_purchase_orders(self.printer_token)
        if not success:
            print("❌ Printer failed to get purchase orders")
            return False

        # 12. Test printer role - mark as printed
        print("\n🖨️ Testing Printer Role - Mark POs as Printed...")
        if not self.test_print_purchase_order(self.printer_token, order_id_1):
            print("❌ Failed to mark first PO as printed")
            return False

        if not self.test_print_purchase_order(self.printer_token, order_id_2):
            print("❌ Failed to mark second PO as printed")
            return False

        # 13. Test dashboard stats for all roles including printer
        print("\n📊 Testing Dashboard Stats for All Roles...")
        self.test_dashboard_stats(self.supervisor_token, "Supervisor")
        self.test_dashboard_stats(self.engineer_token, "Engineer")
        self.test_dashboard_stats(self.manager_token, "Procurement Manager")
        self.test_dashboard_stats(self.printer_token, "Printer")

        print("\n🎉 New features test completed!")
        return True

def main():
    print("🚀 Starting Arabic RTL Material Request Management System API Tests")
    print("=" * 70)
    
    tester = MaterialRequestAPITester()
    
    # Run new features test
    workflow_success = tester.run_new_features_test()
    
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
    return 0 if workflow_success and tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())