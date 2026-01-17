"""
Test Quantity Engineer Rebuilt Features - Iteration 7
Testing the rebuilt Quantity Engineer feature with new logic:
- QE selects items from price catalog (catalog_item_id is mandatory)
- Links items to specific projects
- Sets multiple quantities with different delivery dates
- Quantities are automatically deducted when creating purchase orders

APIs to test:
- POST /api/pg/auth/login - login as quantity_engineer
- GET /api/pg/quantity/dashboard/stats - dashboard stats
- GET /api/pg/quantity/catalog-items - get catalog items for selection
- GET /api/pg/quantity/planned - get planned quantities
- POST /api/pg/quantity/planned - create planned quantity (with catalog_item_id)
- PUT /api/pg/quantity/planned/{id} - update planned quantity
- DELETE /api/pg/quantity/planned/{id} - delete planned quantity
- GET /api/pg/quantity/alerts - get alerts (overdue and due soon items)
- GET /api/pg/quantity/reports/summary - quantity reports
- POST /api/pg/quantity/deduct - deduct quantity from plan
- GET /api/pg/quantity/planned/export - export to Excel
"""

import pytest
import requests
import os
import uuid

from tests.test_config import get_credentials

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
QUANTITY_ENGINEER_CREDS = get_credentials("quantity_engineer")
SYSTEM_ADMIN_CREDS = get_credentials("system_admin")
PROCUREMENT_MANAGER_CREDS = get_credentials("procurement_manager")


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


