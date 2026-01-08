#!/usr/bin/env python3
"""
User Management System API Testing
Tests all user management APIs including setup, CRUD operations, and authorization
"""

import requests
import sys
import json
from datetime import datetime

class UserManagementAPITester:
    def __init__(self, base_url="https://order-central-11.preview.emergentagent.com"):
        self.base_url = base_url
        self.manager_token = None
        self.supervisor_token = None
        self.test_user_id = None
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
                response = requests.delete(url, headers=default_headers)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}, Expected: {expected_status}"
            
            if not success:
                try:
                    error_detail = response.json().get('detail', 'No detail')
                    details += f", Error: {error_detail}"
                except:
                    details += f", Response: {response.text[:200]}"

            self.log_test(name, success, details)
            return success, response.json() if response.content else {}

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

    def test_setup_check(self):
        """Test setup check API"""
        success, response = self.run_test(
            "Setup Check API",
            "GET",
            "setup/check",
            200
        )
        
        if success:
            setup_required = response.get('setup_required', True)
            if setup_required == False:
                print(f"   ✅ Setup not required (manager exists)")
                return True
            else:
                print(f"   ⚠️ Setup required: {setup_required}")
                return True
        return False

    def test_admin_users_list(self, token):
        """Test admin users list API"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Admin Users List API",
            "GET",
            "admin/users",
            200,
            headers=headers
        )
        
        if success and isinstance(response, list):
            print(f"   ✅ Found {len(response)} users in system")
            return True, response
        return False, []

    def test_create_user(self, token):
        """Test create user API"""
        headers = {'Authorization': f'Bearer {token}'}
        user_data = {
            "name": "مشرف اختبار",
            "email": "test_supervisor@test.com",
            "password": "123456",
            "role": "supervisor",
            "assigned_projects": [],
            "assigned_engineers": []
        }
        
        success, response = self.run_test(
            "Create User API",
            "POST",
            "admin/users",
            200,
            data=user_data,
            headers=headers
        )
        
        if success and response.get('user', {}).get('id'):
            self.test_user_id = response['user']['id']
            print(f"   ✅ Created user with ID: {self.test_user_id}")
            return True
        return False

    def test_update_user(self, token, user_id):
        """Test update user API"""
        headers = {'Authorization': f'Bearer {token}'}
        update_data = {
            "name": "مشرف اختبار محدث",
            "role": "supervisor"
        }
        
        success, response = self.run_test(
            "Update User API",
            "PUT",
            f"admin/users/{user_id}",
            200,
            data=update_data,
            headers=headers
        )
        return success

    def test_assign_projects_engineers(self, token, user_id):
        """Test assign projects and engineers"""
        headers = {'Authorization': f'Bearer {token}'}
        
        # First get available projects and engineers
        projects_success, projects_response = self.run_test(
            "Get Projects for Assignment",
            "GET",
            "projects",
            200,
            headers=headers
        )
        
        engineers_success, engineers_response = self.run_test(
            "Get Engineers for Assignment",
            "GET",
            "users/engineers",
            200,
            headers=headers
        )
        
        if projects_success and engineers_success:
            project_ids = [p['id'] for p in projects_response[:2]] if projects_response else []
            engineer_ids = [e['id'] for e in engineers_response[:1]] if engineers_response else []
            
            assign_data = {
                "assigned_projects": project_ids,
                "assigned_engineers": engineer_ids
            }
            
            success, response = self.run_test(
                "Assign Projects & Engineers",
                "PUT",
                f"admin/users/{user_id}",
                200,
                data=assign_data,
                headers=headers
            )
            
            if success:
                print(f"   ✅ Assigned {len(project_ids)} projects and {len(engineer_ids)} engineers")
            return success
        
        return False

    def test_reset_password(self, token, user_id):
        """Test reset password API"""
        headers = {'Authorization': f'Bearer {token}'}
        password_data = {
            "new_password": "newpass123"
        }
        
        success, response = self.run_test(
            "Reset Password API",
            "POST",
            f"admin/users/{user_id}/reset-password",
            200,
            data=password_data,
            headers=headers
        )
        return success

    def test_toggle_active(self, token, user_id):
        """Test toggle active API"""
        headers = {'Authorization': f'Bearer {token}'}
        
        success, response = self.run_test(
            "Toggle Active API",
            "PUT",
            f"admin/users/{user_id}/toggle-active",
            200,
            headers=headers
        )
        
        if success:
            is_active = response.get('is_active')
            print(f"   ✅ User active status: {is_active}")
            return True, is_active
        return False, None

    def test_disabled_user_login(self):
        """Test disabled user login"""
        success, response = self.run_test(
            "Disabled User Login Test",
            "POST",
            "auth/login",
            403,
            data={"email": "test_supervisor@test.com", "password": "newpass123"}
        )
        
        if success:
            error_detail = response.get('detail', '')
            if 'تم تعطيل حسابك' in error_detail or 'disabled' in error_detail.lower():
                print(f"   ✅ Correct error message for disabled user")
            else:
                print(f"   ⚠️ Disabled user rejected but error message may be different: {error_detail}")
            return True
        return False

    def test_authorization_supervisor(self):
        """Test authorization - supervisor accessing admin endpoints"""
        # First login as supervisor
        supervisor_token = self.test_login("supervisor1@test.com", "123456", "Supervisor (for auth test)")
        
        if not supervisor_token:
            print("   ❌ Failed to login as supervisor for authorization test")
            return False
        
        headers = {'Authorization': f'Bearer {supervisor_token}'}
        success, response = self.run_test(
            "Authorization Test - Supervisor Access",
            "GET",
            "admin/users",
            403,
            headers=headers
        )
        
        if success:
            print(f"   ✅ Supervisor correctly denied access to admin endpoints")
        return success

    def test_delete_user(self, token, user_id):
        """Test delete user API"""
        headers = {'Authorization': f'Bearer {token}'}
        
        success, response = self.run_test(
            "Delete User API",
            "DELETE",
            f"admin/users/{user_id}",
            200,
            headers=headers
        )
        return success

    def run_user_management_test(self):
        """Run complete user management system test"""
        print("\n👥 Starting User Management System Test...")
        print("=" * 60)
        
        # 1. Health check
        print("\n🏥 Testing Health Check...")
        if not self.test_health_check():
            print("❌ Health check failed, stopping tests")
            return False

        # 2. Test setup check API
        print("\n⚙️ Testing Setup Check API...")
        if not self.test_setup_check():
            print("❌ Setup check failed")
            return False

        # 3. Login as procurement manager
        print("\n🔑 Testing Manager Authentication...")
        self.manager_token = self.test_login("manager1@test.com", "123456", "Procurement Manager")
        
        if not self.manager_token:
            print("❌ Manager authentication failed")
            return False

        # 4. Test admin users list API
        print("\n📋 Testing Admin Users List API...")
        success, users_list = self.test_admin_users_list(self.manager_token)
        if not success:
            print("❌ Failed to get users list")
            return False

        # 5. Test create user API
        print("\n➕ Testing Create User API...")
        if not self.test_create_user(self.manager_token):
            print("❌ Failed to create user")
            return False

        # 6. Test update user API
        print("\n✏️ Testing Update User API...")
        if not self.test_update_user(self.manager_token, self.test_user_id):
            print("❌ Failed to update user")
            return False

        # 7. Test assign projects and engineers
        print("\n🔗 Testing Assign Projects & Engineers...")
        if not self.test_assign_projects_engineers(self.manager_token, self.test_user_id):
            print("❌ Failed to assign projects and engineers")
            return False

        # 8. Test reset password API
        print("\n🔐 Testing Reset Password API...")
        if not self.test_reset_password(self.manager_token, self.test_user_id):
            print("❌ Failed to reset password")
            return False

        # 9. Test toggle active API (disable user)
        print("\n🔄 Testing Toggle Active API (Disable)...")
        success, is_active = self.test_toggle_active(self.manager_token, self.test_user_id)
        if not success:
            print("❌ Failed to toggle user active status")
            return False

        # 10. Test disabled user login
        print("\n🚫 Testing Disabled User Login...")
        if not self.test_disabled_user_login():
            print("❌ Disabled user login test failed")
            return False

        # 11. Test authorization (supervisor trying to access admin endpoints)
        print("\n🛡️ Testing Authorization (Supervisor Access)...")
        if not self.test_authorization_supervisor():
            print("❌ Authorization test failed")
            return False

        # 12. Re-enable user for cleanup
        print("\n🔄 Re-enabling User for Cleanup...")
        self.test_toggle_active(self.manager_token, self.test_user_id)

        # 13. Test delete user API
        print("\n🗑️ Testing Delete User API...")
        if not self.test_delete_user(self.manager_token, self.test_user_id):
            print("❌ Failed to delete user")
            return False

        print("\n🎉 User Management System Test Completed!")
        return True

def main():
    print("🚀 Starting User Management System API Tests")
    print("=" * 70)
    
    tester = UserManagementAPITester()
    
    # Run user management test
    test_success = tester.run_user_management_test()
    
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
    else:
        print("\n✅ ALL TESTS PASSED!")
    
    # Return appropriate exit code
    return 0 if test_success and tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())