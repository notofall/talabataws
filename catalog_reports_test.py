#!/usr/bin/env python3
"""
Catalog Import/Export and Reports Testing
Tests the new features requested in the review:
1. Catalog Export APIs (Excel, CSV, Template)
2. Catalog Import API
3. Cost Savings Report API
4. Catalog Usage Report API
5. Supplier Performance Report API
6. Authorization Tests
"""

import requests
import sys
import json
import io
import csv
from datetime import datetime

class CatalogReportsAPITester:
    def __init__(self, base_url="https://postgres-migrate-7.preview.emergentagent.com"):
        self.base_url = base_url
        self.manager_token = None
        self.supervisor_token = None
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

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        default_headers = {}
        if not files:  # Only set Content-Type for non-file uploads
            default_headers['Content-Type'] = 'application/json'
        
        if headers:
            default_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers)
            elif method == 'POST':
                if files:
                    # Remove Content-Type for file uploads
                    if 'Content-Type' in default_headers:
                        del default_headers['Content-Type']
                    response = requests.post(url, files=files, headers=default_headers)
                else:
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
            
            # Return response content for successful requests
            if success:
                try:
                    return success, response.json()
                except:
                    # For file downloads, return raw content
                    return success, response.content
            else:
                return success, {}

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

    def test_catalog_export_excel(self, token):
        """Test catalog export to Excel"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Catalog Export Excel",
            "GET",
            "price-catalog/export/excel",
            200,
            headers=headers
        )
        
        if success and isinstance(response, bytes):
            # Check if it's a valid Excel file (starts with PK for ZIP format)
            is_excel = response.startswith(b'PK')
            if is_excel:
                print(f"   📄 Excel file downloaded successfully ({len(response)} bytes)")
                return True
            else:
                print(f"   ❌ Invalid Excel file format")
                return False
        return success

    def test_catalog_export_csv(self, token):
        """Test catalog export to CSV"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Catalog Export CSV",
            "GET",
            "price-catalog/export/csv",
            200,
            headers=headers
        )
        
        if success and isinstance(response, bytes):
            # Try to decode and parse CSV
            try:
                csv_content = response.decode('utf-8-sig')
                csv_reader = csv.reader(io.StringIO(csv_content))
                rows = list(csv_reader)
                if len(rows) > 0:
                    print(f"   📄 CSV file downloaded successfully ({len(rows)} rows)")
                    return True
                else:
                    print(f"   ❌ Empty CSV file")
                    return False
            except Exception as e:
                print(f"   ❌ Invalid CSV format: {e}")
                return False
        return success

    def test_catalog_template(self, token):
        """Test catalog template download"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Catalog Template Download",
            "GET",
            "price-catalog/template",
            200,
            headers=headers
        )
        
        if success and isinstance(response, bytes):
            # Check if it's a valid Excel file
            is_excel = response.startswith(b'PK')
            if is_excel:
                print(f"   📄 Template file downloaded successfully ({len(response)} bytes)")
                return True
            else:
                print(f"   ❌ Invalid template file format")
                return False
        return success

    def test_catalog_import(self, token):
        """Test catalog import with CSV content"""
        headers = {'Authorization': f'Bearer {token}'}
        
        # Create test CSV content with Arabic headers
        csv_content = """اسم الصنف,السعر,الوحدة