class TestDashboardStats:
    """Test dashboard stats API"""
    
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
        expected_fields = ["total_planned_items", "total_remaining_qty", "overdue_items", "due_soon_items", "projects_count", "catalog_items_count"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Dashboard stats retrieved successfully:")
        print(f"  - Total planned items: {data.get('total_planned_items')}")
        print(f"  - Total remaining qty: {data.get('total_remaining_qty')}")
        print(f"  - Overdue items: {data.get('overdue_items')}")
        print(f"  - Due soon items: {data.get('due_soon_items')}")
        print(f"  - Projects count: {data.get('projects_count')}")
        print(f"  - Catalog items count: {data.get('catalog_items_count')}")


class TestCatalogItems:
    """Test catalog items API for selection"""
    
    @pytest.fixture
    def qe_token(self):
        """Get quantity engineer token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("QE login failed")
    
    def test_get_catalog_items(self, qe_token):
        """Test getting catalog items for selection"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/quantity/catalog-items", headers=headers)
        
        assert response.status_code == 200, f"Failed to get catalog items: {response.text}"
        data = response.json()
        
        assert "items" in data, "Response should have 'items'"
        assert "total" in data, "Response should have 'total'"
        
        # Verify item structure
        if data.get("items"):
            item = data["items"][0]
            expected_fields = ["id", "name", "unit", "price", "currency"]
            for field in expected_fields:
                assert field in item, f"Missing field in catalog item: {field}"
        
        print(f"✓ Got catalog items: {data.get('total')} items")
    
    def test_search_catalog_items(self, qe_token):
        """Test searching catalog items"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/quantity/catalog-items?search=اسمنت", headers=headers)
        
        assert response.status_code == 200, f"Failed to search catalog items: {response.text}"
        print(f"✓ Catalog search works correctly")


class TestPlannedQuantitiesCRUD:
    """Test planned quantities CRUD operations with new logic"""
    
    @pytest.fixture
    def qe_token(self):
        """Get quantity engineer token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("QE login failed")
    
    @pytest.fixture
    def catalog_item_id(self, qe_token):
        """Get a catalog item ID for testing"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/quantity/catalog-items", headers=headers)
        if response.status_code == 200:
            items = response.json().get("items", [])
            if items:
                return items[0].get("id")
        pytest.skip("No catalog items available")
    
    @pytest.fixture
    def project_id(self, qe_token):
        """Get a project ID for testing"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/projects", headers=headers)
        if response.status_code == 200:
            data = response.json()
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
        
        # Verify item structure includes catalog_item_id
        if data.get("items"):
            item = data["items"][0]
            assert "catalog_item_id" in item, "Item should have catalog_item_id"
        
        print(f"✓ Got planned quantities: {data.get('total')} items")
    
    def test_create_planned_quantity_with_catalog_item(self, qe_token, catalog_item_id, project_id):
        """Test creating a new planned quantity with catalog_item_id (new logic)"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        
        new_item = {
            "catalog_item_id": catalog_item_id,  # Required - select from catalog
            "project_id": project_id,
            "planned_quantity": 100,
            "expected_order_date": "2026-03-15",
            "priority": 2,
            "notes": "TEST_اختبار إضافة كمية مخططة من الكتالوج"
        }
        
        response = requests.post(f"{BASE_URL}/api/pg/quantity/planned", json=new_item, headers=headers)
        assert response.status_code in [200, 201], f"Failed to create planned quantity: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should have 'id'"
        assert "item_name" in data, "Response should have 'item_name'"
        print(f"✓ Created planned quantity: {data.get('id')} - {data.get('item_name')}")
        assert data.get("id")
    
    def test_create_without_catalog_item_fails(self, qe_token, project_id):
        """Test that creating without catalog_item_id fails"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        
        # Try to create without catalog_item_id
        new_item = {
            "project_id": project_id,
            "planned_quantity": 50
        }
        
        response = requests.post(f"{BASE_URL}/api/pg/quantity/planned", json=new_item, headers=headers)
        # Should fail with 422 (validation error) since catalog_item_id is required
        assert response.status_code == 422, f"Should fail without catalog_item_id: {response.status_code}"
        print(f"✓ Correctly rejects creation without catalog_item_id")
    
    def test_update_planned_quantity(self, qe_token, catalog_item_id, project_id):
        """Test updating a planned quantity"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        
        # First create an item
        new_item = {
            "catalog_item_id": catalog_item_id,
            "project_id": project_id,
            "planned_quantity": 50,
            "priority": 1,
            "notes": "TEST_للتحديث"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/pg/quantity/planned", json=new_item, headers=headers)
        if create_response.status_code not in [200, 201]:
            pytest.skip("Failed to create item for update test")
        
        item_id = create_response.json().get('id')
        
        # Update the item
        update_data = {
            "planned_quantity": 75,
            "priority": 3,
            "notes": "TEST_تم التحديث"
        }
        
        response = requests.put(f"{BASE_URL}/api/pg/quantity/planned/{item_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Failed to update planned quantity: {response.text}"
        print(f"✓ Updated planned quantity: {item_id}")
    
    def test_delete_planned_quantity(self, qe_token, catalog_item_id, project_id):
        """Test deleting a planned quantity"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        
        # First create an item
        new_item = {
            "catalog_item_id": catalog_item_id,
            "project_id": project_id,
            "planned_quantity": 25,
            "notes": "TEST_للحذف"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/pg/quantity/planned", json=new_item, headers=headers)
        if create_response.status_code not in [200, 201]:
            pytest.skip("Failed to create item for delete test")
        
        item_id = create_response.json().get('id')
        
        # Delete the item
        response = requests.delete(f"{BASE_URL}/api/pg/quantity/planned/{item_id}", headers=headers)
        assert response.status_code == 200, f"Failed to delete planned quantity: {response.text}"
        print(f"✓ Deleted planned quantity: {item_id}")


class TestAlerts:
    """Test alerts API"""
    
    @pytest.fixture
    def qe_token(self):
        """Get quantity engineer token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("QE login failed")
    
    def test_get_alerts(self, qe_token):
        """Test getting alerts"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/quantity/alerts", headers=headers)
        
        assert response.status_code == 200, f"Failed to get alerts: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "overdue" in data, "Response should have 'overdue'"
        assert "due_soon" in data, "Response should have 'due_soon'"
        assert "high_priority" in data, "Response should have 'high_priority'"
        
        print(f"✓ Got alerts:")
        print(f"  - Overdue: {data.get('overdue', {}).get('count', 0)}")
        print(f"  - Due soon: {data.get('due_soon', {}).get('count', 0)}")
        print(f"  - High priority: {data.get('high_priority', {}).get('count', 0)}")


class TestReports:
    """Test reports API"""
    
    @pytest.fixture
    def qe_token(self):
        """Get quantity engineer token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("QE login failed")
    
    def test_reports_summary(self, qe_token):
        """Test reports summary"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/quantity/reports/summary", headers=headers)
        
        assert response.status_code == 200, f"Failed to get reports: {response.text}"
        data = response.json()
        
        assert "summary" in data, "Response should have 'summary'"
        assert "by_project" in data, "Response should have 'by_project'"
        
        summary = data.get("summary", {})
        print(f"✓ Got reports summary:")
        print(f"  - Total items: {summary.get('total_items')}")
        print(f"  - Completion rate: {summary.get('completion_rate')}%")


