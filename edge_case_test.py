#!/usr/bin/env python3
"""
Additional Edge Case Testing for Critical Functionality
Testing specific scenarios mentioned in the Arabic review request
"""

import requests
import sys
import json

class EdgeCaseAPITester:
    def __init__(self, base_url="https://procure-hub-19.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        # Test credentials
        self.test_users = {
            "supervisor": {"email": "supervisor1@test.com", "password": "123456"},
            "engineer": {"email": "engineer1@test.com", "password": "123456"},
            "manager": {"email": "manager1@test.com", "password": "123456"},
            "general_manager": {"email": "gm1@test.com", "password": "123456"},
            "printer": {"email": "printer1@test.com", "password": "123456"},
            "delivery_tracker": {"email": "tracker1@test.com", "password": "123456"}
        }

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - FAILED: {details}")

    def make_request(self, method, endpoint, expected_status, data=None, headers=None, role=None):
        """Make API request with proper headers"""
        url = f"{self.base_url}/api/{endpoint}"
        default_headers = {'Content-Type': 'application/json'}
        
        if role and role in self.tokens:
            default_headers['Authorization'] = f'Bearer {self.tokens[role]}'
        
        if headers:
            default_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers, params=data)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=default_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=default_headers)

            success = response.status_code == expected_status
            
            if success:
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                try:
                    error_detail = response.json().get('detail', 'No detail')
                    return False, f"Status: {response.status_code}, Expected: {expected_status}, Error: {error_detail}"
                except:
                    return False, f"Status: {response.status_code}, Expected: {expected_status}, Response: {response.text[:100]}"

        except Exception as e:
            return False, f"Exception: {str(e)}"

    def login_all_users(self):
        """Login all users"""
        print("🔐 Logging in all users...")
        for role, credentials in self.test_users.items():
            success, response = self.make_request('POST', 'auth/login', 200, data=credentials)
            if success and 'access_token' in response:
                self.tokens[role] = response['access_token']
                print(f"✅ {role} logged in")
            else:
                print(f"❌ {role} login failed")
                return False
        return True

    def test_arabic_error_messages(self):
        """Test that error messages are in Arabic"""
        print("\n🌐 Testing Arabic Error Messages...")
        
        # Test wrong password
        success, response = self.make_request(
            'POST', 'auth/login', 401,
            data={"email": "supervisor1@test.com", "password": "wrongpassword"}
        )
        if success:
            # Check if error message contains Arabic
            error_msg = str(response)
            if "البريد الإلكتروني أو كلمة المرور غير صحيحة" in error_msg or "غير صحيحة" in error_msg:
                self.log_test("Arabic error message for wrong password", True, "Error message in Arabic")
            else:
                self.log_test("Arabic error message for wrong password", False, f"Error message: {error_msg}")
        
        # Test unauthorized access
        success, response = self.make_request('GET', 'admin/users', 403, role='supervisor')
        if success:
            error_msg = str(response)
            if "غير مصرح" in error_msg or "مصرح" in error_msg:
                self.log_test("Arabic error message for unauthorized access", True, "Error message in Arabic")
            else:
                self.log_test("Arabic error message for unauthorized access", False, f"Error message: {error_msg}")

    def test_role_based_permissions(self):
        """Test role-based access control thoroughly"""
        print("\n🔒 Testing Role-Based Permissions...")
        
        # Test supervisor cannot access admin functions
        success, response = self.make_request('GET', 'admin/users', 403, role='supervisor')
        self.log_test("Supervisor blocked from admin users", success, "Correctly denied access")
        
        # Test engineer cannot create projects
        project_data = {
            "name": "Test Project",
            "owner_name": "Test Owner",
            "description": "Test",
            "location": "Test Location"
        }
        success, response = self.make_request('POST', 'projects', 403, data=project_data, role='engineer')
        self.log_test("Engineer blocked from creating projects", success, "Correctly denied access")
        
        # Test printer can only access printing functions
        success, response = self.make_request('GET', 'purchase-orders', 200, role='printer')
        self.log_test("Printer can access purchase orders", success, "Printer has correct access")

    def test_workflow_integrity(self):
        """Test complete workflow integrity"""
        print("\n🔄 Testing Workflow Integrity...")
        
        # Get engineer ID
        success, engineers = self.make_request('GET', 'users/engineers', 200, role='supervisor')
        if not success or not engineers:
            self.log_test("Get engineers for workflow test", False, "No engineers found")
            return
        
        engineer_id = engineers[0].get('id')
        
        # Get or create project
        success, projects = self.make_request('GET', 'projects', 200, role='supervisor')
        project_id = None
        if success and projects:
            project_id = projects[0].get('id')
        
        if not project_id:
            # Create project
            project_data = {
                "name": "Workflow Test Project",
                "owner_name": "Test Owner",
                "description": "For workflow testing",
                "location": "Test Location"
            }
            success, response = self.make_request('POST', 'projects', 200, data=project_data, role='supervisor')
            if success:
                project_id = response.get('id')
        
        if not project_id:
            self.log_test("Create/Get project for workflow", False, "No project available")
            return
        
        # Create material request
        request_data = {
            "items": [
                {"name": "مواد اختبار التدفق", "quantity": 5, "unit": "قطعة"}
            ],
            "project_id": project_id,
            "engineer_id": engineer_id,
            "reason": "اختبار تدفق العمل"
        }
        
        success, response = self.make_request('POST', 'requests', 200, data=request_data, role='supervisor')
        if not success:
            self.log_test("Create request for workflow", False, str(response))
            return
        
        request_id = response.get('id')
        self.log_test("Create material request", True, f"Request ID: {request_id}")
        
        # Approve request
        success, response = self.make_request('PUT', f'requests/{request_id}/approve', 200, role='engineer')
        self.log_test("Approve request by engineer", success, str(response) if not success else "Request approved")
        
        if not success:
            return
        
        # Create purchase order
        po_data = {
            "request_id": request_id,
            "supplier_name": "مورد اختبار التدفق",
            "selected_items": [0],
            "notes": "أمر شراء لاختبار التدفق"
        }
        
        success, response = self.make_request('POST', 'purchase-orders', 200, data=po_data, role='manager')
        if not success:
            self.log_test("Create purchase order", False, str(response))
            return
        
        po_id = response.get('id')
        self.log_test("Create purchase order", True, f"PO ID: {po_id}")
        
        # Approve purchase order
        success, response = self.make_request('PUT', f'purchase-orders/{po_id}/approve', 200, role='manager')
        self.log_test("Approve purchase order", success, str(response) if not success else "PO approved")
        
        # Print purchase order
        if success:
            success, response = self.make_request('PUT', f'purchase-orders/{po_id}/print', 200, role='printer')
            self.log_test("Print purchase order", success, str(response) if not success else "PO printed")

    def test_data_validation(self):
        """Test data validation and edge cases"""
        print("\n✅ Testing Data Validation...")
        
        # Test creating user with invalid email
        invalid_user = {
            "name": "Test User",
            "email": "invalid-email",
            "password": "123456",
            "role": "supervisor"
        }
        success, response = self.make_request('POST', 'admin/users', 422, data=invalid_user, role='manager')
        self.log_test("Reject invalid email format", success, "Validation working correctly")
        
        # Test creating request with empty items
        success, engineers = self.make_request('GET', 'users/engineers', 200, role='supervisor')
        if success and engineers:
            engineer_id = engineers[0].get('id')
            success, projects = self.make_request('GET', 'projects', 200, role='supervisor')
            if success and projects:
                project_id = projects[0].get('id')
                
                empty_request = {
                    "items": [],
                    "project_id": project_id,
                    "engineer_id": engineer_id,
                    "reason": "Test empty items"
                }
                
                success, response = self.make_request('POST', 'requests', 422, data=empty_request, role='supervisor')
                self.log_test("Reject empty items in request", success, "Validation working correctly")

    def run_edge_case_tests(self):
        """Run all edge case tests"""
        print("🧪 Starting Edge Case Testing...")
        print("=" * 60)
        
        if not self.login_all_users():
            print("❌ Failed to login users, stopping tests")
            return False
        
        self.test_arabic_error_messages()
        self.test_role_based_permissions()
        self.test_workflow_integrity()
        self.test_data_validation()
        
        print("\n" + "=" * 60)
        print("📊 Edge Case Test Summary")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = EdgeCaseAPITester()
    success = tester.run_edge_case_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())