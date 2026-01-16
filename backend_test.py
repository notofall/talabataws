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
    def __init__(self, base_url="https://app-manager-20.preview.emergentagent.com"):
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
            elif method == 'DELETE':
                response = requests.delete(url, json=data, headers=default_headers)

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

    def test_create_material_request(self, token, engineer_id, project_id=None):
        """Test creating material request with multiple items"""
        headers = {'Authorization': f'Bearer {token}'}
        
        # If no project_id provided, create a project first
        if not project_id:
            project_data = {
                "name": "مشروع برج السلام",
                "owner_name": "مالك المشروع",
                "description": "مشروع اختبار",
                "location": "الرياض"
            }
            
            # Use supervisor token to create project (only supervisors can create projects)
            supervisor_headers = {'Authorization': f'Bearer {self.supervisor_token}'} if hasattr(self, 'supervisor_token') and self.supervisor_token else headers
            
            success, project_response = self.run_test(
                "Create Project for Request",
                "POST",
                "projects",
                200,
                data=project_data,
                headers=supervisor_headers
            )
            
            if success and project_response.get('id'):
                project_id = project_response['id']
            else:
                print("❌ Failed to create project for request")
                return False, None
        
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
            "project_id": project_id,
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

    # ==================== DELIVERY TRACKING TESTS ====================

    def test_ship_order(self, token, order_id, expected_status=200):
        """Test shipping a purchase order"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Ship Order {order_id}",
            "PUT",
            f"purchase-orders/{order_id}/ship",
            expected_status,
            headers=headers
        )
        return success

    def test_get_pending_delivery_orders(self, token, role_name):
        """Test getting orders pending delivery"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Get Pending Delivery Orders - {role_name}",
            "GET",
            "purchase-orders/pending-delivery",
            200,
            headers=headers
        )
        return success, response if success else []

    def test_deliver_order(self, token, order_id, delivery_data, expected_status=200):
        """Test recording delivery of items"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Deliver Order {order_id}",
            "PUT",
            f"purchase-orders/{order_id}/deliver",
            expected_status,
            data=delivery_data,
            headers=headers
        )
        return success, response if success else {}

    def test_get_delivery_records(self, token, order_id):
        """Test getting delivery records for an order"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Get Delivery Records for Order {order_id}",
            "GET",
            f"purchase-orders/{order_id}/deliveries",
            200,
            headers=headers
        )
        return success, response if success else []

    # ==================== PASSWORD MANAGEMENT TESTS ====================

    def test_change_password(self, token, current_password, new_password, expected_status=200, test_name="Change Password"):
        """Test changing password"""
        headers = {'Authorization': f'Bearer {token}'}
        password_data = {
            "current_password": current_password,
            "new_password": new_password
        }
        
        success, response = self.run_test(
            test_name,
            "POST",
            "auth/change-password",
            expected_status,
            data=password_data,
            headers=headers
        )
        return success, response if success else {}

    def test_forgot_password(self, email, expected_status=200, test_name="Forgot Password"):
        """Test forgot password functionality"""
        forgot_data = {"email": email}
        
        success, response = self.run_test(
            test_name,
            "POST",
            "auth/forgot-password",
            expected_status,
            data=forgot_data
        )
        return success, response if success else {}

    def run_password_management_test(self):
        """Test password management features: change password and forgot password"""
        print("\n🔐 Starting Password Management Test...")
        
        # 1. Health check
        if not self.test_health_check():
            print("❌ Health check failed, stopping tests")
            return False

        # 2. Login supervisor to test change password
        print("\n📝 Testing Authentication for Password Management...")
        self.supervisor_token = self.test_login("supervisor1@test.com", "123456", "Supervisor")
        
        if not self.supervisor_token:
            print("❌ Authentication failed for supervisor")
            return False

        # 3. Test Change Password - Valid Current Password
        print("\n🔄 Testing Change Password with Valid Current Password...")
        success, response = self.test_change_password(
            self.supervisor_token, 
            "123456", 
            "newpass123", 
            200, 
            "Change Password - Valid Current Password"
        )
        if not success:
            print("❌ Failed to change password with valid current password")
            return False

        # 4. Test login with new password
        print("\n🔑 Testing Login with New Password...")
        new_token = self.test_login("supervisor1@test.com", "newpass123", "Supervisor (New Password)")
        if not new_token:
            print("❌ Failed to login with new password")
            return False

        # 5. Test Change Password - Wrong Current Password
        print("\n❌ Testing Change Password with Wrong Current Password...")
        success, response = self.test_change_password(
            new_token, 
            "wrongpassword", 
            "anotherpass", 
            400, 
            "Change Password - Wrong Current Password"
        )
        if success:
            # Check if the error message is correct
            try:
                if "كلمة المرور الحالية غير صحيحة" in str(response):
                    print("✅ Correct error message for wrong current password")
                else:
                    print("⚠️ Wrong current password rejected but error message may be different")
            except:
                print("✅ Wrong current password correctly rejected")
        else:
            print("❌ Should have rejected wrong current password")

        # 6. Test Change Password - Short New Password
        print("\n📏 Testing Change Password with Short New Password...")
        success, response = self.test_change_password(
            new_token, 
            "newpass123", 
            "123", 
            400, 
            "Change Password - Short New Password"
        )
        if success:
            # Check if the error message is correct
            try:
                if "كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل" in str(response):
                    print("✅ Correct error message for short password")
                else:
                    print("⚠️ Short password rejected but error message may be different")
            except:
                print("✅ Short password correctly rejected")
        else:
            print("❌ Should have rejected short new password")

        # 7. Restore original password for future tests
        print("\n🔄 Restoring Original Password...")
        success, response = self.test_change_password(
            new_token, 
            "newpass123", 
            "123456", 
            200, 
            "Restore Original Password"
        )
        if not success:
            print("❌ Failed to restore original password")
            return False

        # 8. Test Forgot Password - Existing Email
        print("\n📧 Testing Forgot Password with Existing Email...")
        success, response = self.test_forgot_password(
            "supervisor1@test.com", 
            200, 
            "Forgot Password - Existing Email"
        )
        if not success:
            print("❌ Failed forgot password with existing email")
            return False

        # Check if temp_password is returned
        temp_password = None
        if isinstance(response, dict) and 'temp_password' in response:
            temp_password = response['temp_password']
            print(f"✅ Temporary password received: {temp_password}")
        else:
            print("⚠️ No temporary password in response (email might be configured)")

        # 9. Test login with temporary password if available
        if temp_password:
            print("\n🔑 Testing Login with Temporary Password...")
            temp_token = self.test_login("supervisor1@test.com", temp_password, "Supervisor (Temp Password)")
            if temp_token:
                print("✅ Successfully logged in with temporary password")
                
                # Restore original password
                print("\n🔄 Restoring Original Password after Temp Login...")
                self.test_change_password(
                    temp_token, 
                    temp_password, 
                    "123456", 
                    200, 
                    "Restore Password after Temp Login"
                )
            else:
                print("❌ Failed to login with temporary password")

        # 10. Test Forgot Password - Non-existing Email
        print("\n📧 Testing Forgot Password with Non-existing Email...")
        success, response = self.test_forgot_password(
            "nonexistent@test.com", 
            200, 
            "Forgot Password - Non-existing Email"
        )
        if success:
            print("✅ Forgot password with non-existing email handled correctly (returns success for security)")
        else:
            print("❌ Should return success even for non-existing email")

        # 11. Test engineer login to ensure other accounts work
        print("\n👷 Testing Engineer Login (Verify Other Accounts)...")
        engineer_token = self.test_login("engineer1@test.com", "123456", "Engineer (Verification)")
        if engineer_token:
            print("✅ Engineer login working correctly")
        else:
            print("❌ Engineer login failed")

        print("\n🎉 Password management test completed!")
        return True

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

    def test_delete_purchase_order(self, token, order_id, expected_status=200, test_name="Delete Purchase Order"):
        """Test deleting a purchase order"""
        headers = {'Authorization': f'Bearer {token}'}
        url = f"{self.base_url}/api/purchase-orders/{order_id}"
        
        try:
            response = requests.delete(url, headers=headers)
            success = response.status_code == expected_status
            details = f"Status: {response.status_code}, Expected: {expected_status}"
            
            if not success:
                try:
                    error_detail = response.json().get('detail', 'No detail')
                    details += f", Error: {error_detail}"
                except:
                    details += f", Response: {response.text[:100]}"

            self.log_test(test_name, success, details)
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            return False, {}

    def test_delete_material_request(self, token, request_id, expected_status=200, test_name="Delete Material Request"):
        """Test deleting a material request"""
        headers = {'Authorization': f'Bearer {token}'}
        url = f"{self.base_url}/api/requests/{request_id}"
        
        try:
            response = requests.delete(url, headers=headers)
            success = response.status_code == expected_status
            details = f"Status: {response.status_code}, Expected: {expected_status}"
            
            if not success:
                try:
                    error_detail = response.json().get('detail', 'No detail')
                    details += f", Error: {error_detail}"
                except:
                    details += f", Response: {response.text[:100]}"

            self.log_test(test_name, success, details)
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            return False, {}

    def test_clean_all_data(self, token, keep_user_email, expected_status=200, test_name="Clean All Data"):
        """Test cleaning all data except specified user"""
        headers = {'Authorization': f'Bearer {token}'}
        url = f"{self.base_url}/api/admin/clean-all-data?keep_user_email={keep_user_email}"
        
        try:
            response = requests.delete(url, headers=headers)
            success = response.status_code == expected_status
            details = f"Status: {response.status_code}, Expected: {expected_status}"
            
            if not success:
                try:
                    error_detail = response.json().get('detail', 'No detail')
                    details += f", Error: {error_detail}"
                except:
                    details += f", Response: {response.text[:100]}"

            self.log_test(test_name, success, details)
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            return False, {}

    def try_create_user(self, token, user_data, test_name="Try Create User"):
        """Try to create a user, don't fail if already exists"""
        headers = {'Authorization': f'Bearer {token}'}
        url = f"{self.base_url}/api/admin/users"
        
        try:
            response = requests.post(url, json=user_data, headers=headers)
            if response.status_code == 200:
                print(f"✅ {test_name} - CREATED")
                return True, response.json()
            elif response.status_code == 400 and "مسجل مسبقاً" in response.text:
                print(f"ℹ️ {test_name} - ALREADY EXISTS")
                return True, {}
            else:
                print(f"❌ {test_name} - FAILED: Status {response.status_code}")
                return False, {}
        except Exception as e:
            print(f"❌ {test_name} - EXCEPTION: {str(e)}")
            return False, {}

    def run_delete_apis_test(self):
        """Test DELETE APIs for purchase orders, requests, and clean-all-data"""
        print("\n🗑️ Starting DELETE APIs Test...")
        
        # 1. Health check
        if not self.test_health_check():
            print("❌ Health check failed, stopping tests")
            return False

        # 2. Login main user (PROCUREMENT_MANAGER)
        print("\n📝 Testing Authentication...")
        self.manager_token = self.test_login("notofall@gmail.com", "123456", "Procurement Manager")
        
        if not self.manager_token:
            print("❌ Authentication failed for procurement manager")
            return False

        # 3. Create test users for other roles or login if they exist
        print("\n👥 Creating/Login Test Users...")
        
        # Try to create supervisor, if exists just login
        supervisor_data = {
            "name": "مشرف اختبار",
            "email": "supervisor_test@test.com",
            "password": "123456",
            "role": "supervisor"
        }
        self.try_create_user(self.manager_token, supervisor_data, "Create Test Supervisor")
        self.supervisor_token = self.test_login("supervisor_test@test.com", "123456", "Test Supervisor")
        
        # Try to create engineer, if exists just login
        engineer_data = {
            "name": "مهندس اختبار",
            "email": "engineer_test@test.com", 
            "password": "123456",
            "role": "engineer"
        }
        self.try_create_user(self.manager_token, engineer_data, "Create Test Engineer")
        self.engineer_token = self.test_login("engineer_test@test.com", "123456", "Test Engineer")

        # 4. Create test data (request and purchase order)
        print("\n📋 Creating Test Data...")
        
        # Get engineers list
        success, engineers = self.test_get_engineers(self.manager_token)
        if not success or not engineers:
            print("❌ Failed to get engineers list")
            return False

        engineer_id = engineers[0].get('id') if engineers else None
        if not engineer_id:
            print("❌ No engineer ID found")
            return False

        # Create material request (supervisors create requests)
        success, request_id = self.test_create_material_request(self.supervisor_token, engineer_id)
        if not success or not request_id:
            print("❌ Failed to create material request for testing")
            return False

        # Approve request (need engineer token for this)
        if self.engineer_token:
            self.test_approve_request(self.engineer_token, request_id)
        else:
            # If no engineer token, approve with manager (might work in some systems)
            self.test_approve_request(self.manager_token, request_id)

        # Create purchase order
        success, order_id = self.test_create_purchase_order_with_selected_items(
            self.manager_token, request_id, [0, 1]
        )
        if not success or not order_id:
            print("❌ Failed to create purchase order for testing")
            return False

        # 5. Test DELETE /api/purchase-orders/{order_id} - Authorized (PROCUREMENT_MANAGER)
        print("\n🗑️ Testing DELETE Purchase Order - Authorized (PROCUREMENT_MANAGER)...")
        success, response = self.test_delete_purchase_order(
            self.manager_token, 
            order_id, 
            200, 
            "Delete Purchase Order - Authorized"
        )
        if not success:
            print("❌ Failed to delete purchase order as PROCUREMENT_MANAGER")
            return False

        # 6. Test DELETE /api/purchase-orders/{order_id} - Unauthorized (other role)
        print("\n🚫 Testing DELETE Purchase Order - Unauthorized (Supervisor)...")
        
        # Create another purchase order for unauthorized test
        success, request_id2 = self.test_create_material_request(self.supervisor_token, engineer_id)
        if success and request_id2:
            if self.engineer_token:
                self.test_approve_request(self.engineer_token, request_id2)
            else:
                self.test_approve_request(self.manager_token, request_id2)
            
            success, order_id2 = self.test_create_purchase_order_with_selected_items(
                self.manager_token, request_id2, [0]
            )
            
            if success and order_id2:
                # Try to delete with supervisor token (should fail with 403)
                if self.supervisor_token:
                    success, response = self.test_delete_purchase_order(
                        self.supervisor_token, 
                        order_id2, 
                        403, 
                        "Delete Purchase Order - Unauthorized (Supervisor)"
                    )
                    if success:
                        print("✅ Correctly rejected unauthorized purchase order deletion")
                    else:
                        print("❌ Should have rejected unauthorized purchase order deletion")
                else:
                    print("⚠️ No supervisor token available for unauthorized test")

        # 7. Test DELETE /api/requests/{request_id} - Authorized (PROCUREMENT_MANAGER)
        print("\n🗑️ Testing DELETE Material Request - Authorized (PROCUREMENT_MANAGER)...")
        
        # Create a new request for deletion test
        success, request_id3 = self.test_create_material_request(self.supervisor_token, engineer_id)
        if success and request_id3:
            # Create a purchase order for this request to test cascade deletion
            if self.engineer_token:
                self.test_approve_request(self.engineer_token, request_id3)
            else:
                self.test_approve_request(self.manager_token, request_id3)
            
            success, order_id3 = self.test_create_purchase_order_with_selected_items(
                self.manager_token, request_id3, [0, 1]
            )
            
            # Now delete the request (should also delete related purchase orders)
            success, response = self.test_delete_material_request(
                self.manager_token, 
                request_id3, 
                200, 
                "Delete Material Request - Authorized"
            )
            if success:
                print("✅ Successfully deleted material request")
                if response.get('deleted_orders', 0) > 0:
                    print(f"✅ Correctly deleted {response['deleted_orders']} related purchase orders")
                else:
                    print("⚠️ No related purchase orders were deleted")
            else:
                print("❌ Failed to delete material request as PROCUREMENT_MANAGER")

        # 8. Test DELETE /api/requests/{request_id} - Unauthorized (other role)
        print("\n🚫 Testing DELETE Material Request - Unauthorized (Supervisor)...")
        
        # Create another request for unauthorized test
        success, request_id4 = self.test_create_material_request(self.supervisor_token, engineer_id)
        if success and request_id4 and self.supervisor_token:
            success, response = self.test_delete_material_request(
                self.supervisor_token, 
                request_id4, 
                403, 
                "Delete Material Request - Unauthorized (Supervisor)"
            )
            if success:
                print("✅ Correctly rejected unauthorized material request deletion")
            else:
                print("❌ Should have rejected unauthorized material request deletion")

        # 9. Test DELETE /api/admin/clean-all-data - Non-existent email (should 404)
        print("\n🚫 Testing Clean All Data - Non-existent Email...")
        success, response = self.test_clean_all_data(
            self.manager_token, 
            "nonexistent@example.com", 
            404, 
            "Clean All Data - Non-existent Email"
        )
        if success:
            print("✅ Correctly returned 404 for non-existent email")
        else:
            print("❌ Should have returned 404 for non-existent email")

        # 10. Test DELETE /api/admin/clean-all-data - Unauthorized (other role)
        print("\n🚫 Testing Clean All Data - Unauthorized (Supervisor)...")
        if self.supervisor_token:
            success, response = self.test_clean_all_data(
                self.supervisor_token, 
                "notofall@gmail.com", 
                403, 
                "Clean All Data - Unauthorized (Supervisor)"
            )
            if success:
                print("✅ Correctly rejected unauthorized clean-all-data request")
            else:
                print("❌ Should have rejected unauthorized clean-all-data request")

        # 11. Test DELETE /api/admin/clean-all-data - Valid (PROCUREMENT_MANAGER with existing email)
        print("\n🗑️ Testing Clean All Data - Valid (PROCUREMENT_MANAGER)...")
        success, response = self.test_clean_all_data(
            self.manager_token, 
            "notofall@gmail.com", 
            200, 
            "Clean All Data - Valid"
        )
        if success:
            print("✅ Successfully cleaned all data")
            if response.get('deleted'):
                deleted = response['deleted']
                print(f"   Deleted: {deleted.get('users', 0)} users, {deleted.get('requests', 0)} requests, {deleted.get('orders', 0)} orders")
            else:
                print("⚠️ No deletion counts in response")
        else:
            print("❌ Failed to clean all data as PROCUREMENT_MANAGER")

        print("\n🎉 DELETE APIs test completed!")
        return True

    def run_delivery_tracking_test(self):
        """Test complete delivery tracking workflow"""
        print("\n🚚 Starting Delivery Tracking Workflow Test...")
        
        # 1. Health check
        if not self.test_health_check():
            print("❌ Health check failed, stopping tests")
            return False

        # 2. Login all users
        print("\n📝 Testing Authentication...")
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

        # 4. Create material request
        print("\n📋 Creating Material Request...")
        success, request_id = self.test_create_material_request(self.supervisor_token, engineer_id)
        if not success or not request_id:
            print("❌ Failed to create material request")
            return False

        # 5. Approve request
        print("\n✅ Approving Request...")
        if not self.test_approve_request(self.engineer_token, request_id):
            print("❌ Failed to approve request")
            return False

        # 6. Create purchase order
        print("\n🛒 Creating Purchase Order...")
        success, order_id = self.test_create_purchase_order_with_selected_items(
            self.manager_token, request_id, [0, 1, 2]
        )
        if not success or not order_id:
            print("❌ Failed to create purchase order")
            return False

        # 7. Approve purchase order
        print("\n✅ Approving Purchase Order...")
        if not self.test_approve_purchase_order(self.manager_token, order_id):
            print("❌ Failed to approve purchase order")
            return False

        # 8. Print purchase order
        print("\n🖨️ Printing Purchase Order...")
        if not self.test_print_purchase_order(self.printer_token, order_id):
            print("❌ Failed to print purchase order")
            return False

        # 9. Test shipping workflow
        print("\n🚢 Testing Shipping Workflow...")
        
        # Test shipping a printed order (should succeed)
        if not self.test_ship_order(self.manager_token, order_id, 200):
            print("❌ Failed to ship printed order")
            return False

        # Test shipping an already shipped order (should fail)
        if self.test_ship_order(self.manager_token, order_id, 400):
            print("✅ Correctly prevented shipping already shipped order")
        else:
            print("❌ Should have prevented shipping already shipped order")

        # 10. Test pending delivery API
        print("\n📦 Testing Pending Delivery API...")
        
        # As supervisor, should see shipped orders
        success, pending_orders = self.test_get_pending_delivery_orders(self.supervisor_token, "Supervisor")
        if not success:
            print("❌ Failed to get pending deliveries as supervisor")
            return False
        
        print(f"   Supervisor sees {len(pending_orders)} pending delivery orders")

        # As manager, should return empty array (endpoint is for supervisor/engineer only)
        success, manager_orders = self.test_get_pending_delivery_orders(self.manager_token, "Manager")
        if success and len(manager_orders) == 0:
            print("✅ Manager correctly sees no pending deliveries (endpoint restricted)")
        else:
            print("❌ Manager should see empty array for pending deliveries")

        # 11. Test delivery workflow
        print("\n📥 Testing Delivery Workflow...")
        
        # Test partial delivery
        partial_delivery_data = {
            "items_delivered": [
                {"name": "حديد تسليح 12مم", "quantity_delivered": 50},
                {"name": "أسمنت بورتلاندي", "quantity_delivered": 25}
            ],
            "delivery_date": datetime.now().isoformat(),
            "received_by": "محمد المشرف",
            "notes": "تسليم جزئي - الباقي غداً"
        }
        
        success, partial_response = self.test_deliver_order(
            self.supervisor_token, order_id, partial_delivery_data, 200
        )
        if not success:
            print("❌ Failed to record partial delivery")
            return False
        
        if partial_response.get('status') == 'partially_delivered':
            print("✅ Partial delivery recorded correctly")
        else:
            print("❌ Partial delivery status not set correctly")

        # Test full delivery of remaining items
        full_delivery_data = {
            "items_delivered": [
                {"name": "حديد تسليح 12مم", "quantity_delivered": 50},
                {"name": "أسمنت بورتلاندي", "quantity_delivered": 25},
                {"name": "رمل ناعم", "quantity_delivered": 20}
            ],
            "delivery_date": datetime.now().isoformat(),
            "received_by": "محمد المشرف",
            "notes": "تسليم كامل"
        }
        
        success, full_response = self.test_deliver_order(
            self.supervisor_token, order_id, full_delivery_data, 200
        )
        if not success:
            print("❌ Failed to record full delivery")
            return False
        
        if full_response.get('status') == 'delivered':
            print("✅ Full delivery recorded correctly")
        else:
            print("❌ Full delivery status not set correctly")

        # 12. Test delivery records API
        print("\n📋 Testing Delivery Records API...")
        success, delivery_records = self.test_get_delivery_records(self.supervisor_token, order_id)
        if not success:
            print("❌ Failed to get delivery records")
            return False
        
        print(f"   Found {len(delivery_records)} delivery records")

        # 13. Test edge cases
        print("\n⚠️ Testing Edge Cases...")
        
        # Test delivery with invalid order_id
        invalid_delivery_data = {
            "items_delivered": [{"name": "test", "quantity_delivered": 1}],
            "delivery_date": datetime.now().isoformat(),
            "received_by": "Test User"
        }
        
        if self.test_deliver_order(self.supervisor_token, "invalid-id", invalid_delivery_data, 404):
            print("✅ Correctly handled invalid order_id")
        else:
            print("❌ Should have failed with invalid order_id")

        # Test delivery with 0 quantity
        zero_delivery_data = {
            "items_delivered": [{"name": "حديد تسليح 12مم", "quantity_delivered": 0}],
            "delivery_date": datetime.now().isoformat(),
            "received_by": "Test User"
        }
        
        # Create another request and order for this test
        print("\n🔄 Creating new request for edge case testing...")
        success, test_request_id = self.test_create_material_request(self.supervisor_token, engineer_id)
        if success and test_request_id:
            self.test_approve_request(self.engineer_token, test_request_id)
            success, test_order_id = self.test_create_purchase_order_with_selected_items(
                self.manager_token, test_request_id, [0]
            )
            if success and test_order_id:
                self.test_approve_purchase_order(self.manager_token, test_order_id)
                self.test_print_purchase_order(self.printer_token, test_order_id)
                self.test_ship_order(self.manager_token, test_order_id, 200)
                
                # This should work as the API doesn't explicitly prevent 0 quantity
                success, _ = self.test_deliver_order(self.supervisor_token, test_order_id, zero_delivery_data, 200)
                if success:
                    print("✅ Zero quantity delivery handled (API allows this)")
                else:
                    print("❌ Zero quantity delivery failed unexpectedly")

        # Test shipping workflow edge cases
        print("\n🚢 Testing Shipping Edge Cases...")
        
        # Create another order to test shipping a pending order
        success, pending_request_id = self.test_create_material_request(self.supervisor_token, engineer_id)
        if success and pending_request_id:
            self.test_approve_request(self.engineer_token, pending_request_id)
            success, pending_order_id = self.test_create_purchase_order_with_selected_items(
                self.manager_token, pending_request_id, [0]
            )
            if success and pending_order_id:
                # Try to ship a pending order (should fail - must be printed first)
                if self.test_ship_order(self.manager_token, pending_order_id, 400):
                    print("✅ Correctly prevented shipping pending order (must be printed first)")
                else:
                    print("❌ Should have prevented shipping pending order")

        print("\n🎉 Delivery tracking test completed!")
        return True

def main():
    print("🚀 Starting Arabic RTL Material Request Management System API Tests")
    print("=" * 70)
    
    tester = MaterialRequestAPITester()
    
    # Run DELETE APIs test (as requested in review)
    delete_success = tester.run_delete_apis_test()
    
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
    return 0 if delete_success and tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())