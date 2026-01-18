"""
Test Bug Fixes - Iteration 5
Testing 4 reported bugs:
1) Item price in catalog not showing in purchase order
2) Reports button in catalog leads to empty page
3) General Manager settings not working
4) Export purchase orders as GM not returning data

APIs to test:
- GET /api/pg/settings - for general_manager and procurement_manager
- PUT /api/pg/settings/{key} - for general_manager
- GET /api/pg/reports/cost-savings - should return summary with total_estimated, total_actual
- GET /api/pg/gm/all-orders - should return items with each order
- GET /api/pg/gm/pending-orders - should return items with each order
"""

import pytest
import requests
import os

from tests.test_config import get_credentials

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
GENERAL_MANAGER_CREDS = get_credentials("general_manager")
PROCUREMENT_MANAGER_CREDS = get_credentials("procurement_manager")
SYSTEM_ADMIN_CREDS = get_credentials("system_admin")


class TestAuthentication:
    """Test login for different roles"""
    
    def test_login_general_manager(self):
        """Test login as general manager"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=GENERAL_MANAGER_CREDS)
        assert response.status_code == 200, f"GM login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert data.get("user", {}).get("role") == "general_manager", f"Wrong role: {data.get('user', {}).get('role')}"
        print(f"✓ General Manager login successful - role: {data.get('user', {}).get('role')}")
    
    def test_login_procurement_manager(self):
        """Test login as procurement manager"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=PROCUREMENT_MANAGER_CREDS)
        assert response.status_code == 200, f"PM login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert data.get("user", {}).get("role") == "procurement_manager", f"Wrong role: {data.get('user', {}).get('role')}"
        print(f"✓ Procurement Manager login successful - role: {data.get('user', {}).get('role')}")


class TestSettingsAPI:
    """Test settings API for general_manager and procurement_manager"""
    
    @pytest.fixture
    def gm_token(self):
        """Get general manager token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=GENERAL_MANAGER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("GM login failed")
    
    @pytest.fixture
    def pm_token(self):
        """Get procurement manager token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=PROCUREMENT_MANAGER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("PM login failed")
    
    def test_get_settings_as_general_manager(self, gm_token):
        """BUG FIX #3: General Manager should be able to access settings"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/settings", headers=headers)
        
        assert response.status_code == 200, f"GM cannot access settings: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Settings should be a list, got: {type(data)}"
        print(f"✓ General Manager can access settings - {len(data)} settings found")
        
        # Verify settings structure
        if len(data) > 0:
            setting = data[0]
            assert "key" in setting, "Setting should have 'key'"
            assert "value" in setting, "Setting should have 'value'"
            print(f"  Sample setting: {setting.get('key')} = {setting.get('value')}")
    
    def test_get_settings_as_procurement_manager(self, pm_token):
        """Procurement Manager should also be able to access settings"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/settings", headers=headers)
        
        assert response.status_code == 200, f"PM cannot access settings: {response.status_code} - {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Settings should be a list, got: {type(data)}"
        print(f"✓ Procurement Manager can access settings - {len(data)} settings found")
    
    def test_update_setting_as_general_manager(self, gm_token):
        """BUG FIX #3: General Manager should be able to update settings"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        
        # First get current settings
        get_response = requests.get(f"{BASE_URL}/api/pg/settings", headers=headers)
        if get_response.status_code != 200 or not get_response.json():
            pytest.skip("No settings available to update")
        
        settings = get_response.json()
        # Find approval_limit setting
        approval_limit_setting = next((s for s in settings if s.get("key") == "approval_limit"), None)
        
        if approval_limit_setting:
            current_value = approval_limit_setting.get("value")
            # Update to a new value
            new_value = "25000" if current_value != "25000" else "20000"
            
            update_response = requests.put(
                f"{BASE_URL}/api/pg/settings/approval_limit",
                json={"value": new_value},
                headers=headers
            )
            
            assert update_response.status_code == 200, f"GM cannot update settings: {update_response.status_code} - {update_response.text}"
            print(f"✓ General Manager can update settings - approval_limit: {current_value} -> {new_value}")
            
            # Restore original value
            requests.put(
                f"{BASE_URL}/api/pg/settings/approval_limit",
                json={"value": current_value},
                headers=headers
            )
        else:
            print("⚠ approval_limit setting not found, skipping update test")


class TestReportsAPI:
    """Test reports API - cost-savings should return summary"""
    
    @pytest.fixture
    def pm_token(self):
        """Get procurement manager token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=PROCUREMENT_MANAGER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("PM login failed")
    
    @pytest.fixture
    def gm_token(self):
        """Get general manager token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=GENERAL_MANAGER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("GM login failed")
    
    def test_cost_savings_report_has_summary(self, pm_token):
        """BUG FIX #2: Reports should return summary with total_estimated, total_actual"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/reports/cost-savings", headers=headers)
        
        assert response.status_code == 200, f"Cost savings report failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Check for summary field
        assert "summary" in data, f"Response should have 'summary' field. Keys: {data.keys()}"
        summary = data["summary"]
        
        # Check summary structure
        assert "total_estimated" in summary, f"Summary should have 'total_estimated'. Keys: {summary.keys()}"
        assert "total_actual" in summary, f"Summary should have 'total_actual'. Keys: {summary.keys()}"
        
        print(f"✓ Cost savings report has summary:")
        print(f"  - total_estimated: {summary.get('total_estimated')}")
        print(f"  - total_actual: {summary.get('total_actual')}")
        print(f"  - total_saving: {summary.get('total_saving')}")
        print(f"  - saving_percent: {summary.get('saving_percent')}")
    
    def test_cost_savings_report_has_by_project(self, pm_token):
        """Reports should have by_project data"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/reports/cost-savings", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "by_project" in data, f"Response should have 'by_project'. Keys: {data.keys()}"
        print(f"✓ Cost savings report has by_project: {len(data.get('by_project', []))} projects")
    
    def test_cost_savings_report_as_gm(self, gm_token):
        """General Manager should also access cost savings report"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/reports/cost-savings", headers=headers)
        
        assert response.status_code == 200, f"GM cannot access cost savings: {response.status_code} - {response.text}"
        data = response.json()
        assert "summary" in data, "Response should have 'summary'"
        print(f"✓ General Manager can access cost savings report")


