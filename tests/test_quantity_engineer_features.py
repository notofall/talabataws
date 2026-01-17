"""
Test Quantity Engineer Features - Iteration 6
Testing new features:
1) Create user with quantity_engineer role from system admin dashboard
2) Login as quantity_engineer and auto-redirect to dashboard
3) Quantity Engineer Dashboard - display stats
4) Add new planned quantity
5) Export/Import quantities from Excel
6) Supplier performance report in advanced reports
7) Price variance report in advanced reports
8) Export price catalog to Excel

APIs to test:
- POST /api/pg/admin/users - create user with quantity_engineer role
- POST /api/pg/auth/login - login as quantity_engineer
- GET /api/pg/quantity/dashboard/stats - dashboard stats
- GET /api/pg/quantity/planned - get planned quantities
- POST /api/pg/quantity/planned - create planned quantity
- PUT /api/pg/quantity/planned/{id} - update planned quantity
- DELETE /api/pg/quantity/planned/{id} - delete planned quantity
- GET /api/pg/quantity/planned/template - download template
- POST /api/pg/quantity/planned/import - import from Excel
- GET /api/pg/quantity/planned/export - export to Excel
- GET /api/pg/quantity/reports/summary - quantity reports
- GET /api/pg/reports/advanced/supplier-performance - supplier performance
- GET /api/pg/reports/advanced/price-variance - price variance report
- GET /api/pg/price-catalog/export/excel - export catalog to Excel
"""

import pytest
import requests
import os
import uuid

from tests.test_config import get_credentials

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SYSTEM_ADMIN_CREDS = get_credentials("system_admin")
QUANTITY_ENGINEER_CREDS = get_credentials("quantity_engineer")
PROCUREMENT_MANAGER_CREDS = get_credentials("procurement_manager")


class TestSystemAdminUserManagement:
    """Test creating quantity_engineer user from system admin"""
    
    @pytest.fixture
    def admin_token(self):
        """Get system admin token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=SYSTEM_ADMIN_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("System admin login failed")
    
    def test_admin_login(self):
        """Test system admin login"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=SYSTEM_ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert data.get("user", {}).get("role") == "system_admin", f"Wrong role: {data.get('user', {}).get('role')}"
        print(f"✓ System Admin login successful")
    
    def test_get_users_list(self, admin_token):
        """Test getting users list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/admin/users", headers=headers)
        
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Users should be a list"
        print(f"✓ Got {len(data)} users")
        
        # Check if quantity_engineer exists
        quantity_engineers = [u for u in data if u.get("role") == "quantity_engineer"]
        print(f"  Found {len(quantity_engineers)} quantity engineers")
        assert data is not None
    
    def test_create_quantity_engineer_user(self, admin_token):
        """Test creating a user with quantity_engineer role"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First check if user already exists
        response = requests.get(f"{BASE_URL}/api/pg/admin/users", headers=headers)
        users = response.json()
        existing = [u for u in users if u.get("email") == QUANTITY_ENGINEER_CREDS["email"]]
        
        if existing:
            print(f"✓ Quantity engineer user already exists: {existing[0].get('name')}")
            return
        
        # Create new quantity engineer
        new_user = {
            "name": "مهندس كميات اختبار",
            "email": QUANTITY_ENGINEER_CREDS["email"],
            "password": QUANTITY_ENGINEER_CREDS["password"],
            "role": "quantity_engineer"
        }
        
        response = requests.post(f"{BASE_URL}/api/pg/admin/users", json=new_user, headers=headers)
        assert response.status_code in [200, 201], f"Failed to create user: {response.text}"
        print(f"✓ Created quantity engineer user: {new_user['email']}")


