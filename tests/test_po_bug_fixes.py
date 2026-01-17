"""
Test Purchase Order Bug Fixes - Iteration 8
Tests for:
1. order_number displays correctly as PO-00000001 (not UUID)
2. Catalog item linking when creating PO
3. Supplier invoice number restricted to Delivery Tracker only
4. Delivery tracker APIs work correctly
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PROCUREMENT_MANAGER = {"email": "notofall@gmail.com", "password": "123456"}
DELIVERY_TRACKER = {"email": "delivery@test.com", "password": "123456"}
ENGINEER = {"email": "engineer1@test.com", "password": "123456"}

# Test order ID
TEST_ORDER_ID = "5dcb244b-89f2-467a-9ff3-26b2cba367cc"


@pytest.fixture(scope="module")
def pm_token():
    """Get procurement manager token"""
    response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=PROCUREMENT_MANAGER)
    assert response.status_code == 200, f"PM login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def dt_token():
    """Get delivery tracker token"""
    response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=DELIVERY_TRACKER)
    assert response.status_code == 200, f"DT login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def eng_token():
    """Get engineer token"""
    response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=ENGINEER)
    assert response.status_code == 200, f"Engineer login failed: {response.text}"
    return response.json()["access_token"]


class TestOrderNumberFormat:
    """Test that order_number displays correctly as PO-XXXXXXXX format"""
    
    def test_purchase_orders_api_returns_order_number(self, pm_token):
        """GET /api/pg/purchase-orders returns order_number in correct format"""
        response = requests.get(
            f"{BASE_URL}/api/pg/purchase-orders",
            headers={"Authorization": f"Bearer {pm_token}"}
        )
        assert response.status_code == 200
        orders = response.json()
        
        if len(orders) > 0:
            order = orders[0]
            # Verify order_number field exists
            assert "order_number" in order, "order_number field missing"
            # Verify format is PO-XXXXXXXX
            assert order["order_number"].startswith("PO-"), f"order_number should start with PO-, got: {order['order_number']}"
            # Verify it's not a UUID
            assert len(order["order_number"]) == 11, f"order_number should be 11 chars (PO-00000001), got: {order['order_number']}"
            # Verify order_seq exists
            assert "order_seq" in order, "order_seq field missing"
            assert isinstance(order["order_seq"], int), "order_seq should be integer"
    
    def test_delivery_tracker_orders_returns_order_number(self, dt_token):
        """GET /api/pg/delivery-tracker/orders returns order_number in correct format"""
        response = requests.get(
            f"{BASE_URL}/api/pg/delivery-tracker/orders",
            headers={"Authorization": f"Bearer {dt_token}"}
        )
        assert response.status_code == 200
        orders = response.json()
        
        if len(orders) > 0:
            order = orders[0]
            # Verify order_number field exists
            assert "order_number" in order, "order_number field missing"
            # Verify format is PO-XXXXXXXX
            assert order["order_number"].startswith("PO-"), f"order_number should start with PO-, got: {order['order_number']}"
            # Verify order_seq exists
            assert "order_seq" in order, "order_seq field missing"


class TestSupplierInvoiceRestriction:
    """Test that supplier_invoice_number can only be updated by Delivery Tracker"""
    
    def test_procurement_manager_cannot_update_invoice(self, pm_token):
        """Procurement Manager should get 403 when updating supplier invoice"""
        response = requests.put(
            f"{BASE_URL}/api/pg/purchase-orders/{TEST_ORDER_ID}/supplier-invoice",
            headers={"Authorization": f"Bearer {pm_token}", "Content-Type": "application/json"},
            json={"supplier_invoice_number": "INV-PM-TEST"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "متتبع التسليم" in response.json().get("detail", ""), "Error message should mention delivery tracker"
    
    def test_engineer_cannot_update_invoice(self, eng_token):
        """Engineer should get 403 when updating supplier invoice"""
        response = requests.put(
            f"{BASE_URL}/api/pg/purchase-orders/{TEST_ORDER_ID}/supplier-invoice",
            headers={"Authorization": f"Bearer {eng_token}", "Content-Type": "application/json"},
            json={"supplier_invoice_number": "INV-ENG-TEST"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_delivery_tracker_can_update_invoice(self, dt_token):
        """Delivery Tracker should be able to update supplier invoice"""
        response = requests.put(
            f"{BASE_URL}/api/pg/purchase-orders/{TEST_ORDER_ID}/supplier-invoice",
            headers={"Authorization": f"Bearer {dt_token}", "Content-Type": "application/json"},
            json={"supplier_invoice_number": "INV-DT-TEST-123"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "تم تحديث" in response.json().get("message", ""), "Success message expected"


class TestDeliveryTrackerAPIs:
    """Test Delivery Tracker specific APIs"""
    
    def test_delivery_tracker_stats(self, dt_token):
        """GET /api/pg/delivery-tracker/stats returns correct stats"""
        response = requests.get(
            f"{BASE_URL}/api/pg/delivery-tracker/stats",
            headers={"Authorization": f"Bearer {dt_token}"}
        )
        assert response.status_code == 200
        stats = response.json()
        
        # Verify all expected fields
        assert "pending_delivery" in stats, "pending_delivery field missing"
        assert "partially_delivered" in stats, "partially_delivered field missing"
        assert "delivered" in stats, "delivered field missing"
        assert "shipped" in stats, "shipped field missing"
        
        # Verify values are integers
        assert isinstance(stats["pending_delivery"], int)
        assert isinstance(stats["partially_delivered"], int)
        assert isinstance(stats["delivered"], int)
        assert isinstance(stats["shipped"], int)
    
    def test_delivery_tracker_orders(self, dt_token):
        """GET /api/pg/delivery-tracker/orders returns orders"""
        response = requests.get(
            f"{BASE_URL}/api/pg/delivery-tracker/orders",
            headers={"Authorization": f"Bearer {dt_token}"}
        )
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list), "Response should be a list"
        
        if len(orders) > 0:
            order = orders[0]
            # Verify order structure
            assert "id" in order
            assert "order_number" in order
            assert "status" in order
            assert "items" in order
            assert "supplier_name" in order
    
    def test_non_delivery_tracker_cannot_access_stats(self, pm_token):
        """Non-delivery tracker users should get 403 on stats API"""
        response = requests.get(
            f"{BASE_URL}/api/pg/delivery-tracker/stats",
            headers={"Authorization": f"Bearer {pm_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_non_delivery_tracker_cannot_access_orders(self, eng_token):
        """Non-delivery tracker users should get 403 on orders API"""
        response = requests.get(
            f"{BASE_URL}/api/pg/delivery-tracker/orders",
            headers={"Authorization": f"Bearer {eng_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"


class TestCatalogItemLinking:
    """Test catalog item linking in purchase orders"""
    
    def test_order_items_have_catalog_fields(self, pm_token):
        """Order items should have catalog_item_id and item_code fields"""
        response = requests.get(
            f"{BASE_URL}/api/pg/purchase-orders",
            headers={"Authorization": f"Bearer {pm_token}"}
        )
        assert response.status_code == 200
        orders = response.json()
        
        if len(orders) > 0:
            order = orders[0]
            if "items" in order and len(order["items"]) > 0:
                item = order["items"][0]
                # Verify catalog fields exist (can be null)
                assert "catalog_item_id" in item, "catalog_item_id field missing from order items"
                assert "item_code" in item, "item_code field missing from order items"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
