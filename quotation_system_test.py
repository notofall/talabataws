#!/usr/bin/env python3
"""
Quotation & Approval System Phase 1 Testing
Tests all new features: GM Role, System Settings, Price Catalog, Item Aliases, GM Approval Workflow
"""

import requests
import sys
import json
from datetime import datetime

class QuotationSystemTester:
    def __init__(self, base_url="https://ordermanager-18.preview.emergentagent.com"):
        self.base_url = base_url
        self.gm_token = None
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

    # ==================== GENERAL MANAGER ROLE TESTS ====================

    def test_gm_stats(self, token):
        """Test GM stats API"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "GM Stats API",
            "GET",
            "gm/stats",
            200,
            headers=headers
        )
        return success, response

    def test_gm_pending_approvals(self, token):
        """Test GM pending approvals API"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "GM Pending Approvals API",
            "GET",
            "gm/pending-approvals",
            200,
            headers=headers
        )
        return success, response

    def test_gm_approve_order(self, token, order_id):
        """Test GM approve order"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"GM Approve Order {order_id}",
            "PUT",
            f"gm/approve/{order_id}",
            200,
            headers=headers
        )
        return success, response

    def test_gm_reject_order(self, token, order_id):
        """Test GM reject order"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"GM Reject Order {order_id}",
            "PUT",
            f"gm/reject/{order_id}",
            200,
            headers=headers
        )
        return success, response

    # ==================== SYSTEM SETTINGS TESTS ====================

    def test_get_system_settings(self, token):
        """Test get system settings"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Get System Settings",
            "GET",
            "system-settings",
            200,
            headers=headers
        )
        return success, response

    def test_update_approval_limit(self, token, new_limit):
        """Test update approval limit"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Update Approval Limit to {new_limit}",
            "PUT",
            "system-settings/approval_limit",
            200,
            data={"value": str(new_limit)},
            headers=headers
        )
        return success, response

    # ==================== PRICE CATALOG TESTS ====================

    def test_get_price_catalog(self, token):
        """Test get price catalog"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Get Price Catalog",
            "GET",
            "price-catalog",
            200,
            headers=headers
        )
        return success, response

    def test_create_catalog_item(self, token, item_data):
        """Test create catalog item"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Create Catalog Item: {item_data['name']}",
            "POST",
            "price-catalog",
            200,
            data=item_data,
            headers=headers
        )
        return success, response

    def test_update_catalog_item(self, token, item_id, update_data):
        """Test update catalog item"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Update Catalog Item {item_id}",
            "PUT",
            f"price-catalog/{item_id}",
            200,
            data=update_data,
            headers=headers
        )
        return success, response

    def test_delete_catalog_item(self, token, item_id):
        """Test delete catalog item"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Delete Catalog Item {item_id}",
            "DELETE",
            f"price-catalog/{item_id}",
            200,
            headers=headers
        )
        return success, response

    # ==================== ITEM ALIASES TESTS ====================

    def test_get_item_aliases(self, token):
        """Test get item aliases"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Get Item Aliases",
            "GET",
            "item-aliases",
            200,
            headers=headers
        )
        return success, response

    def test_create_item_alias(self, token, alias_data):
        """Test create item alias"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Create Item Alias: {alias_data['alias_name']}",
            "POST",
            "item-aliases",
            200,
            data=alias_data,
            headers=headers
        )
        return success, response

    def test_suggest_item(self, token, item_name):
        """Test item suggestion API"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Suggest Item for: {item_name}",
            "GET",
            f"item-aliases/suggest/{item_name}",
            200,
            headers=headers
        )
        return success, response

    def test_delete_item_alias(self, token, alias_id):
        """Test delete item alias"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Delete Item Alias {alias_id}",
            "DELETE",
            f"item-aliases/{alias_id}",
            200,
            headers=headers
        )
        return success, response

    # ==================== AUTHORIZATION TESTS ====================

    def test_unauthorized_access(self, token, endpoint, method="GET", expected_status=403):
        """Test unauthorized access to endpoints"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            f"Unauthorized Access Test: {endpoint}",
            method,
            endpoint,
            expected_status,
            headers=headers
        )
        return success

    # ==================== WORKFLOW TESTS ====================

    def create_high_value_po(self, token, amount=25000):
        """Create a high-value PO that requires GM approval"""
        headers = {'Authorization': f'Bearer {token}'}
        
        # First create a project as supervisor (only supervisors can create projects)
        project_data = {
            "name": "مشروع اختبار الموافقة العليا",
            "owner_name": "مالك المشروع",
            "description": "مشروع لاختبار موافقة المدير العام",
            "location": "الرياض"
        }
        
        success, project_response = self.run_test(
            "Create Project for High-Value PO",
            "POST",
            "projects",
            200,
            data=project_data,
            headers={'Authorization': f'Bearer {self.supervisor_token}'}
        )
        
        if not success:
            return False, None
        
        project_id = project_response.get('id')
        
        # Get engineer ID
        success, engineers = self.run_test(
            "Get Engineers for High-Value PO",
            "GET",
            "users/engineers",
            200,
            headers=headers
        )
        
        if not success or not engineers:
            return False, None
        
        engineer_id = engineers[0].get('id')
        
        # Create material request
        request_data = {
            "items": [
                {
                    "name": "معدات ثقيلة",
                    "quantity": 1,
                    "unit": "قطعة"
                }
            ],
            "project_id": project_id,
            "reason": "معدات للمشروع الكبير",
            "engineer_id": engineer_id
        }
        
        success, request_response = self.run_test(
            "Create Material Request for High-Value PO",
            "POST",
            "requests",
            200,
            data=request_data,
            headers={'Authorization': f'Bearer {self.supervisor_token}'}
        )
        
        if not success:
            return False, None
        
        request_id = request_response.get('id')
        
        # Approve request as engineer
        success, _ = self.run_test(
            "Approve Request for High-Value PO",
            "PUT",
            f"requests/{request_id}/approve",
            200,
            headers={'Authorization': f'Bearer {self.engineer_token}'}
        )
        
        if not success:
            return False, None
        
        # Create high-value purchase order
        po_data = {
            "request_id": request_id,
            "supplier_name": "شركة المعدات الثقيلة",
            "selected_items": [0],
            "item_prices": [{"index": 0, "unit_price": amount}],
            "notes": f"أمر شراء بقيمة {amount} ريال"
        }
        
        success, po_response = self.run_test(
            f"Create High-Value PO ({amount} SAR)",
            "POST",
            "purchase-orders",
            200,
            data=po_data,
            headers=headers
        )
        
        if success:
            return True, po_response.get('id')
        return False, None

    def run_quotation_system_test(self):
        """Run comprehensive quotation system tests"""
        print("\n🎯 Starting Quotation & Approval System Phase 1 Tests...")
        
        # 1. Health check
        if not self.test_health_check():
            print("❌ Health check failed, stopping tests")
            return False

        # 2. Login all users
        print("\n📝 Testing Authentication...")
        self.gm_token = self.test_login("gm1@test.com", "123456", "General Manager")
        self.manager_token = self.test_login("manager1@test.com", "123456", "Procurement Manager")
        self.supervisor_token = self.test_login("supervisor1@test.com", "123456", "Supervisor")
        self.engineer_token = self.test_login("engineer1@test.com", "123456", "Engineer")

        if not all([self.gm_token, self.manager_token, self.supervisor_token, self.engineer_token]):
            print("❌ Authentication failed for one or more users")
            return False

        # 3. Test General Manager Role
        print("\n👔 Testing General Manager Role...")
        
        # Test GM stats
        success, gm_stats = self.test_gm_stats(self.gm_token)
        if success:
            print(f"   GM Stats: {json.dumps(gm_stats, indent=2, ensure_ascii=False)}")
        
        # Test GM pending approvals
        success, pending_approvals = self.test_gm_pending_approvals(self.gm_token)
        if success:
            print(f"   Pending Approvals Count: {len(pending_approvals)}")

        # 4. Test System Settings APIs
        print("\n⚙️ Testing System Settings APIs...")
        
        # Get system settings
        success, settings = self.test_get_system_settings(self.manager_token)
        if success:
            print(f"   Found {len(settings)} system settings")
            # Check for required settings
            setting_keys = [s.get('key') for s in settings]
            required_keys = ['approval_limit', 'currency', 'auto_learn_aliases']
            for key in required_keys:
                if key in setting_keys:
                    print(f"   ✅ Found required setting: {key}")
                else:
                    print(f"   ❌ Missing required setting: {key}")
        
        # Test updating approval limit
        success, _ = self.test_update_approval_limit(self.manager_token, 25000)
        if success:
            print("   ✅ Successfully updated approval limit")
        
        # Test unauthorized access to system settings
        self.test_unauthorized_access(self.supervisor_token, "system-settings", "GET", 403)

        # 5. Test Price Catalog APIs
        print("\n📋 Testing Price Catalog APIs...")
        
        # Get price catalog
        success, catalog = self.test_get_price_catalog(self.manager_token)
        if success:
            print(f"   Current catalog has {len(catalog)} items")
        
        # Create new catalog item
        catalog_item_data = {
            "name": "حديد تسليح 16مم - كتالوج",
            "description": "حديد تسليح عالي الجودة",
            "unit": "طن",
            "supplier_name": "شركة الحديد المتطور",
            "price": 3500.0,
            "currency": "SAR"
        }
        
        success, new_item = self.test_create_catalog_item(self.manager_token, catalog_item_data)
        catalog_item_id = None
        if success:
            catalog_item_id = new_item.get('id')
            print(f"   ✅ Created catalog item with ID: {catalog_item_id}")
        
        # Update catalog item
        if catalog_item_id:
            update_data = {
                "price": 3600.0,
                "description": "حديد تسليح عالي الجودة - محدث"
            }
            success, _ = self.test_update_catalog_item(self.manager_token, catalog_item_id, update_data)
            if success:
                print("   ✅ Successfully updated catalog item")
        
        # Test unauthorized access to catalog management
        self.test_unauthorized_access(self.supervisor_token, "price-catalog", "POST", 403)
        self.test_unauthorized_access(self.engineer_token, "price-catalog", "PUT", 403)

        # 6. Test Item Aliases APIs
        print("\n🔗 Testing Item Aliases APIs...")
        
        # Get item aliases
        success, aliases = self.test_get_item_aliases(self.manager_token)
        if success:
            print(f"   Current aliases count: {len(aliases)}")
        
        # Create item alias (if we have a catalog item)
        alias_id = None
        if catalog_item_id:
            alias_data = {
                "alias_name": "حديد 16",
                "catalog_item_id": catalog_item_id
            }
            
            success, new_alias = self.test_create_item_alias(self.manager_token, alias_data)
            if success:
                alias_id = new_alias.get('id')
                print(f"   ✅ Created alias with ID: {alias_id}")
        
        # Test smart suggestion
        success, suggestions = self.test_suggest_item(self.manager_token, "حديد")
        if success:
            print(f"   Smart suggestion for 'حديد': {len(suggestions)} results")
        
        # Test suggestion with alias
        success, alias_suggestions = self.test_suggest_item(self.manager_token, "حديد 16")
        if success:
            print(f"   Smart suggestion for 'حديد 16': {len(alias_suggestions)} results")

        # 7. Test GM Approval Workflow
        print("\n🔄 Testing GM Approval Workflow...")
        
        # Create high-value PO that requires GM approval
        success, high_value_po_id = self.create_high_value_po(self.manager_token, 25000)
        if success and high_value_po_id:
            print(f"   ✅ Created high-value PO: {high_value_po_id}")
            
            # Check if PO status is pending_gm_approval
            success, po_details = self.run_test(
                "Check High-Value PO Status",
                "GET",
                f"purchase-orders/{high_value_po_id}",
                200,
                headers={'Authorization': f'Bearer {self.manager_token}'}
            )
            
            if success:
                po_status = po_details.get('status')
                if po_status == 'pending_gm_approval':
                    print("   ✅ High-value PO correctly set to pending_gm_approval")
                else:
                    print(f"   ❌ Expected pending_gm_approval, got: {po_status}")
            
            # Test GM approval
            success, _ = self.test_gm_approve_order(self.gm_token, high_value_po_id)
            if success:
                print("   ✅ GM successfully approved high-value PO")
        
        # Create another high-value PO for rejection test
        success, reject_po_id = self.create_high_value_po(self.manager_token, 30000)
        if success and reject_po_id:
            # Test GM rejection
            success, _ = self.test_gm_reject_order(self.gm_token, reject_po_id)
            if success:
                print("   ✅ GM successfully rejected high-value PO")

        # 8. Test Authorization
        print("\n🔒 Testing Authorization...")
        
        # Test supervisor cannot access GM endpoints
        self.test_unauthorized_access(self.supervisor_token, "gm/stats", "GET", 403)
        self.test_unauthorized_access(self.engineer_token, "gm/pending-approvals", "GET", 403)
        
        # Test only procurement manager can manage catalog
        if catalog_item_id:
            self.test_unauthorized_access(self.supervisor_token, f"price-catalog/{catalog_item_id}", "DELETE", 403)
            self.test_unauthorized_access(self.engineer_token, f"price-catalog/{catalog_item_id}", "PUT", 403)

        # 9. Cleanup - Delete test items
        print("\n🧹 Cleaning up test data...")
        if alias_id:
            success, _ = self.test_delete_item_alias(self.manager_token, alias_id)
            if success:
                print("   ✅ Deleted test alias")
        
        if catalog_item_id:
            success, _ = self.test_delete_catalog_item(self.manager_token, catalog_item_id)
            if success:
                print("   ✅ Deleted test catalog item")

        print("\n🎉 Quotation & Approval System Phase 1 tests completed!")
        return True

def main():
    print("🚀 Starting Quotation & Approval System Phase 1 Tests")
    print("=" * 70)
    
    tester = QuotationSystemTester()
    
    # Run quotation system tests
    quotation_success = tester.run_quotation_system_test()
    
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
    return 0 if quotation_success and tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())