class TestGMOrdersAPI:
    """Test GM orders API - should return items with each order"""
    
    @pytest.fixture
    def gm_token(self):
        """Get general manager token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=GENERAL_MANAGER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("GM login failed")
    
    def test_gm_all_orders_returns_items(self, gm_token):
        """BUG FIX #4: GM all-orders should return items with each order"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/gm/all-orders", headers=headers)
        
        assert response.status_code == 200, f"GM all-orders failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert isinstance(data, list), f"Response should be a list, got: {type(data)}"
        print(f"✓ GM all-orders returned {len(data)} orders")
        
        # Check if orders have items field
        if len(data) > 0:
            order = data[0]
            assert "items" in order, f"Order should have 'items' field. Keys: {order.keys()}"
            items = order.get("items", [])
            print(f"  First order has {len(items)} items")
            
            # Check item structure if items exist
            if len(items) > 0:
                item = items[0]
                assert "name" in item, f"Item should have 'name'. Keys: {item.keys()}"
                assert "quantity" in item, f"Item should have 'quantity'"
                assert "unit_price" in item, f"Item should have 'unit_price'"
                print(f"  Sample item: {item.get('name')} - qty: {item.get('quantity')} - price: {item.get('unit_price')}")
    
    def test_gm_pending_orders_returns_items(self, gm_token):
        """BUG FIX #4: GM pending-orders should return items with each order"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/gm/pending-orders", headers=headers)
        
        assert response.status_code == 200, f"GM pending-orders failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert isinstance(data, list), f"Response should be a list, got: {type(data)}"
        print(f"✓ GM pending-orders returned {len(data)} orders")
        
        # Check if orders have items field
        if len(data) > 0:
            order = data[0]
            assert "items" in order, f"Order should have 'items' field. Keys: {order.keys()}"
            items = order.get("items", [])
            print(f"  First pending order has {len(items)} items")
    
    def test_gm_all_orders_with_filter(self, gm_token):
        """Test GM all-orders with approval_type filter"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        
        # Test gm_approved filter
        response = requests.get(f"{BASE_URL}/api/pg/gm/all-orders?approval_type=gm_approved", headers=headers)
        assert response.status_code == 200, f"GM all-orders with filter failed: {response.status_code}"
        data = response.json()
        print(f"✓ GM all-orders (gm_approved) returned {len(data)} orders")
        
        # Test manager_approved filter
        response = requests.get(f"{BASE_URL}/api/pg/gm/all-orders?approval_type=manager_approved", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ GM all-orders (manager_approved) returned {len(data)} orders")


class TestPriceCatalogInPurchaseOrder:
    """Test that item prices from catalog appear in purchase orders"""
    
    @pytest.fixture
    def pm_token(self):
        """Get procurement manager token"""
        response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=PROCUREMENT_MANAGER_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("PM login failed")
    
    def test_price_catalog_exists(self, pm_token):
        """Check if price catalog API exists and returns data"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/price-catalog", headers=headers)
        
        assert response.status_code == 200, f"Price catalog failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Check structure
        if isinstance(data, dict):
            items = data.get("items", [])
        else:
            items = data
        
        print(f"✓ Price catalog returned {len(items)} items")
        
        if len(items) > 0:
            item = items[0]
            print(f"  Sample catalog item: {item}")
    
    def test_purchase_orders_have_item_prices(self, pm_token):
        """BUG FIX #1: Purchase orders should have item prices from catalog"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/pg/purchase-orders", headers=headers)
        
        assert response.status_code == 200, f"Purchase orders failed: {response.status_code}"
        data = response.json()
        
        if isinstance(data, dict):
            orders = data.get("orders", [])
        else:
            orders = data
        
        print(f"✓ Purchase orders returned {len(orders)} orders")
        
        # Check if orders have items with prices
        for order in orders[:3]:  # Check first 3 orders
            items = order.get("items", [])
            if len(items) > 0:
                for item in items:
                    unit_price = item.get("unit_price")
                    print(f"  Order {order.get('order_number', order.get('id', '')[:8])}: Item '{item.get('name')}' - unit_price: {unit_price}")
                    # Price should be present (can be 0 but should exist)
                    assert "unit_price" in item, f"Item should have unit_price field"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
