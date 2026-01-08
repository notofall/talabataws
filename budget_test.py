#!/usr/bin/env python3
"""
Budget Management API Testing for Material Procurement System
Tests budget categories CRUD, budget reports, and PO integration with categories
"""

import requests
import sys
import json
from datetime import datetime

class BudgetManagementTester:
    def __init__(self, base_url="https://ordermanager-18.preview.emergentagent.com"):
        self.base_url = base_url
        self.manager_token = None
        self.supervisor_token = None
        self.engineer_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.created_category_id = None
        self.created_request_id = None
        self.created_order_id = None

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
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

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

    def test_create_budget_category(self, token, category_data, expected_status=200):
        """Test creating budget category"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Create Budget Category - {category_data['name']}",
            "POST",
            "budget-categories",
            expected_status,
            data=category_data,
            headers=headers
        )
        return success, response.get('id') if success else None

    def test_get_budget_categories(self, token, project_name=None):
        """Test getting budget categories"""
        headers = {'Authorization': f'Bearer {token}'}
        endpoint = "budget-categories"
        if project_name:
            endpoint += f"?project_name={project_name}"
        
        success, response = self.run_test(
            f"Get Budget Categories{' for ' + project_name if project_name else ''}",
            "GET",
            endpoint,
            200,
            headers=headers
        )
        return success, response if success else []

    def test_update_budget_category(self, token, category_id, update_data, expected_status=200):
        """Test updating budget category"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Update Budget Category {category_id}",
            "PUT",
            f"budget-categories/{category_id}",
            expected_status,
            data=update_data,
            headers=headers
        )
        return success

    def test_delete_budget_category(self, token, category_id, expected_status=200):
        """Test deleting budget category"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Delete Budget Category {category_id}",
            "DELETE",
            f"budget-categories/{category_id}",
            expected_status,
            headers=headers
        )
        return success

    def test_budget_reports(self, token, project_name=None):
        """Test budget reports endpoint"""
        headers = {'Authorization': f'Bearer {token}'}
        endpoint = "budget-reports"
        if project_name:
            endpoint += f"?project_name={project_name}"
        
        success, response = self.run_test(
            f"Get Budget Reports{' for ' + project_name if project_name else ''}",
            "GET",
            endpoint,
            200,
            headers=headers
        )
        return success, response if success else {}

    def test_create_material_request(self, token, engineer_id):
        """Test creating material request"""
        headers = {'Authorization': f'Bearer {token}'}
        request_data = {
            "items": [
                {
                    "name": "حديد تسليح 16مم",
                    "quantity": 50,
                    "unit": "طن"
                },
                {
                    "name": "أسمنت مقاوم",
                    "quantity": 100,
                    "unit": "كيس"
                }
            ],
            "project_name": "مشروع برج السلام",
            "reason": "مطلوب للأساسات",
            "engineer_id": engineer_id
        }
        
        success, response = self.run_test(
            "Create Material Request for Budget Test",
            "POST",
            "requests",
            200,
            data=request_data,
            headers=headers
        )
        return success, response.get('id') if success else None

    def test_approve_request(self, token, request_id):
        """Test approving request"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Approve Request for Budget Test",
            "PUT",
            f"requests/{request_id}/approve",
            200,
            headers=headers
        )
        return success

    def test_create_purchase_order_with_category(self, token, request_id, category_id, item_prices=None):
        """Test creating purchase order with budget category"""
        headers = {'Authorization': f'Bearer {token}'}
        order_data = {
            "request_id": request_id,
            "supplier_name": "شركة المواد الإنشائية",
            "selected_items": [0, 1],
            "category_id": category_id,
            "notes": "أمر شراء مع تصنيف ميزانية"
        }
        
        if item_prices:
            order_data["item_prices"] = item_prices
        
        success, response = self.run_test(
            f"Create Purchase Order with Category {category_id}",
            "POST",
            "purchase-orders",
            200,
            data=order_data,
            headers=headers
        )
        return success, response.get('id') if success else None

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

    def run_budget_management_test(self):
        """Test complete budget management workflow"""
        print("\n💰 Starting Budget Management Test...")
        
        # 1. Login users
        print("\n📝 Testing Authentication...")
        self.manager_token = self.test_login("manager1@test.com", "123456", "Manager")
        self.supervisor_token = self.test_login("supervisor1@test.com", "123456", "Supervisor")
        self.engineer_token = self.test_login("engineer1@test.com", "123456", "Engineer")

        if not all([self.manager_token, self.supervisor_token, self.engineer_token]):
            print("❌ Authentication failed for one or more users")
            return False

        # 2. Test authorization - only manager can create categories
        print("\n🔒 Testing Authorization...")
        
        # Test supervisor trying to create category (should fail)
        category_data = {
            "name": "اختبار التفويض",
            "project_name": "مشروع برج السلام",
            "estimated_budget": 10000
        }
        
        success, _ = self.test_create_budget_category(
            self.supervisor_token, category_data, expected_status=403
        )
        if success:
            print("✅ Correctly denied supervisor access to create budget category")
        else:
            print("❌ Should have denied supervisor access")

        # 3. Test creating budget category as manager
        print("\n💰 Testing Budget Category Creation...")
        
        test_category_data = {
            "name": "اختبار",
            "project_name": "مشروع برج السلام", 
            "estimated_budget": 25000
        }
        
        success, category_id = self.test_create_budget_category(
            self.manager_token, test_category_data
        )
        if not success or not category_id:
            print("❌ Failed to create budget category")
            return False
        
        self.created_category_id = category_id
        print(f"   Created category ID: {category_id}")

        # 4. Test validation - missing fields should fail
        print("\n⚠️ Testing Validation...")
        
        invalid_category_data = {
            "name": "فئة غير مكتملة"
            # Missing project_name and estimated_budget
        }
        
        success, _ = self.test_create_budget_category(
            self.manager_token, invalid_category_data, expected_status=422
        )
        if success:
            print("✅ Correctly rejected incomplete category data")
        else:
            print("❌ Should have rejected incomplete category data")

        # 5. Test getting budget categories
        print("\n📋 Testing Get Budget Categories...")
        
        success, categories = self.test_get_budget_categories(self.manager_token)
        if not success:
            print("❌ Failed to get budget categories")
            return False
        
        print(f"   Found {len(categories)} budget categories")
        
        # Verify our created category is in the list
        found_category = None
        for cat in categories:
            if cat.get('id') == category_id:
                found_category = cat
                break
        
        if found_category:
            print(f"✅ Found created category: {found_category['name']}")
            print(f"   Estimated budget: {found_category['estimated_budget']}")
            print(f"   Actual spent: {found_category.get('actual_spent', 0)}")
        else:
            print("❌ Created category not found in list")

        # 6. Test filtering by project name
        print("\n🔍 Testing Project Name Filter...")
        
        success, filtered_categories = self.test_get_budget_categories(
            self.manager_token, "مشروع برج السلام"
        )
        if success:
            print(f"   Found {len(filtered_categories)} categories for project")
        else:
            print("❌ Failed to filter categories by project")

        # 7. Test updating budget category
        print("\n✏️ Testing Budget Category Update...")
        
        update_data = {
            "name": "اختبار محدث",
            "estimated_budget": 30000
        }
        
        success = self.test_update_budget_category(
            self.manager_token, category_id, update_data
        )
        if not success:
            print("❌ Failed to update budget category")
            return False

        # 8. Test authorization for update (non-manager should fail)
        success = self.test_update_budget_category(
            self.supervisor_token, category_id, update_data, expected_status=403
        )
        if success:
            print("✅ Correctly denied supervisor access to update category")
        else:
            print("❌ Should have denied supervisor access to update")

        # 9. Create material request and PO to test budget integration
        print("\n🛒 Testing Budget Integration with Purchase Orders...")
        
        # Get engineer ID
        success, engineers = self.test_get_engineers(self.supervisor_token)
        if not success or not engineers:
            print("❌ Failed to get engineers list")
            return False
        
        engineer_id = engineers[0].get('id')
        
        # Create material request
        success, request_id = self.test_create_material_request(self.supervisor_token, engineer_id)
        if not success or not request_id:
            print("❌ Failed to create material request")
            return False
        
        self.created_request_id = request_id
        
        # Approve request
        success = self.test_approve_request(self.engineer_token, request_id)
        if not success:
            print("❌ Failed to approve request")
            return False

        # Create PO with category and prices
        item_prices = [
            {"index": 0, "unit_price": 200},  # حديد تسليح 16مم - 50 طن × 200 = 10,000
            {"index": 1, "unit_price": 50}    # أسمنت مقاوم - 100 كيس × 50 = 5,000
        ]
        
        success, order_id = self.test_create_purchase_order_with_category(
            self.manager_token, request_id, category_id, item_prices
        )
        if not success or not order_id:
            print("❌ Failed to create purchase order with category")
            return False
        
        self.created_order_id = order_id
        print(f"   Created PO with total amount: 15,000 (within budget of 30,000)")

        # 10. Test budget reports
        print("\n📊 Testing Budget Reports...")
        
        success, report = self.test_budget_reports(self.manager_token)
        if not success:
            print("❌ Failed to get budget reports")
            return False
        
        print(f"   Total estimated: {report.get('total_estimated', 0)}")
        print(f"   Total spent: {report.get('total_spent', 0)}")
        print(f"   Total remaining: {report.get('total_remaining', 0)}")
        print(f"   Categories count: {len(report.get('categories', []))}")
        print(f"   Over budget count: {len(report.get('over_budget', []))}")
        print(f"   Under budget count: {len(report.get('under_budget', []))}")

        # Verify our category appears in the report
        found_in_report = False
        for cat in report.get('categories', []):
            if cat.get('id') == category_id:
                found_in_report = True
                print(f"✅ Found category in report: {cat['name']}")
                print(f"   Status: {cat.get('status', 'unknown')}")
                print(f"   Actual spent: {cat.get('actual_spent', 0)}")
                break
        
        if not found_in_report:
            print("❌ Category not found in budget report")

        # 11. Test project-specific budget report
        success, project_report = self.test_budget_reports(
            self.manager_token, "مشروع برج السلام"
        )
        if success:
            print(f"   Project-specific report categories: {len(project_report.get('categories', []))}")
        else:
            print("❌ Failed to get project-specific budget report")

        # 12. Test deleting category with linked POs (should fail)
        print("\n🗑️ Testing Delete Category with Linked POs...")
        
        success = self.test_delete_budget_category(
            self.manager_token, category_id, expected_status=400
        )
        if success:
            print("✅ Correctly prevented deletion of category with linked POs")
        else:
            print("❌ Should have prevented deletion of category with linked POs")

        # 13. Create a new category for deletion test
        print("\n🗑️ Testing Delete Category without Linked POs...")
        
        delete_test_category = {
            "name": "فئة للحذف",
            "project_name": "مشروع اختبار",
            "estimated_budget": 5000
        }
        
        success, delete_category_id = self.test_create_budget_category(
            self.manager_token, delete_test_category
        )
        if success and delete_category_id:
            # Delete the category (should succeed)
            success = self.test_delete_budget_category(
                self.manager_token, delete_category_id
            )
            if success:
                print("✅ Successfully deleted category without linked POs")
            else:
                print("❌ Failed to delete category without linked POs")
        else:
            print("❌ Failed to create category for deletion test")

        # 14. Test authorization for delete (non-manager should fail)
        success = self.test_delete_budget_category(
            self.supervisor_token, category_id, expected_status=403
        )
        if success:
            print("✅ Correctly denied supervisor access to delete category")
        else:
            print("❌ Should have denied supervisor access to delete")

        print("\n🎉 Budget management test completed!")
        return True

def main():
    print("🚀 Starting Budget Management API Tests")
    print("=" * 70)
    
    tester = BudgetManagementTester()
    
    # Run budget management test
    budget_success = tester.run_budget_management_test()
    
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
    return 0 if budget_success and tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())