class TestQuantityEngineerLogin:
    """Test quantity engineer login and authentication"""
    
    def test_quantity_engineer_login(self):
        """Test login as quantity engineer"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        assert response.status_code == 200, f"QE login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert data.get("user", {}).get("role") == "quantity_engineer", f"Wrong role: {data.get('user', {}).get('role')}"
        print(f"✓ Quantity Engineer login successful - role: {data.get('user', {}).get('role')}")
    
    def test_quantity_engineer_me_endpoint(self):
        """Test /auth/me endpoint for quantity engineer"""
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        if login_response.status_code != 200:
            pytest.skip("QE login failed")
        
        token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/pg/auth/me", headers=headers)
        assert response.status_code == 200, f"Failed to get user info: {response.text}"
        data = response.json()
        assert data.get("role") == "quantity_engineer", f"Wrong role: {data.get('role')}"
        print(f"✓ /auth/me returns correct role: {data.get('role')}")


class TestQuantityEngineerDashboard:
    """Test quantity engineer dashboard APIs"""
    
    @pytest.fixture
    def qe_token(self):
        """Get quantity engineer token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("QE login failed")
    
    def test_dashboard_stats(self, qe_token):
        """Test dashboard stats API"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/quantity/dashboard/stats", headers=headers)
        
        assert response.status_code == 200, f"Failed to get dashboard stats: {response.text}"
        data = response.json()
        
        # Verify expected fields
        expected_fields = ["total_planned_items", "total_remaining_qty", "overdue_items", "due_soon_items"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Dashboard stats retrieved successfully:")
        print(f"  - Total planned items: {data.get('total_planned_items')}")
        print(f"  - Total remaining qty: {data.get('total_remaining_qty')}")
        print(f"  - Overdue items: {data.get('overdue_items')}")
        print(f"  - Due soon items: {data.get('due_soon_items')}")
    
    def test_get_projects_list(self, qe_token):
        """Test getting projects list for quantity engineer"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/projects", headers=headers)
        
        assert response.status_code == 200, f"Failed to get projects: {response.text}"
        data = response.json()
        # API returns list directly
        projects = data if isinstance(data, list) else data.get('projects', [])
        print(f"✓ Got projects list: {len(projects)} projects")


