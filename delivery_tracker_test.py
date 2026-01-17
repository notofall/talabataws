#!/usr/bin/env python3
"""
Delivery Tracker Role Testing for Material Request Management System
Tests the new delivery_tracker role functionality including:
- Registration and login
- Delivery tracker APIs (stats, orders, confirm receipt)
- Authorization tests
"""

import requests
import sys
import json
from datetime import datetime

class DeliveryTrackerTester:
    def __init__(self, base_url="https://procure-hub-19.preview.emergentagent.com"):
        self.base_url = base_url
        self.tracker_token = None
        self.manager_token = None
        self.supervisor_token = None
        self.engineer_token = None
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

    def test_register_delivery_tracker(self):
        """Test registering a new delivery tracker user"""
        register_data = {
            "name": "متتبع التوريد الجديد",
            "email": "tracker_new@test.com",
            "password": "123456",
            "role": "delivery_tracker"
        }
        
        success, response = self.run_test(
            "Register Delivery Tracker",
            "POST",
            "auth/register",
            200,
            data=register_data
        )
        
        if success and response.get('user', {}).get('role') == 'delivery_tracker':
            print(f"   ✅ Registered delivery tracker with role: {response['user']['role']}")
            return True
        return False

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
            user_role = response.get('user', {}).get('role', '')
            print(f"   ✅ Login successful, role: {user_role}")
            return response['access_token']
        return None

    def test_delivery_tracker_stats(self, token):
        """Test delivery tracker stats API"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Delivery Tracker Stats API",
            "GET",
            "delivery-tracker/stats",
            200,
            headers=headers
        )
        
        if success:
            expected_fields = ['pending_delivery', 'shipped', 'partially_delivered', 'delivered', 'awaiting_shipment']
            for field in expected_fields:
                if field not in response:
                    print(f"   ❌ Missing field in stats: {field}")
                    return False
            print(f"   ✅ Stats response contains all expected fields: {list(response.keys())}")
        
        return success

    def test_delivery_tracker_orders(self, token):
        """Test delivery tracker orders API"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Delivery Tracker Orders API",
            "GET",
            "delivery-tracker/orders",
            200,
            headers=headers
        )
        
        if success:
            orders = response if isinstance(response, list) else []
            print(f"   ✅ Retrieved {len(orders)} orders for delivery tracking")
            
            # Check order structure if orders exist
            if orders:
                order = orders[0]
                expected_fields = ['id', 'project_name', 'supplier_name', 'total_amount', 'status']
                for field in expected_fields:
                    if field not in order:
                        print(f"   ❌ Missing field in order: {field}")
                        return False
                print(f"   ✅ Order structure contains expected fields")
        
        return success

    def test_confirm_receipt(self, token, order_id):
        """Test confirm receipt API"""
        headers = {'Authorization': f'Bearer {token}'}
        receipt_data = {
            "supplier_receipt_number": "REC-123456",
            "delivery_notes": "Test delivery notes",
            "items_delivered": [
                {"name": "حديد تسليح 12مم", "quantity_delivered": 50}
            ]
        }
        
        success, response = self.run_test(
            f"Confirm Receipt for Order {order_id}",
            "PUT",
            f"delivery-tracker/orders/{order_id}/confirm-receipt",
            200,
            data=receipt_data,
            headers=headers
        )
        
        return success

    def test_authorization_restrictions(self):
        """Test that other roles cannot access delivery tracker endpoints"""
        print("\n🔒 Testing Authorization Restrictions...")
        
        # Test supervisor cannot access delivery tracker orders
        if self.supervisor_token:
            headers = {'Authorization': f'Bearer {self.supervisor_token}'}
            success, response = self.run_test(
                "Supervisor Access to Delivery Tracker Orders (Should Fail)",
                "GET",
                "delivery-tracker/orders",
                403,
                headers=headers
            )
            if success:
                print("   ✅ Supervisor correctly denied access to delivery tracker orders")
        
        # Test engineer cannot access delivery tracker stats
        if self.engineer_token:
            headers = {'Authorization': f'Bearer {self.engineer_token}'}
            success, response = self.run_test(
                "Engineer Access to Delivery Tracker Stats (Should Fail)",
                "GET",
                "delivery-tracker/stats",
                403,
                headers=headers
            )
            if success:
                print("   ✅ Engineer correctly denied access to delivery tracker stats")

    def setup_test_data(self):
        """Setup test data by creating orders that can be tracked"""
        print("\n📋 Setting up test data...")
        
        # Login as manager to create test orders
        self.manager_token = self.test_login("manager1@test.com", "123456", "Manager")
        self.supervisor_token = self.test_login("supervisor1@test.com", "123456", "Supervisor")
        engineer_token = self.test_login("engineer1@test.com", "123456", "Engineer")
        
        if not all([self.manager_token, self.supervisor_token, engineer_token]):
            print("❌ Failed to login required users for test setup")
            return False
        
        # Get engineers list
        headers = {'Authorization': f'Bearer {self.supervisor_token}'}
        success, response = self.run_test(
            "Get Engineers for Test Setup",
            "GET",
            "users/engineers",
            200,
            headers=headers
        )
        
        if not success or not response:
            print("❌ Failed to get engineers list")
            return False
        
        engineer_id = response[0]['id'] if response else None
        if not engineer_id:
            print("❌ No engineer found")
            return False
        
        # Create project
        project_data = {
            "name": "مشروع اختبار التتبع",
            "owner_name": "مالك المشروع",
            "description": "مشروع لاختبار تتبع التوريد",
            "location": "الرياض"
        }
        
        success, project_response = self.run_test(
            "Create Test Project",
            "POST",
            "projects",
            200,
            data=project_data,
            headers=headers
        )
        
        if not success:
            print("❌ Failed to create test project")
            return False
        
        project_id = project_response.get('id')
        
        # Create material request
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
                }
            ],
            "project_id": project_id,
            "reason": "مطلوب لاختبار التتبع",
            "engineer_id": engineer_id
        }
        
        success, request_response = self.run_test(
            "Create Test Material Request",
            "POST",
            "requests",
            200,
            data=request_data,
            headers=headers
        )
        
        if not success:
            print("❌ Failed to create test request")
            return False
        
        request_id = request_response.get('id')
        
        # Approve request as engineer
        engineer_headers = {'Authorization': f'Bearer {engineer_token}'}
        success, _ = self.run_test(
            "Approve Test Request",
            "PUT",
            f"requests/{request_id}/approve",
            200,
            headers=engineer_headers
        )
        
        if not success:
            print("❌ Failed to approve test request")
            return False
        
        # Create purchase order as manager
        manager_headers = {'Authorization': f'Bearer {self.manager_token}'}
        order_data = {
            "request_id": request_id,
            "supplier_name": "شركة التوريد للاختبار",
            "selected_items": [0, 1],
            "notes": "أمر شراء للاختبار"
        }
        
        success, order_response = self.run_test(
            "Create Test Purchase Order",
            "POST",
            "purchase-orders",
            200,
            data=order_data,
            headers=manager_headers
        )
        
        if not success:
            print("❌ Failed to create test purchase order")
            return False
        
        order_id = order_response.get('id')
        
        # Approve and print the order
        success, _ = self.run_test(
            "Approve Test Purchase Order",
            "PUT",
            f"purchase-orders/{order_id}/approve",
            200,
            headers=manager_headers
        )
        
        if not success:
            print("❌ Failed to approve test purchase order")
            return False
        
        # Login as printer and print the order
        printer_token = self.test_login("printer1@test.com", "123456", "Printer")
        if printer_token:
            printer_headers = {'Authorization': f'Bearer {printer_token}'}
            success, _ = self.run_test(
                "Print Test Purchase Order",
                "PUT",
                f"purchase-orders/{order_id}/print",
                200,
                headers=printer_headers
            )
            
            if not success:
                print("❌ Failed to print test purchase order")
                return False
        
        # Ship the order
        success, _ = self.run_test(
            "Ship Test Purchase Order",
            "PUT",
            f"purchase-orders/{order_id}/ship",
            200,
            headers=manager_headers
        )
        
        if not success:
            print("❌ Failed to ship test purchase order")
            return False
        
        print(f"✅ Test data setup complete. Order ID: {order_id}")
        return order_id

    def run_delivery_tracker_tests(self):
        """Run comprehensive delivery tracker tests"""
        print("\n🚚 Starting Delivery Tracker Role Tests...")
        
        # 1. Test registration
        print("\n📝 Testing Delivery Tracker Registration...")
        if not self.test_register_delivery_tracker():
            print("❌ Delivery tracker registration failed")
            return False
        
        # 2. Test login with existing tracker credentials
        print("\n🔑 Testing Delivery Tracker Login...")
        self.tracker_token = self.test_login("tracker1@test.com", "123456", "Delivery Tracker")
        if not self.tracker_token:
            print("❌ Delivery tracker login failed")
            return False
        
        # 3. Setup test data (create orders to track)
        test_order_id = self.setup_test_data()
        if not test_order_id:
            print("❌ Failed to setup test data")
            return False
        
        # 4. Test delivery tracker stats API
        print("\n📊 Testing Delivery Tracker Stats API...")
        if not self.test_delivery_tracker_stats(self.tracker_token):
            print("❌ Delivery tracker stats API failed")
            return False
        
        # 5. Test delivery tracker orders API
        print("\n📋 Testing Delivery Tracker Orders API...")
        if not self.test_delivery_tracker_orders(self.tracker_token):
            print("❌ Delivery tracker orders API failed")
            return False
        
        # 6. Test confirm receipt API
        print("\n📦 Testing Confirm Receipt API...")
        if not self.test_confirm_receipt(self.tracker_token, test_order_id):
            print("❌ Confirm receipt API failed")
            return False
        
        # 7. Test authorization restrictions
        self.test_authorization_restrictions()
        
        print("\n🎉 Delivery tracker tests completed!")
        return True

def main():
    print("🚀 Starting Delivery Tracker Role Tests")
    print("=" * 70)
    
    tester = DeliveryTrackerTester()
    
    # Run delivery tracker tests
    success = tester.run_delivery_tracker_tests()
    
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