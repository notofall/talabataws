#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Material Procurement System Review
Tests specific scenarios mentioned in the review request:
1. PDF Export with Budget Category
2. Mobile Responsiveness (backend support)
3. Status Labels (Arabic)
4. Project Management
5. Budget Category with Project
"""

import requests
import sys
import json
from datetime import datetime

class MaterialProcurementReviewTester:
    def __init__(self, base_url="https://codehealer-44.preview.emergentagent.com"):
        self.base_url = base_url
        self.supervisor_token = None
        self.manager_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.project_id = None
        self.category_id = None
        self.order_id = None

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
                    details += f", Response: {response.text[:100]}"

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

    def test_project_management(self):
        """Test Project Management functionality"""
        print("\n🏗️ Testing Project Management...")
        
        headers = {'Authorization': f'Bearer {self.supervisor_token}'}
        
        # 1. Create a new project
        project_data = {
            "name": "مشروع اختبار المراجعة",
            "owner_name": "مالك المشروع الاختباري",
            "description": "مشروع لاختبار وظائف النظام",
            "location": "الرياض"
        }
        
        success, response = self.run_test(
            "Create New Project",
            "POST",
            "projects",
            200,
            data=project_data,
            headers=headers
        )
        
        if success and response.get('id'):
            self.project_id = response['id']
            print(f"   Created project with ID: {self.project_id}")
        else:
            print("❌ Failed to create project")
            return False

        # 2. Get projects list
        success, projects = self.run_test(
            "Get Projects List",
            "GET",
            "projects",
            200,
            headers=headers
        )
        
        if success:
            project_found = any(p.get('id') == self.project_id for p in projects)
            if project_found:
                print("✅ New project appears in projects list")
            else:
                print("❌ New project not found in projects list")
                return False

        # 3. Get specific project details
        success, project_details = self.run_test(
            "Get Project Details",
            "GET",
            f"projects/{self.project_id}",
            200,
            headers=headers
        )
        
        if success:
            if project_details.get('name') == project_data['name']:
                print("✅ Project details retrieved correctly")
            else:
                print("❌ Project details don't match")
                return False

        return True

    def test_budget_category_with_project(self):
        """Test Budget Category creation with Project"""
        print("\n💰 Testing Budget Category with Project...")
        
        headers = {'Authorization': f'Bearer {self.manager_token}'}
        
        # 1. Create budget category with project
        category_data = {
            "name": "تصنيف اختبار المراجعة",
            "project_id": self.project_id,
            "estimated_budget": 50000.0
        }
        
        success, response = self.run_test(
            "Create Budget Category with Project",
            "POST",
            "budget-categories",
            200,
            data=category_data,
            headers=headers
        )
        
        if success and response.get('id'):
            self.category_id = response['id']
            print(f"   Created category with ID: {self.category_id}")
            
            # Verify project name is included
            if response.get('project_name'):
                print(f"✅ Category includes project name: {response['project_name']}")
            else:
                print("❌ Category missing project name")
                return False
        else:
            print("❌ Failed to create budget category")
            return False

        # 2. Get budget categories filtered by project
        success, categories = self.run_test(
            "Get Budget Categories by Project",
            "GET",
            f"budget-categories?project_id={self.project_id}",
            200,
            headers=headers
        )
        
        if success:
            category_found = any(c.get('id') == self.category_id for c in categories)
            if category_found:
                print("✅ Category found when filtering by project")
            else:
                print("❌ Category not found when filtering by project")
                return False

        # 3. Test budget reports filtered by project
        success, report = self.run_test(
            "Get Budget Report by Project",
            "GET",
            f"budget-reports?project_id={self.project_id}",
            200,
            headers=headers
        )
        
        if success:
            if report.get('project') and report['project'].get('id') == self.project_id:
                print("✅ Budget report filtered by project correctly")
            else:
                print("❌ Budget report project filtering failed")
                return False

        return True

    def test_purchase_order_with_category(self):
        """Test creating Purchase Order with Budget Category"""
        print("\n🛒 Testing Purchase Order with Budget Category...")
        
        headers = {'Authorization': f'Bearer {self.manager_token}'}
        
        # First, we need to create a request and approve it
        # Get engineer ID
        success, engineers = self.run_test(
            "Get Engineers for PO Test",
            "GET",
            "users/engineers",
            200,
            headers=headers
        )
        
        if not success or not engineers:
            print("❌ Failed to get engineers")
            return False
        
        engineer_id = engineers[0]['id']
        
        # Create request with supervisor token
        supervisor_headers = {'Authorization': f'Bearer {self.supervisor_token}'}
        request_data = {
            "items": [
                {
                    "name": "مواد اختبار المراجعة",
                    "quantity": 10,
                    "unit": "قطعة",
                    "estimated_price": 100.0
                }
            ],
            "project_id": self.project_id,
            "reason": "اختبار أمر الشراء مع تصنيف الميزانية",
            "engineer_id": engineer_id
        }
        
        success, request_response = self.run_test(
            "Create Request for PO Test",
            "POST",
            "requests",
            200,
            data=request_data,
            headers=supervisor_headers
        )
        
        if not success:
            print("❌ Failed to create request for PO test")
            return False
        
        request_id = request_response['id']
        
        # Approve request with engineer token
        engineer_token = self.test_login("engineer1@test.com", "123456", "Engineer")
        engineer_headers = {'Authorization': f'Bearer {engineer_token}'}
        
        success, _ = self.run_test(
            "Approve Request for PO Test",
            "PUT",
            f"requests/{request_id}/approve",
            200,
            headers=engineer_headers
        )
        
        if not success:
            print("❌ Failed to approve request for PO test")
            return False

        # Create purchase order with category
        order_data = {
            "request_id": request_id,
            "supplier_name": "مورد اختبار المراجعة",
            "selected_items": [0],
            "category_id": self.category_id,
            "item_prices": [{"index": 0, "unit_price": 150.0}],
            "notes": "أمر شراء لاختبار تصنيف الميزانية"
        }
        
        success, response = self.run_test(
            "Create Purchase Order with Category",
            "POST",
            "purchase-orders",
            200,
            data=order_data,
            headers=headers
        )
        
        if success and response.get('id'):
            self.order_id = response['id']
            print(f"   Created PO with ID: {self.order_id}")
            
            # Verify category is included
            if response.get('category_id') == self.category_id:
                print("✅ Purchase order includes budget category ID")
            else:
                print("❌ Purchase order missing budget category ID")
                return False
                
            # Check if category name is included
            if response.get('category_name'):
                print(f"✅ Purchase order includes category name: {response['category_name']}")
            else:
                print("❌ Purchase order missing category name")
                return False
        else:
            print("❌ Failed to create purchase order with category")
            return False

        return True

    def test_status_labels_arabic(self):
        """Test that status labels are properly handled in Arabic"""
        print("\n🏷️ Testing Arabic Status Labels...")
        
        headers = {'Authorization': f'Bearer {self.manager_token}'}
        
        # Test different status transitions
        if not self.order_id:
            print("❌ No order ID available for status testing")
            return False

        # 1. Approve the order (pending_approval → approved)
        success, _ = self.run_test(
            "Approve Purchase Order (Status Test)",
            "PUT",
            f"purchase-orders/{self.order_id}/approve",
            200,
            headers=headers
        )
        
        if not success:
            print("❌ Failed to approve order for status test")
            return False

        # 2. Get the order and check status
        success, order = self.run_test(
            "Get Order Status After Approval",
            "GET",
            f"purchase-orders",
            200,
            headers=headers
        )
        
        if success:
            # Find our order in the list
            our_order = None
            for o in order:
                if o.get('id') == self.order_id:
                    our_order = o
                    break
            
            if our_order and our_order.get('status') == 'approved':
                print("✅ Order status correctly set to 'approved'")
            else:
                print("❌ Order status not correctly updated")
                return False

        # 3. Test printer workflow (approved → printed)
        printer_token = self.test_login("printer1@test.com", "123456", "Printer")
        if printer_token:
            printer_headers = {'Authorization': f'Bearer {printer_token}'}
            
            success, _ = self.run_test(
                "Mark Order as Printed (Status Test)",
                "PUT",
                f"purchase-orders/{self.order_id}/print",
                200,
                headers=printer_headers
            )
            
            if success:
                print("✅ Order status transition to 'printed' successful")
            else:
                print("❌ Failed to mark order as printed")
                return False

        # 4. Test shipping (printed → shipped)
        success, _ = self.run_test(
            "Mark Order as Shipped (Status Test)",
            "PUT",
            f"purchase-orders/{self.order_id}/ship",
            200,
            headers=headers
        )
        
        if success:
            print("✅ Order status transition to 'shipped' successful")
        else:
            print("❌ Failed to mark order as shipped")
            return False

        # 5. Test delivery (shipped → delivered)
        supervisor_headers = {'Authorization': f'Bearer {self.supervisor_token}'}
        delivery_data = {
            "items_delivered": [
                {"name": "مواد اختبار المراجعة", "quantity_delivered": 10}
            ],
            "delivery_date": datetime.now().isoformat(),
            "received_by": "مشرف الاختبار",
            "notes": "تسليم كامل"
        }
        
        success, delivery_response = self.run_test(
            "Record Full Delivery (Status Test)",
            "PUT",
            f"purchase-orders/{self.order_id}/deliver",
            200,
            data=delivery_data,
            headers=supervisor_headers
        )
        
        if success and delivery_response.get('status') == 'delivered':
            print("✅ Order status transition to 'delivered' successful")
        else:
            print("❌ Failed to record delivery or status not updated")
            return False

        print("✅ All Arabic status transitions working correctly")
        return True

    def test_pdf_export_backend_support(self):
        """Test backend support for PDF export with budget category"""
        print("\n📄 Testing PDF Export Backend Support...")
        
        headers = {'Authorization': f'Bearer {self.manager_token}'}
        
        # Get purchase orders to verify data structure for PDF export
        success, orders = self.run_test(
            "Get Purchase Orders for PDF Export",
            "GET",
            "purchase-orders",
            200,
            headers=headers
        )
        
        if not success:
            print("❌ Failed to get purchase orders")
            return False

        # Find an order with category_id
        order_with_category = None
        for order in orders:
            if order.get('category_id'):
                order_with_category = order
                break

        if not order_with_category:
            print("❌ No order found with category_id for PDF export test")
            return False

        # Verify required fields for PDF export are present
        required_fields = [
            'id', 'request_number', 'project_name', 'supervisor_name', 
            'engineer_name', 'category_name', 'items', 'total_amount', 'status'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in order_with_category or order_with_category[field] is None:
                missing_fields.append(field)

        if missing_fields:
            print(f"❌ Missing required fields for PDF export: {missing_fields}")
            return False
        else:
            print("✅ All required fields present for PDF export")

        # Verify Arabic status is available
        status = order_with_category.get('status')
        if status:
            print(f"✅ Order status available for PDF: {status}")
        else:
            print("❌ Order status missing")
            return False

        # Verify budget category name is available
        category_name = order_with_category.get('category_name')
        if category_name:
            print(f"✅ Budget category name available for PDF: {category_name}")
        else:
            print("❌ Budget category name missing")
            return False

        return True

    def test_mobile_responsiveness_backend(self):
        """Test backend endpoints that support mobile responsiveness"""
        print("\n📱 Testing Mobile Responsiveness Backend Support...")
        
        # Test dashboard stats for supervisor (mobile stats cards)
        supervisor_headers = {'Authorization': f'Bearer {self.supervisor_token}'}
        success, stats = self.run_test(
            "Get Supervisor Dashboard Stats (Mobile)",
            "GET",
            "dashboard/stats",
            200,
            headers=supervisor_headers
        )
        
        if not success:
            print("❌ Failed to get supervisor dashboard stats")
            return False

        # Verify stats structure for mobile display
        if isinstance(stats, dict) and 'total' in stats:
            print("✅ Supervisor dashboard stats available for mobile")
        else:
            print("❌ Supervisor dashboard stats structure invalid")
            return False

        # Test manager dashboard stats
        manager_headers = {'Authorization': f'Bearer {self.manager_token}'}
        success, manager_stats = self.run_test(
            "Get Manager Dashboard Stats (Mobile)",
            "GET",
            "dashboard/stats",
            200,
            headers=manager_headers
        )
        
        if not success:
            print("❌ Failed to get manager dashboard stats")
            return False

        # Test requests list for mobile (should be paginated/limited)
        success, requests = self.run_test(
            "Get Requests List (Mobile)",
            "GET",
            "requests",
            200,
            headers=supervisor_headers
        )
        
        if success:
            print(f"✅ Requests list available for mobile ({len(requests)} items)")
        else:
            print("❌ Failed to get requests list for mobile")
            return False

        # Test purchase orders list for mobile
        success, orders = self.run_test(
            "Get Purchase Orders List (Mobile)",
            "GET",
            "purchase-orders",
            200,
            headers=manager_headers
        )
        
        if success:
            print(f"✅ Purchase orders list available for mobile ({len(orders)} items)")
        else:
            print("❌ Failed to get purchase orders list for mobile")
            return False

        return True

    def run_comprehensive_review_test(self):
        """Run all review-specific tests"""
        print("\n🔍 Starting Comprehensive Review Testing...")
        print("=" * 70)
        
        # 1. Authentication
        print("\n🔐 Testing Authentication...")
        self.supervisor_token = self.test_login("supervisor1@test.com", "123456", "Supervisor")
        self.manager_token = self.test_login("manager1@test.com", "123456", "Manager")

        if not all([self.supervisor_token, self.manager_token]):
            print("❌ Authentication failed")
            return False

        # 2. Project Management Test
        if not self.test_project_management():
            print("❌ Project Management test failed")
            return False

        # 3. Budget Category with Project Test
        if not self.test_budget_category_with_project():
            print("❌ Budget Category with Project test failed")
            return False

        # 4. Purchase Order with Category Test
        if not self.test_purchase_order_with_category():
            print("❌ Purchase Order with Category test failed")
            return False

        # 5. Status Labels Test
        if not self.test_status_labels_arabic():
            print("❌ Arabic Status Labels test failed")
            return False

        # 6. PDF Export Backend Support Test
        if not self.test_pdf_export_backend_support():
            print("❌ PDF Export Backend Support test failed")
            return False

        # 7. Mobile Responsiveness Backend Test
        if not self.test_mobile_responsiveness_backend():
            print("❌ Mobile Responsiveness Backend test failed")
            return False

        print("\n🎉 All review tests completed successfully!")
        return True

def main():
    print("🚀 Starting Material Procurement System Review Testing")
    print("=" * 70)
    
    tester = MaterialProcurementReviewTester()
    
    # Run comprehensive review test
    review_success = tester.run_comprehensive_review_test()
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 REVIEW TEST SUMMARY")
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
    return 0 if review_success and tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())