class TestPlannedQuantities:
    """Test planned quantities CRUD operations"""
    
    @pytest.fixture
    def qe_token(self):
        """Get quantity engineer token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("QE login failed")

    @pytest.fixture
    def pm_token(self):
        """Get procurement manager token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=PROCUREMENT_MANAGER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Procurement manager login failed")

    @pytest.fixture
    def catalog_item_id(self, qe_token, pm_token):
        """Get or create a catalog item ID for planned quantities"""
        qe_headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/quantity/catalog-items", headers=qe_headers)
        if response.status_code == 200:
            items = response.json().get("items", [])
            if items:
                return items[0].get("id")

        pm_headers = {"Authorization": f"Bearer {pm_token}"}
        new_item = {
            "name": f"صنف كتالوج اختبار {uuid.uuid4().hex[:6]}",
            "price": 25.0,
            "currency": "SAR",
            "unit": "قطعة"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/pg/price-catalog",
            headers=pm_headers,
            json=new_item,
        )
        assert create_response.status_code in [200, 201], f"Failed to create catalog item: {create_response.text}"
        return create_response.json().get("id")
    
    @pytest.fixture
    def project_id(self, qe_token):
        """Get a project ID for testing"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/projects", headers=headers)
        if response.status_code == 200:
            data = response.json()
            # API returns list directly
            projects = data if isinstance(data, list) else data.get('projects', [])
            if projects:
                return projects[0].get('id')
        pytest.skip("No projects available")
    
    def test_get_planned_quantities(self, qe_token):
        """Test getting planned quantities list"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/quantity/planned", headers=headers)
        
        assert response.status_code == 200, f"Failed to get planned quantities: {response.text}"
        data = response.json()
        
        assert "items" in data, "Response should have 'items'"
        assert "total" in data, "Response should have 'total'"
        print(f"✓ Got planned quantities: {data.get('total')} items")
    
    def test_get_planned_quantities_with_filters(self, qe_token):
        """Test getting planned quantities with filters"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        
        # Test with search filter
        response = requests.get(f"{BASE_URL}/api/pg/quantity/planned?search=test", headers=headers)
        assert response.status_code == 200, f"Failed with search filter: {response.text}"
        
        # Test with status filter
        response = requests.get(f"{BASE_URL}/api/pg/quantity/planned?status=planned", headers=headers)
        assert response.status_code == 200, f"Failed with status filter: {response.text}"
        
        # Test with pagination
        response = requests.get(f"{BASE_URL}/api/pg/quantity/planned?page=1&page_size=10", headers=headers)
        assert response.status_code == 200, f"Failed with pagination: {response.text}"
        
        print(f"✓ Planned quantities filters work correctly")
    
    def test_create_planned_quantity(self, qe_token, project_id, catalog_item_id):
        """Test creating a new planned quantity"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        
        new_item = {
            "catalog_item_id": catalog_item_id,
            "project_id": project_id,
            "planned_quantity": 100,
            "expected_order_date": "2026-03-01",
            "priority": 2,
            "notes": "ملاحظات اختبار"
        }
        
        response = requests.post(f"{BASE_URL}/api/pg/quantity/planned", json=new_item, headers=headers)
        assert response.status_code in [200, 201], f"Failed to create planned quantity: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should have 'id'"
        print(f"✓ Created planned quantity: {data.get('id')}")
        assert data.get("id")
    
    def test_update_planned_quantity(self, qe_token, project_id, catalog_item_id):
        """Test updating a planned quantity"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        
        # First create an item
        new_item = {
            "catalog_item_id": catalog_item_id,
            "project_id": project_id,
            "planned_quantity": 50,
            "priority": 1
        }
        
        create_response = requests.post(f"{BASE_URL}/api/pg/quantity/planned", json=new_item, headers=headers)
        if create_response.status_code not in [200, 201]:
            pytest.skip("Failed to create item for update test")
        
        item_id = create_response.json().get('id')
        
        # Update the item
        update_data = {
            "planned_quantity": 75,
            "priority": 3
        }
        
        response = requests.put(f"{BASE_URL}/api/pg/quantity/planned/{item_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Failed to update planned quantity: {response.text}"
        print(f"✓ Updated planned quantity: {item_id}")
    
    def test_delete_planned_quantity(self, qe_token, project_id, catalog_item_id):
        """Test deleting a planned quantity"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        
        # First create an item
        new_item = {
            "catalog_item_id": catalog_item_id,
            "project_id": project_id,
            "planned_quantity": 25
        }
        
        create_response = requests.post(f"{BASE_URL}/api/pg/quantity/planned", json=new_item, headers=headers)
        if create_response.status_code not in [200, 201]:
            pytest.skip("Failed to create item for delete test")
        
        item_id = create_response.json().get('id')
        
        # Delete the item
        response = requests.delete(f"{BASE_URL}/api/pg/quantity/planned/{item_id}", headers=headers)
        assert response.status_code == 200, f"Failed to delete planned quantity: {response.text}"
        print(f"✓ Deleted planned quantity: {item_id}")


