#!/usr/bin/env python3
"""
V2 High-Performance API Testing for Procurement System
Tests paginated APIs, dashboard stats, health checks, concurrent load, and search functionality
"""

import requests
import sys
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class V2PerformanceAPITester:
    def __init__(self, base_url="https://app-manager-20.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test credentials for all roles
        self.test_users = {
            "supervisor": {"email": "supervisor1@test.com", "password": "123456"},
            "engineer": {"email": "engineer1@test.com", "password": "123456"},
            "manager": {"email": "manager1@test.com", "password": "123456"},
            "printer": {"email": "printer1@test.com", "password": "123456"},
            "tracker": {"email": "tracker1@test.com", "password": "123456"}
        }

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

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=default_headers, timeout=30)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}, Expected: {expected_status}"
            
            if not success:
                try:
                    error_detail = response.json().get('detail', 'No detail')
                    details += f", Error: {error_detail}"
                except:
                    details += f", Response: {response.text[:200]}"

            self.log_test(name, success, details)
            
            try:
                return success, response.json() if response.content else {}
            except:
                return success, {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_health_checks(self):
        """Test both health check endpoints"""
        print("\n🏥 Testing Health Check Endpoints...")
        
        # Test root level health check (for Kubernetes)
        success1, response1 = self.run_test(
            "Health Check - Root Level (/health)",
            "GET",
            "/health",
            200
        )
        
        # Verify response structure
        if success1 and response1.get("status") == "healthy":
            print("   ✅ Root health check returns correct status")
        elif success1:
            print(f"   ⚠️ Root health check missing 'healthy' status: {response1}")
        
        # Test API level health check
        success2, response2 = self.run_test(
            "Health Check - API Level (/api/health)",
            "GET",
            "/api/health",
            200
        )
        
        # Verify response structure
        if success2 and response2.get("status") == "healthy":
            print("   ✅ API health check returns correct status")
        elif success2:
            print(f"   ⚠️ API health check missing 'healthy' status: {response2}")
        
        return success1 and success2

    def login_all_users(self):
        """Login all test users and store tokens"""
        print("\n🔐 Logging in all test users...")
        
        for role, credentials in self.test_users.items():
            success, response = self.run_test(
                f"Login {role.title()}",
                "POST",
                "/api/auth/login",
                200,
                data=credentials
            )
            
            if success and 'access_token' in response:
                self.tokens[role] = response['access_token']
                print(f"   ✅ {role.title()} logged in successfully")
            else:
                print(f"   ❌ {role.title()} login failed")
                return False
        
        return len(self.tokens) == len(self.test_users)

    def test_v2_paginated_requests(self):
        """Test V2 paginated requests API"""
        print("\n📄 Testing V2 Paginated Requests API...")
        
        if 'manager' not in self.tokens:
            print("❌ Manager token not available")
            return False
        
        headers = {'Authorization': f'Bearer {self.tokens["manager"]}'}
        
        # Test basic pagination
        success1, response1 = self.run_test(
            "V2 Requests - Basic Pagination (page=1, page_size=10)",
            "GET",
            "/api/v2/requests",
            200,
            headers=headers,
            params={"page": 1, "page_size": 10}
        )
        
        if success1:
            # Verify pagination structure
            required_fields = ["items", "total", "page", "page_size", "total_pages", "has_next", "has_prev"]
            missing_fields = [field for field in required_fields if field not in response1]
            
            if not missing_fields:
                print(f"   ✅ Pagination structure complete: {len(response1.get('items', []))} items, total: {response1.get('total', 0)}")
            else:
                print(f"   ⚠️ Missing pagination fields: {missing_fields}")
        
        # Test with status filter
        success2, response2 = self.run_test(
            "V2 Requests - Status Filter (status=approved)",
            "GET",
            "/api/v2/requests",
            200,
            headers=headers,
            params={"page": 1, "page_size": 10, "status": "approved_by_engineer"}
        )
        
        # Test with pending status filter
        success3, response3 = self.run_test(
            "V2 Requests - Status Filter (status=pending)",
            "GET",
            "/api/v2/requests",
            200,
            headers=headers,
            params={"page": 1, "page_size": 10, "status": "pending_engineer"}
        )
        
        return success1 and success2 and success3

    def test_v2_paginated_purchase_orders(self):
        """Test V2 paginated purchase orders API"""
        print("\n🛒 Testing V2 Paginated Purchase Orders API...")
        
        if 'manager' not in self.tokens:
            print("❌ Manager token not available")
            return False
        
        headers = {'Authorization': f'Bearer {self.tokens["manager"]}'}
        
        # Test basic pagination
        success1, response1 = self.run_test(
            "V2 Purchase Orders - Basic Pagination (page=1, page_size=10)",
            "GET",
            "/api/v2/purchase-orders",
            200,
            headers=headers,
            params={"page": 1, "page_size": 10}
        )
        
        if success1:
            # Verify pagination structure
            required_fields = ["items", "total", "page", "page_size", "total_pages", "has_next", "has_prev"]
            missing_fields = [field for field in required_fields if field not in response1]
            
            if not missing_fields:
                print(f"   ✅ Pagination structure complete: {len(response1.get('items', []))} items, total: {response1.get('total', 0)}")
            else:
                print(f"   ⚠️ Missing pagination fields: {missing_fields}")
        
        # Test with status filter
        success2, response2 = self.run_test(
            "V2 Purchase Orders - Status Filter (status=approved)",
            "GET",
            "/api/v2/purchase-orders",
            200,
            headers=headers,
            params={"page": 1, "page_size": 10, "status": "approved"}
        )
        
        # Test with pending status filter
        success3, response3 = self.run_test(
            "V2 Purchase Orders - Status Filter (status=pending)",
            "GET",
            "/api/v2/purchase-orders",
            200,
            headers=headers,
            params={"page": 1, "page_size": 10, "status": "pending_approval"}
        )
        
        return success1 and success2 and success3

    def test_v2_dashboard_stats_all_roles(self):
        """Test V2 optimized dashboard stats for all roles"""
        print("\n📊 Testing V2 Dashboard Stats for All Roles...")
        
        results = []
        
        for role, token in self.tokens.items():
            headers = {'Authorization': f'Bearer {token}'}
            
            success, response = self.run_test(
                f"V2 Dashboard Stats - {role.title()}",
                "GET",
                "/api/v2/dashboard/stats",
                200,
                headers=headers
            )
            
            if success:
                # Verify stats structure based on role
                if role == "supervisor":
                    expected_fields = ["total_requests", "pending_engineer", "approved_by_engineer", "rejected_by_engineer"]
                elif role == "engineer":
                    expected_fields = ["pending_approval", "approved_requests", "rejected_requests"]
                elif role == "manager":
                    expected_fields = ["total_requests", "total_orders", "pending_approval", "approved_orders", "printed_orders"]
                elif role == "printer":
                    expected_fields = ["pending_print", "printed_orders"]
                elif role == "tracker":
                    expected_fields = ["pending_delivery", "shipped", "partially_delivered", "delivered", "awaiting_shipment"]
                else:
                    expected_fields = []
                
                missing_fields = [field for field in expected_fields if field not in response]
                if not missing_fields:
                    print(f"   ✅ {role.title()} stats structure complete")
                else:
                    print(f"   ⚠️ {role.title()} missing fields: {missing_fields}")
            
            results.append(success)
        
        return all(results)

    def test_concurrent_load(self):
        """Test concurrent load with 20 simultaneous requests"""
        print("\n⚡ Testing Concurrent Load (20 simultaneous requests)...")
        
        if 'manager' not in self.tokens:
            print("❌ Manager token not available")
            return False
        
        headers = {'Authorization': f'Bearer {self.tokens["manager"]}'}
        
        def make_request(request_id):
            """Make a single request"""
            try:
                url = f"{self.base_url}/api/v2/requests"
                response = requests.get(
                    url, 
                    headers=headers, 
                    params={"page": 1, "page_size": 5},
                    timeout=30
                )
                return {
                    "id": request_id,
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                return {
                    "id": request_id,
                    "status_code": 0,
                    "success": False,
                    "error": str(e),
                    "response_time": 0
                }
        
        # Record start time
        start_time = time.time()
        
        # Execute 20 concurrent requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            results = [future.result() for future in as_completed(futures)]
        
        # Record end time
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        
        success_rate = len(successful_requests) / len(results) * 100
        avg_response_time = sum(r["response_time"] for r in successful_requests) / len(successful_requests) if successful_requests else 0
        
        print(f"   📈 Concurrent Load Results:")
        print(f"   - Total requests: 20")
        print(f"   - Successful: {len(successful_requests)}")
        print(f"   - Failed: {len(failed_requests)}")
        print(f"   - Success rate: {success_rate:.1f}%")
        print(f"   - Average response time: {avg_response_time:.3f}s")
        print(f"   - Total execution time: {total_time:.3f}s")
        
        # Log the test result
        test_success = success_rate >= 95  # 95% success rate threshold
        details = f"Success rate: {success_rate:.1f}%, Avg response: {avg_response_time:.3f}s"
        
        if failed_requests:
            details += f", Failures: {[r.get('error', 'Unknown') for r in failed_requests[:3]]}"
        
        self.log_test("Concurrent Load Test (20 requests)", test_success, details)
        
        return test_success

    def test_v2_search_api(self):
        """Test V2 global search API"""
        print("\n🔍 Testing V2 Search API...")
        
        if 'manager' not in self.tokens:
            print("❌ Manager token not available")
            return False
        
        headers = {'Authorization': f'Bearer {self.tokens["manager"]}'}
        
        # Test search with query
        success1, response1 = self.run_test(
            "V2 Search - Query 'test' with limit 10",
            "GET",
            "/api/v2/search",
            200,
            headers=headers,
            params={"q": "test", "limit": 10}
        )
        
        if success1:
            # Verify search response structure
            if "requests" in response1 and "orders" in response1:
                print(f"   ✅ Search structure correct: {len(response1.get('requests', []))} requests, {len(response1.get('orders', []))} orders")
            else:
                print(f"   ⚠️ Search response missing 'requests' or 'orders' arrays")
        
        # Test search with Arabic query
        success2, response2 = self.run_test(
            "V2 Search - Arabic Query 'حديد' with limit 5",
            "GET",
            "/api/v2/search",
            200,
            headers=headers,
            params={"q": "حديد", "limit": 5}
        )
        
        # Test search with empty query
        success3, response3 = self.run_test(
            "V2 Search - Empty Query",
            "GET",
            "/api/v2/search",
            200,
            headers=headers,
            params={"q": "", "limit": 10}
        )
        
        return success1 and success2 and success3

    def test_default_budget_categories(self):
        """Test default budget categories API"""
        print("\n💰 Testing Default Budget Categories API...")
        
        if 'manager' not in self.tokens:
            print("❌ Manager token not available")
            return False
        
        headers = {'Authorization': f'Bearer {self.tokens["manager"]}'}
        
        # Test getting default budget categories
        success, response = self.run_test(
            "Get Default Budget Categories",
            "GET",
            "/api/default-budget-categories",
            200,
            headers=headers
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Retrieved {len(response)} default budget categories")
                
                # Check if categories have required fields
                if response:
                    sample_category = response[0]
                    required_fields = ["id", "name", "default_budget", "created_by", "created_at"]
                    missing_fields = [field for field in required_fields if field not in sample_category]
                    
                    if not missing_fields:
                        print(f"   ✅ Category structure complete")
                    else:
                        print(f"   ⚠️ Category missing fields: {missing_fields}")
            else:
                print(f"   ⚠️ Response is not a list: {type(response)}")
        
        return success

    def test_system_configuration_verification(self):
        """Verify system has expected data volumes"""
        print("\n🔧 Verifying System Configuration...")
        
        if 'manager' not in self.tokens:
            print("❌ Manager token not available")
            return False
        
        headers = {'Authorization': f'Bearer {self.tokens["manager"]}'}
        
        # Check material requests count
        success1, requests_response = self.run_test(
            "Check Material Requests Count",
            "GET",
            "/api/v2/requests",
            200,
            headers=headers,
            params={"page": 1, "page_size": 100}
        )
        
        # Check purchase orders count
        success2, orders_response = self.run_test(
            "Check Purchase Orders Count",
            "GET",
            "/api/v2/purchase-orders",
            200,
            headers=headers,
            params={"page": 1, "page_size": 100}
        )
        
        if success1 and success2:
            requests_total = requests_response.get('total', 0)
            orders_total = orders_response.get('total', 0)
            
            print(f"   📊 System Data Volumes:")
            print(f"   - Material Requests: {requests_total}")
            print(f"   - Purchase Orders: {orders_total}")
            print(f"   - User Roles: {len(self.tokens)} (Expected: 5)")
            
            # Verify expected volumes from review request
            expected_requests = 54
            expected_orders = 22
            expected_roles = 5
            
            requests_ok = requests_total >= expected_requests * 0.8  # Allow 20% variance
            orders_ok = orders_total >= expected_orders * 0.8
            roles_ok = len(self.tokens) == expected_roles
            
            if requests_ok and orders_ok and roles_ok:
                print(f"   ✅ System configuration meets expected volumes")
            else:
                print(f"   ⚠️ System configuration variance detected")
                if not requests_ok:
                    print(f"      - Requests: {requests_total} (expected ~{expected_requests})")
                if not orders_ok:
                    print(f"      - Orders: {orders_total} (expected ~{expected_orders})")
                if not roles_ok:
                    print(f"      - Roles: {len(self.tokens)} (expected {expected_roles})")
        
        return success1 and success2

    def run_comprehensive_v2_test(self):
        """Run comprehensive V2 API and performance tests"""
        print("🚀 Starting V2 High-Performance API Testing")
        print("=" * 70)
        
        # 1. Health checks
        if not self.test_health_checks():
            print("❌ Health checks failed, stopping tests")
            return False
        
        # 2. Login all users
        if not self.login_all_users():
            print("❌ User authentication failed, stopping tests")
            return False
        
        # 3. Verify system configuration
        self.test_system_configuration_verification()
        
        # 4. Test V2 paginated APIs
        print("\n" + "=" * 50)
        print("📄 TESTING V2 PAGINATED APIS")
        print("=" * 50)
        
        requests_success = self.test_v2_paginated_requests()
        orders_success = self.test_v2_paginated_purchase_orders()
        
        # 5. Test V2 dashboard stats
        print("\n" + "=" * 50)
        print("📊 TESTING V2 DASHBOARD STATS")
        print("=" * 50)
        
        stats_success = self.test_v2_dashboard_stats_all_roles()
        
        # 6. Test search API
        print("\n" + "=" * 50)
        print("🔍 TESTING V2 SEARCH API")
        print("=" * 50)
        
        search_success = self.test_v2_search_api()
        
        # 7. Test default budget categories
        print("\n" + "=" * 50)
        print("💰 TESTING DEFAULT BUDGET CATEGORIES")
        print("=" * 50)
        
        budget_success = self.test_default_budget_categories()
        
        # 8. Test concurrent load
        print("\n" + "=" * 50)
        print("⚡ TESTING CONCURRENT LOAD")
        print("=" * 50)
        
        load_success = self.test_concurrent_load()
        
        # Overall success
        overall_success = all([
            requests_success, orders_success, stats_success, 
            search_success, budget_success, load_success
        ])
        
        print("\n🎉 V2 High-Performance API testing completed!")
        return overall_success

def main():
    print("🚀 Starting V2 High-Performance Procurement System API Tests")
    print("=" * 70)
    
    tester = V2PerformanceAPITester()
    
    # Run comprehensive V2 test
    overall_success = tester.run_comprehensive_v2_test()
    
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
    
    # Performance summary
    print("\n📈 PERFORMANCE SUMMARY:")
    print("- Health checks: Root + API level endpoints")
    print("- Authentication: 5 user roles tested")
    print("- Pagination: V2 requests and purchase orders APIs")
    print("- Dashboard stats: Optimized for all roles")
    print("- Search: Global search with Arabic support")
    print("- Concurrent load: 20 simultaneous requests")
    print("- Budget categories: Default categories API")
    
    # Return appropriate exit code
    return 0 if overall_success and tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())