class TestDeductQuantity:
    """Test deduct quantity API (for procurement manager)"""
    
    @pytest.fixture
    def pm_token(self):
        """Get procurement manager token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=PROCUREMENT_MANAGER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("PM login failed")
    
    @pytest.fixture
    def qe_token(self):
        """Get quantity engineer token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("QE login failed")
    
    @pytest.fixture
    def test_planned_item(self, qe_token):
        """Create a test planned item for deduction"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        
        # Get catalog item
        catalog_response = requests.get(f"{BASE_URL}/api/pg/quantity/catalog-items", headers=headers)
        if catalog_response.status_code != 200:
            pytest.skip("Failed to get catalog items")
        catalog_items = catalog_response.json().get("items", [])
        if not catalog_items:
            pytest.skip("No catalog items")
        
        # Get project
        project_response = requests.get(f"{BASE_URL}/api/pg/projects", headers=headers)
        if project_response.status_code != 200:
            pytest.skip("Failed to get projects")
        projects = project_response.json()
        if isinstance(projects, dict):
            projects = projects.get("projects", [])
        if not projects:
            pytest.skip("No projects")
        
        # Create planned item
        new_item = {
            "catalog_item_id": catalog_items[0]["id"],
            "project_id": projects[0]["id"],
            "planned_quantity": 100,
            "notes": "TEST_للخصم"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/pg/quantity/planned", json=new_item, headers=headers)
        if create_response.status_code not in [200, 201]:
            pytest.skip("Failed to create test item")
        
        return {
            "catalog_item_id": catalog_items[0]["id"],
            "project_id": projects[0]["id"]
        }
    
    def test_deduct_quantity(self, pm_token, test_planned_item):
        """Test deducting quantity from plan"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        
        deduct_data = {
            "catalog_item_id": test_planned_item["catalog_item_id"],
            "project_id": test_planned_item["project_id"],
            "quantity_to_deduct": 10
        }
        
        response = requests.post(f"{BASE_URL}/api/pg/quantity/deduct", json=deduct_data, headers=headers)
        assert response.status_code == 200, f"Failed to deduct quantity: {response.text}"
        
        data = response.json()
        assert "deducted" in data, "Response should have 'deducted'"
        print(f"✓ Deducted quantity: {data.get('deducted')}")
    
    def test_qe_cannot_deduct(self, qe_token, test_planned_item):
        """Test that QE cannot deduct (only PM can)"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        
        deduct_data = {
            "catalog_item_id": test_planned_item["catalog_item_id"],
            "project_id": test_planned_item["project_id"],
            "quantity_to_deduct": 5
        }
        
        response = requests.post(f"{BASE_URL}/api/pg/quantity/deduct", json=deduct_data, headers=headers)
        assert response.status_code == 403, f"QE should not be able to deduct: {response.status_code}"
        print(f"✓ QE correctly denied deduct access")


class TestExport:
    """Test export functionality"""
    
    @pytest.fixture
    def qe_token(self):
        """Get quantity engineer token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=QUANTITY_ENGINEER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("QE login failed")
    
    def test_export_to_excel(self, qe_token):
        """Test exporting planned quantities to Excel"""
        headers = {"Authorization": f"Bearer {qe_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/quantity/planned/export", headers=headers)
        
        assert response.status_code == 200, f"Failed to export: {response.text}"
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers.get("content-type", ""), \
            f"Wrong content type: {response.headers.get('content-type')}"
        assert len(response.content) > 0, "Export file is empty"
        print(f"✓ Exported to Excel: {len(response.content)} bytes")


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
        test_items = [i for i in items if 'TEST_' in (i.get('notes') or '')]
        
        deleted = 0
        for item in test_items:
            if item.get('ordered_quantity', 0) == 0:
                del_response = requests.delete(f"{BASE_URL}/api/pg/quantity/planned/{item['id']}", headers=headers)
                if del_response.status_code == 200:
                    deleted += 1
        
        print(f"✓ Cleaned up {deleted} test items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