حديد تسليح 14مم,2800,طن
اسمنت مقاوم,28,كيس
رمل خشن,160,متر مكعب
حصى مدرج,180,متر مكعب"""
        
        # Create file-like object
        csv_file = io.BytesIO(csv_content.encode('utf-8-sig'))
        
        files = {'file': ('test_catalog.csv', csv_file, 'text/csv')}
        
        success, response = self.run_test(
            "Catalog Import CSV",
            "POST",
            "price-catalog/import",
            200,
            files=files,
            headers=headers
        )
        
        if success and isinstance(response, dict):
            imported = response.get('imported', 0)
            updated = response.get('updated', 0)
            errors = response.get('errors', [])
            print(f"   📊 Import results: {imported} new, {updated} updated, {len(errors)} errors")
            return imported > 0 or updated > 0
        
        return success

    def test_cost_savings_report(self, token):
        """Test cost savings report API"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Cost Savings Report",
            "GET",
            "reports/cost-savings",
            200,
            headers=headers
        )
        
        if success and isinstance(response, dict):
            summary = response.get('summary', {})
            by_project = response.get('by_project', [])
            top_savings = response.get('top_savings_items', [])
            
            # Verify required fields in summary
            required_fields = ['total_estimated', 'total_actual', 'total_saving', 'saving_percent', 
                             'items_from_catalog', 'items_not_in_catalog', 'catalog_usage_percent', 'orders_count']
            
            missing_fields = [field for field in required_fields if field not in summary]
            
            if missing_fields:
                print(f"   ❌ Missing summary fields: {missing_fields}")
                return False
            
            print(f"   📊 Summary: {summary.get('orders_count', 0)} orders, {summary.get('total_saving', 0)} SAR saved")
            print(f"   📊 Projects: {len(by_project)}, Top savings items: {len(top_savings)}")
            return True
        
        return success

    def test_catalog_usage_report(self, token):
        """Test catalog usage report API"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Catalog Usage Report",
            "GET",
            "reports/catalog-usage",
            200,
            headers=headers
        )
        
        if success and isinstance(response, dict):
            summary = response.get('summary', {})
            most_used = response.get('most_used_items', [])
            unused_items = response.get('unused_items', [])
            
            # Verify required fields in summary
            required_fields = ['total_catalog_items', 'items_with_usage', 'unused_items', 
                             'total_aliases', 'total_alias_usage']
            
            missing_fields = [field for field in required_fields if field not in summary]
            
            if missing_fields:
                print(f"   ❌ Missing summary fields: {missing_fields}")
                return False
            
            print(f"   📊 Catalog: {summary.get('total_catalog_items', 0)} items, {summary.get('items_with_usage', 0)} used")
            print(f"   📊 Most used: {len(most_used)}, Unused: {len(unused_items)}")
            return True
        
        return success

    def test_supplier_performance_report(self, token):
        """Test supplier performance report API"""
        headers = {'Authorization': f'Bearer {token}'}
        success, response = self.run_test(
            "Supplier Performance Report",
            "GET",
            "reports/supplier-performance",
            200,
            headers=headers
        )
        
        if success and isinstance(response, dict):
            suppliers = response.get('suppliers', [])
            summary = response.get('summary', {})
            
            # Verify required fields in summary
            required_summary_fields = ['total_suppliers', 'total_orders', 'total_value']
            missing_summary_fields = [field for field in required_summary_fields if field not in summary]
            
            if missing_summary_fields:
                print(f"   ❌ Missing summary fields: {missing_summary_fields}")
                return False
            
            # Verify supplier fields
            if suppliers:
                required_supplier_fields = ['supplier_name', 'orders_count', 'total_value', 
                                          'delivered_count', 'delivery_rate', 'on_time_rate']
                first_supplier = suppliers[0]
                missing_supplier_fields = [field for field in required_supplier_fields if field not in first_supplier]
                
                if missing_supplier_fields:
                    print(f"   ❌ Missing supplier fields: {missing_supplier_fields}")
                    return False
            
            print(f"   📊 Suppliers: {len(suppliers)}, Total orders: {summary.get('total_orders', 0)}")
            print(f"   📊 Total value: {summary.get('total_value', 0)} SAR")
            return True
        
        return success

    def test_authorization_supervisor_reports(self, supervisor_token):
        """Test that supervisor CANNOT access reports endpoints"""
        headers = {'Authorization': f'Bearer {supervisor_token}'}
        
        report_endpoints = [
            "reports/cost-savings",
            "reports/catalog-usage", 
            "reports/supplier-performance"
        ]
        
        all_forbidden = True
        for endpoint in report_endpoints:
            success, response = self.run_test(
                f"Supervisor Access Denied - {endpoint}",
                "GET",
                endpoint,
                403,  # Expecting 403 Forbidden
                headers=headers
            )
            if not success:
                all_forbidden = False
        
        return all_forbidden

    def test_authorization_supervisor_catalog_export(self, supervisor_token):
        """Test that supervisor CANNOT export/import catalog"""
        headers = {'Authorization': f'Bearer {supervisor_token}'}
        
        export_endpoints = [
            "price-catalog/export/excel",
            "price-catalog/export/csv",
            "price-catalog/template"
        ]
        
        all_forbidden = True
        for endpoint in export_endpoints:
            success, response = self.run_test(
                f"Supervisor Export Denied - {endpoint}",
                "GET",
                endpoint,
                403,  # Expecting 403 Forbidden
                headers=headers
            )
            if not success:
                all_forbidden = False
        
        # Test import as well
        csv_content = "اسم الصنف,السعر,الوحدة\nاختبار,100,قطعة"
        csv_file = io.BytesIO(csv_content.encode('utf-8-sig'))
        files = {'file': ('test.csv', csv_file, 'text/csv')}
        
        success, response = self.run_test(
            "Supervisor Import Denied - price-catalog/import",
            "POST",
            "price-catalog/import",
            403,  # Expecting 403 Forbidden
            files=files,
            headers=headers
        )
        
        return all_forbidden and success

    def run_all_tests(self):
        """Run all catalog and reports tests"""
        print("🚀 Starting Catalog Import/Export and Reports API Tests")
        print("=" * 60)
        
        # Test login for manager (should have access)
        print("\n📋 Testing Authentication...")
        self.manager_token = self.test_login("manager1@test.com", "123456", "Manager")
        if not self.manager_token:
            print("❌ Manager login failed - cannot continue tests")
            return
        
        # Test login for supervisor (should NOT have access to reports)
        self.supervisor_token = self.test_login("supervisor1@test.com", "123456", "Supervisor")
        if not self.supervisor_token:
            print("❌ Supervisor login failed - cannot test authorization")
        
        print("\n📋 Testing Catalog Export APIs...")
        # Test catalog export APIs (as manager)
        self.test_catalog_export_excel(self.manager_token)
        self.test_catalog_export_csv(self.manager_token)
        self.test_catalog_template(self.manager_token)
        
        print("\n📋 Testing Catalog Import API...")
        # Test catalog import
        self.test_catalog_import(self.manager_token)
        
        print("\n📋 Testing Reports APIs...")
        # Test reports APIs
        self.test_cost_savings_report(self.manager_token)
        self.test_catalog_usage_report(self.manager_token)
        self.test_supplier_performance_report(self.manager_token)
        
        print("\n📋 Testing Authorization...")
        # Test authorization (supervisor should be denied)
        if self.supervisor_token:
            self.test_authorization_supervisor_reports(self.supervisor_token)
            self.test_authorization_supervisor_catalog_export(self.supervisor_token)
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            print("⚠️  SOME TESTS FAILED")
            # Print failed tests
            failed_tests = [t for t in self.test_results if not t['success']]
            for test in failed_tests:
                print(f"   ❌ {test['test']}: {test['details']}")
            return False

if __name__ == "__main__":
    tester = CatalogReportsAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)