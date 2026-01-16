#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Arabic Material Management System
Based on detailed review request - اختبار شامل ومفصل للنظام

Tests all authentication, user management, projects, suppliers, material requests,
purchase orders, GM dashboard, price catalog, reports, and backup functionality.
"""

import requests
import sys
import json
from datetime import datetime
import time

class ComprehensiveAPITester:
    def __init__(self, base_url="https://procure-id-system.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}  # Store tokens for all user roles
        self.test_data = {}  # Store created test data
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test credentials from review request
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
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

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

    # ==================== 1. نظام المصادقة (Authentication) ====================
    
    def test_authentication_system(self):
        """Test complete authentication system"""
        print("\n🔐 1. اختبار نظام المصادقة (Authentication System)")
        
        # 1.1 تسجيل الدخول لكل دور
        print("\n1.1 تسجيل الدخول لكل دور:")
        for role, credentials in self.test_users.items():
            success, response = self.make_request(
                'POST', 'auth/login', 200, 
                data=credentials
            )
            
            if success and 'access_token' in response:
                self.tokens[role] = response['access_token']
                user_data = response.get('user', {})
                self.log_test(f"تسجيل دخول {role}", True, 
                    f"Token received, User: {user_data.get('name', 'N/A')}, Role: {user_data.get('role', 'N/A')}")
            else:
                self.log_test(f"تسجيل دخول {role}", False, str(response))
        
        # 1.2 التسجيل المحمي (should return 403)
        print("\n1.2 التسجيل المحمي:")
        success, response = self.make_request(
            'POST', 'auth/register', 403,
            data={"name": "Test User", "email": "test@test.com", "password": "123456", "role": "supervisor"}
        )
        self.log_test("التسجيل المحمي يُرجع 403", success, str(response) if not success else "Registration correctly disabled")
        
        # 1.3 تغيير كلمة المرور
        print("\n1.3 تغيير كلمة المرور:")
        if 'supervisor' in self.tokens:
            success, response = self.make_request(
                'POST', 'auth/change-password', 200,
                data={"current_password": "123456", "new_password": "newpass123"},
                role='supervisor'
            )
            self.log_test("تغيير كلمة المرور", success, str(response) if not success else "Password changed successfully")
            
            # Restore original password
            if success:
                self.make_request(
                    'POST', 'auth/change-password', 200,
                    data={"current_password": "newpass123", "new_password": "123456"},
                    role='supervisor'
                )

    # ==================== 2. نظام إدارة المستخدمين (User Management) ====================
    
    def test_user_management_system(self):
        """Test complete user management system"""
        print("\n👥 2. اختبار نظام إدارة المستخدمين (User Management)")
        
        # 2.1 التحقق من الإعداد
        print("\n2.1 التحقق من الإعداد:")
        success, response = self.make_request('GET', 'setup/check', 200)
        setup_required = response.get('setup_required', True) if success else True
        self.log_test("فحص الإعداد", success, f"Setup required: {setup_required}")
        
        # 2.2 قائمة المستخدمين (كمدير مشتريات)
        print("\n2.2 قائمة المستخدمين:")
        success, response = self.make_request('GET', 'admin/users', 200, role='manager')
        users_count = len(response) if success and isinstance(response, list) else 0
        self.log_test("قائمة المستخدمين (مدير)", success, f"Found {users_count} users")
        
        # Test supervisor cannot access (should get 403)
        success, response = self.make_request('GET', 'admin/users', 403, role='supervisor')
        self.log_test("منع المشرف من الوصول لقائمة المستخدمين", success, "Correctly denied access")
        
        # 2.3 إنشاء مستخدم اختبار
        print("\n2.3 إنشاء مستخدم اختبار:")
        test_user_data = {
            "name": "مستخدم اختبار",
            "email": "test_user_check@test.com",
            "password": "test123",
            "role": "supervisor"
        }
        success, response = self.make_request('POST', 'admin/users', 200, data=test_user_data, role='manager')
        test_user_id = response.get('user', {}).get('id') if success else None
        self.test_data['test_user_id'] = test_user_id
        self.log_test("إنشاء مستخدم اختبار", success, f"User ID: {test_user_id}")
        
        if test_user_id:
            # 2.4 تحديث مستخدم
            print("\n2.4 تحديث مستخدم:")
            update_data = {"name": "مستخدم اختبار محدث"}
            success, response = self.make_request('PUT', f'admin/users/{test_user_id}', 200, data=update_data, role='manager')
            self.log_test("تحديث اسم المستخدم", success, str(response) if not success else "User updated successfully")
            
            # 2.5 إعادة تعيين كلمة المرور
            print("\n2.5 إعادة تعيين كلمة المرور:")
            reset_data = {"new_password": "newtest123"}
            success, response = self.make_request('POST', f'admin/users/{test_user_id}/reset-password', 200, data=reset_data, role='manager')
            self.log_test("إعادة تعيين كلمة المرور", success, str(response) if not success else "Password reset successfully")
            
            # 2.6 تعطيل/تفعيل المستخدم
            print("\n2.6 تعطيل/تفعيل المستخدم:")
            success, response = self.make_request('PUT', f'admin/users/{test_user_id}/toggle-active', 200, role='manager')
            is_active = response.get('is_active', True) if success else True
            self.log_test("تعطيل المستخدم", success, f"User active status: {is_active}")
            
            # Test disabled user cannot login
            if success and not is_active:
                login_success, login_response = self.make_request(
                    'POST', 'auth/login', 403,
                    data={"email": "test_user_check@test.com", "password": "newtest123"}
                )
                self.log_test("منع المستخدم المعطل من تسجيل الدخول", login_success, "Correctly denied login")
            
            # Re-enable user
            success, response = self.make_request('PUT', f'admin/users/{test_user_id}/toggle-active', 200, role='manager')
            self.log_test("إعادة تفعيل المستخدم", success, "User re-enabled")
            
            # 2.7 حذف المستخدم
            print("\n2.7 حذف المستخدم:")
            success, response = self.make_request('DELETE', f'admin/users/{test_user_id}', 200, role='manager')
            self.log_test("حذف مستخدم الاختبار", success, str(response) if not success else "User deleted successfully")

    # ==================== 3. المشاريع (Projects) ====================
    
    def test_projects_system(self):
        """Test projects management"""
        print("\n🏗️ 3. اختبار المشاريع (Projects)")
        
        # 3.1 قائمة المشاريع
        print("\n3.1 قائمة المشاريع:")
        success, response = self.make_request('GET', 'projects', 200, role='supervisor')
        projects_count = len(response) if success and isinstance(response, list) else 0
        self.log_test("قائمة المشاريع", success, f"Found {projects_count} projects")
        
        # Store existing project if available
        if success and response and len(response) > 0:
            self.test_data['project_id'] = response[0].get('id')
        
        # 3.2 إنشاء مشروع (إذا لم يوجد)
        if projects_count == 0:
            print("\n3.2 إنشاء مشروع:")
            project_data = {
                "name": "مشروع اختبار شامل",
                "owner_name": "مالك المشروع",
                "description": "مشروع للاختبار الشامل",
                "location": "الرياض"
            }
            success, response = self.make_request('POST', 'projects', 200, data=project_data, role='supervisor')
            project_id = response.get('id') if success else None
            self.test_data['project_id'] = project_id
            self.log_test("إنشاء مشروع اختبار", success, f"Project ID: {project_id}")

    # ==================== 4. الموردين (Suppliers) ====================
    
    def test_suppliers_system(self):
        """Test suppliers management"""
        print("\n🏪 4. اختبار الموردين (Suppliers)")
        
        # 4.1 قائمة الموردين
        print("\n4.1 قائمة الموردين:")
        success, response = self.make_request('GET', 'suppliers', 200, role='manager')
        suppliers_count = len(response) if success and isinstance(response, list) else 0
        self.log_test("قائمة الموردين", success, f"Found {suppliers_count} suppliers")

    # ==================== 5. طلبات المواد (Material Requests) ====================
    
    def test_material_requests_system(self):
        """Test material requests workflow"""
        print("\n📋 5. اختبار طلبات المواد (Material Requests)")
        
        # Get engineer ID first
        success, engineers = self.make_request('GET', 'users/engineers', 200, role='supervisor')
        engineer_id = None
        if success and engineers and len(engineers) > 0:
            engineer_id = engineers[0].get('id')
        
        if not engineer_id:
            self.log_test("الحصول على معرف المهندس", False, "No engineer found")
            return
        
        # 5.1 إنشاء طلب (كمشرف)
        print("\n5.1 إنشاء طلب مواد:")
        request_data = {
            "items": [
                {"name": "صنف اختبار", "quantity": 10, "unit": "قطعة"}
            ],
            "project_id": self.test_data.get('project_id'),
            "engineer_id": engineer_id,
            "reason": "طلب اختبار شامل"
        }
        
        if not request_data["project_id"]:
            self.log_test("إنشاء طلب مواد", False, "No project ID available")
            return
        
        success, response = self.make_request('POST', 'requests', 200, data=request_data, role='supervisor')
        request_id = response.get('id') if success else None
        self.test_data['request_id'] = request_id
        self.log_test("إنشاء طلب مواد", success, f"Request ID: {request_id}")
        
        # 5.2 قائمة الطلبات
        print("\n5.2 قائمة الطلبات:")
        success, response = self.make_request('GET', 'requests', 200, role='supervisor')
        requests_count = len(response) if success and isinstance(response, list) else 0
        self.log_test("قائمة الطلبات", success, f"Found {requests_count} requests")
        
        # 5.3 الموافقة على الطلب (كمهندس)
        if request_id:
            print("\n5.3 الموافقة على الطلب:")
            success, response = self.make_request('PUT', f'requests/{request_id}/approve', 200, role='engineer')
            self.log_test("الموافقة على الطلب", success, str(response) if not success else "Request approved")

    # ==================== 6. أوامر الشراء (Purchase Orders) ====================
    
    def test_purchase_orders_system(self):
        """Test purchase orders workflow"""
        print("\n🛒 6. اختبار أوامر الشراء (Purchase Orders)")
        
        request_id = self.test_data.get('request_id')
        if not request_id:
            self.log_test("إصدار أمر شراء", False, "No approved request available")
            return
        
        # 6.1 إصدار أمر شراء (كمدير مشتريات)
        print("\n6.1 إصدار أمر شراء:")
        po_data = {
            "request_id": request_id,
            "supplier_name": "مورد اختبار",
            "selected_items": [0],
            "notes": "أمر شراء للاختبار"
        }
        success, response = self.make_request('POST', 'purchase-orders', 200, data=po_data, role='manager')
        po_id = response.get('id') if success else None
        self.test_data['po_id'] = po_id
        self.log_test("إصدار أمر شراء", success, f"PO ID: {po_id}")
        
        # 6.2 قائمة أوامر الشراء
        print("\n6.2 قائمة أوامر الشراء:")
        success, response = self.make_request('GET', 'purchase-orders', 200, role='manager')
        po_count = len(response) if success and isinstance(response, list) else 0
        self.log_test("قائمة أوامر الشراء", success, f"Found {po_count} purchase orders")

    # ==================== 7. لوحة المدير العام (GM Dashboard) ====================
    
    def test_gm_dashboard(self):
        """Test General Manager dashboard"""
        print("\n👔 7. اختبار لوحة المدير العام (GM Dashboard)")
        
        # 7.1 إحصائيات المدير العام
        print("\n7.1 إحصائيات المدير العام:")
        success, response = self.make_request('GET', 'gm/stats', 200, role='general_manager')
        self.log_test("إحصائيات المدير العام", success, f"Stats: {response}" if success else str(response))
        
        # 7.2 الأوامر المعلقة
        print("\n7.2 الأوامر المعلقة:")
        success, response = self.make_request('GET', 'gm/all-orders', 200, 
            data={"status": "pending"}, role='general_manager')
        pending_count = len(response) if success and isinstance(response, list) else 0
        self.log_test("الأوامر المعلقة", success, f"Found {pending_count} pending orders")
        
        # 7.3 الأوامر المعتمدة
        print("\n7.3 الأوامر المعتمدة:")
        success, response = self.make_request('GET', 'gm/all-orders', 200, 
            data={"status": "approved"}, role='general_manager')
        approved_count = len(response) if success and isinstance(response, list) else 0
        self.log_test("الأوامر المعتمدة", success, f"Found {approved_count} approved orders")

    # ==================== 8. الكتالوج (Price Catalog) ====================
    
    def test_price_catalog_system(self):
        """Test price catalog management"""
        print("\n📚 8. اختبار الكتالوج (Price Catalog)")
        
        # 8.1 قائمة الكتالوج
        print("\n8.1 قائمة الكتالوج:")
        success, response = self.make_request('GET', 'price-catalog', 200, role='manager')
        catalog_count = len(response) if success and isinstance(response, list) else 0
        self.log_test("قائمة الكتالوج", success, f"Found {catalog_count} catalog items")
        
        # 8.2 إضافة صنف
        print("\n8.2 إضافة صنف:")
        catalog_item = {
            "name": "صنف كتالوج اختبار",
            "description": "صنف للاختبار",
            "unit": "قطعة",
            "price": 100.0,
            "supplier_name": "مورد الاختبار"
        }
        success, response = self.make_request('POST', 'price-catalog', 200, data=catalog_item, role='manager')
        catalog_item_id = response.get('id') if success else None
        self.test_data['catalog_item_id'] = catalog_item_id
        self.log_test("إضافة صنف للكتالوج", success, f"Item ID: {catalog_item_id}")
        
        # 8.3 الأسماء البديلة
        print("\n8.3 الأسماء البديلة:")
        success, response = self.make_request('GET', 'item-aliases', 200, role='manager')
        aliases_count = len(response) if success and isinstance(response, list) else 0
        self.log_test("قائمة الأسماء البديلة", success, f"Found {aliases_count} aliases")

    # ==================== 9. التقارير (Reports) ====================
    
    def test_reports_system(self):
        """Test reports functionality"""
        print("\n📊 9. اختبار التقارير (Reports)")
        
        # 9.1 تقرير التوفير
        print("\n9.1 تقرير التوفير:")
        success, response = self.make_request('GET', 'reports/cost-savings', 200, role='manager')
        self.log_test("تقرير التوفير", success, f"Report data: {response}" if success else str(response))
        
        # 9.2 تقرير استخدام الكتالوج
        print("\n9.2 تقرير استخدام الكتالوج:")
        success, response = self.make_request('GET', 'reports/catalog-usage', 200, role='manager')
        self.log_test("تقرير استخدام الكتالوج", success, f"Report data: {response}" if success else str(response))

    # ==================== 10. النسخ الاحتياطي (Backup) ====================
    
    def test_backup_system(self):
        """Test backup functionality"""
        print("\n💾 10. اختبار النسخ الاحتياطي (Backup)")
        
        # 10.1 إحصائيات النظام
        print("\n10.1 إحصائيات النظام:")
        success, response = self.make_request('GET', 'backup/stats', 200, role='manager')
        self.log_test("إحصائيات النظام", success, f"System stats: {response}" if success else str(response))

    # ==================== CLEANUP ====================
    
    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 تنظيف بيانات الاختبار:")
        
        # Delete test catalog item if created
        if self.test_data.get('catalog_item_id'):
            success, response = self.make_request('DELETE', f'price-catalog/{self.test_data["catalog_item_id"]}', 200, role='manager')
            self.log_test("حذف صنف الكتالوج", success, "Catalog item deleted" if success else str(response))

    # ==================== MAIN TEST RUNNER ====================
    
    def run_comprehensive_test(self):
        """Run all comprehensive tests"""
        print("🚀 بدء الاختبار الشامل للنظام")
        print("=" * 80)
        
        try:
            # Run all test modules
            self.test_authentication_system()
            self.test_user_management_system()
            self.test_projects_system()
            self.test_suppliers_system()
            self.test_material_requests_system()
            self.test_purchase_orders_system()
            self.test_gm_dashboard()
            self.test_price_catalog_system()
            self.test_reports_system()
            self.test_backup_system()
            
            # Cleanup
            self.cleanup_test_data()
            
        except Exception as e:
            print(f"\n❌ خطأ في الاختبار: {str(e)}")
            return False
        
        return True

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("📊 ملخص الاختبار (TEST SUMMARY)")
        print("=" * 80)
        print(f"إجمالي الاختبارات: {self.tests_run}")
        print(f"نجح: {self.tests_passed}")
        print(f"فشل: {self.tests_run - self.tests_passed}")
        print(f"معدل النجاح: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        # Print failed tests
        failed_tests = [t for t in self.test_results if not t['success']]
        if failed_tests:
            print("\n❌ الاختبارات الفاشلة (FAILED TESTS):")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        else:
            print("\n✅ جميع الاختبارات نجحت!")

def main():
    print("🌟 اختبار شامل ومفصل للنظام - Comprehensive System Testing")
    print("Material Request Management System - نظام إدارة طلبات المواد")
    print("=" * 80)
    
    tester = ComprehensiveAPITester()
    
    # Run comprehensive test
    success = tester.run_comprehensive_test()
    
    # Print summary
    tester.print_summary()
    
    # Return appropriate exit code
    return 0 if success and tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())