class TestQuantityExportImport:
    """Test export/import functionality for planned quantities"""
    
    @pytest.fixture
    def qe_token(self):
        """Get quantity engineer token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("QE login failed")
    
    def test_download_template(self, qe_token):
        """Test downloading Excel template"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/quantity/planned/template", headers=headers)
        
        assert response.status_code == 200, f"Failed to download template: {response.text}"
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers.get("content-type", ""), \
            f"Wrong content type: {response.headers.get('content-type')}"
        assert len(response.content) > 0, "Template file is empty"
        print(f"✓ Downloaded template: {len(response.content)} bytes")
    
    def test_export_planned_quantities(self, qe_token):
        """Test exporting planned quantities to Excel"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/quantity/planned/export", headers=headers)
        
        assert response.status_code == 200, f"Failed to export: {response.text}"
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers.get("content-type", ""), \
            f"Wrong content type: {response.headers.get('content-type')}"
        print(f"✓ Exported planned quantities: {len(response.content)} bytes")


class TestQuantityReports:
    """Test quantity reports"""
    
    @pytest.fixture
    def qe_token(self):
        """Get quantity engineer token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("QE login failed")
    
    def test_quantity_summary_report(self, qe_token):
        """Test quantity summary report"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/quantity/reports/summary", headers=headers)
        
        assert response.status_code == 200, f"Failed to get summary report: {response.text}"
        data = response.json()
        
        assert "summary" in data, "Response should have 'summary'"
        print(f"✓ Got quantity summary report")
        print(f"  - Total items: {data.get('summary', {}).get('total_items')}")
        print(f"  - Completion rate: {data.get('summary', {}).get('completion_rate')}%")


class TestAdvancedReports:
    """Test advanced reports (supplier performance, price variance)"""
    
    @pytest.fixture
    def pm_token(self):
        """Get procurement manager token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=PROCUREMENT_MANAGER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("PM login failed")
    
    def test_supplier_performance_report(self, pm_token):
        """Test supplier performance report"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/reports/advanced/supplier-performance", headers=headers)
        
        assert response.status_code == 200, f"Failed to get supplier performance: {response.text}"
        data = response.json()
        
        assert "summary" in data, "Response should have 'summary'"
        assert "suppliers" in data, "Response should have 'suppliers'"
        
        print(f"✓ Got supplier performance report")
        print(f"  - Total suppliers: {data.get('summary', {}).get('total_suppliers')}")
        print(f"  - Total orders: {data.get('summary', {}).get('total_orders')}")
        print(f"  - Total spending: {data.get('summary', {}).get('total_spending')}")
    
    def test_price_variance_report(self, pm_token):
        """Test price variance report"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/reports/advanced/price-variance", headers=headers)
        
        assert response.status_code == 200, f"Failed to get price variance: {response.text}"
        data = response.json()
        
        assert "summary" in data, "Response should have 'summary'"
        print(f"✓ Got price variance report")
        print(f"  - Items analyzed: {data.get('summary', {}).get('total_items_analyzed')}")
        print(f"  - Items with changes: {data.get('summary', {}).get('items_with_changes')}")


class TestPriceCatalogExport:
    """Test price catalog export to Excel"""
    
    @pytest.fixture
    def pm_token(self):
        """Get procurement manager token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=PROCUREMENT_MANAGER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("PM login failed")
    
    def test_export_catalog_to_excel(self, pm_token):
        """Test exporting price catalog to Excel"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/price-catalog/export/excel", headers=headers)
        
        assert response.status_code == 200, f"Failed to export catalog: {response.text}"
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers.get("content-type", ""), \
            f"Wrong content type: {response.headers.get('content-type')}"
        assert len(response.content) > 0, "Export file is empty"
        print(f"✓ Exported price catalog to Excel: {len(response.content)} bytes")
    
    def test_export_catalog_to_csv(self, pm_token):
        """Test exporting price catalog to CSV"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/price-catalog/export", headers=headers)
        
        assert response.status_code == 200, f"Failed to export catalog CSV: {response.text}"
        assert "text/csv" in response.headers.get("content-type", ""), \
            f"Wrong content type: {response.headers.get('content-type')}"
        print(f"✓ Exported price catalog to CSV: {len(response.content)} bytes")
    
    def test_get_catalog_template(self, pm_token):
        """Test getting catalog import template"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/price-catalog/template", headers=headers)
        
        assert response.status_code == 200, f"Failed to get template: {response.text}"
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers.get("content-type", ""), \
            f"Wrong content type: {response.headers.get('content-type')}"
        print(f"✓ Got catalog template: {len(response.content)} bytes")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def qe_token(self):
        """Get quantity engineer token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("QE login failed")
    
    def test_cleanup_test_items(self, qe_token):
        """Cleanup TEST_ prefixed items"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        
        # Get all planned items
        response = requests.get(f"{BASE_URL}/api/pg/quantity/planned?page_size=100", headers=headers)
        if response.status_code != 200:
            print("Could not get items for cleanup")
            return
        
        items = response.json().get('items', [])
        test_items = [i for i in items if i.get('item_name', '').startswith('TEST_')]
        
        deleted = 0
        for item in test_items:
            if item.get('ordered_quantity', 0) == 0:
                del_response = requests.delete(f"{BASE_URL}/api/pg/quantity/planned/{item['id']}", headers=headers)
                if del_response.status_code == 200:
                    deleted += 1
        
        print(f"✓ Cleaned up {deleted} test items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
