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
import uuid

from tests.test_config import get_credentials

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PROCUREMENT_MANAGER = get_credentials("procurement_manager")
DELIVERY_TRACKER = get_credentials("delivery_tracker")
ENGINEER = get_credentials("engineer")
SUPERVISOR = get_credentials("supervisor")
SYSTEM_ADMIN = get_credentials("system_admin")


def login(creds):
    response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=creds)
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


def get_user_id_by_email(admin_token, email):
    response = requests.get(
        f"{BASE_URL}/api/pg/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, f"Failed to get users: {response.text}"
    for user in response.json():
        if user.get("email") == email:
            return user.get("id")
    pytest.skip(f"User not found: {email}")


@pytest.fixture(scope="module")
def pm_token():
    """Get procurement manager token"""
    return login(PROCUREMENT_MANAGER)


@pytest.fixture(scope="module")
def dt_token():
    """Get delivery tracker token"""
    return login(DELIVERY_TRACKER)


@pytest.fixture(scope="module")
def eng_token():
    """Get engineer token"""
    return login(ENGINEER)


@pytest.fixture(scope="module")
def supervisor_token():
    return login(SUPERVISOR)


@pytest.fixture(scope="module")
def admin_token():
    return login(SYSTEM_ADMIN)


@pytest.fixture(scope="module")
def test_order_context(pm_token, eng_token, supervisor_token, admin_token):
    """Create a purchase order through the full workflow and return its context."""
    headers = {"Authorization": f"Bearer {supervisor_token}"}
    engineer_id = get_user_id_by_email(admin_token, ENGINEER["email"])

    project_payload = {
        "name": f"مشروع اختبار أوامر الشراء {uuid.uuid4().hex[:6]}",
        "owner_name": "مالك الاختبار",
        "description": "مشروع لإنشاء أمر شراء تجريبي",
    }
    project_response = requests.post(
        f"{BASE_URL}/api/pg/projects",
        headers=headers,
        json=project_payload,
    )
    assert project_response.status_code == 200, f"Project create failed: {project_response.text}"
    project_id = project_response.json()["id"]

    request_payload = {
        "items": [
            {
                "name": "صنف اختبار",
                "quantity": 5,
                "unit": "قطعة",
                "estimated_price": 12.5,
            }
        ],
        "project_id": project_id,
        "reason": "طلب اختبار لإصدار أمر شراء",
        "engineer_id": engineer_id,
    }
    request_response = requests.post(
        f"{BASE_URL}/api/pg/requests",
        headers=headers,
        json=request_payload,
    )
    assert request_response.status_code == 200, f"Request create failed: {request_response.text}"
    request_id = request_response.json()["id"]

    approve_response = requests.post(
        f"{BASE_URL}/api/pg/requests/{request_id}/approve",
        headers={"Authorization": f"Bearer {eng_token}"},
    )
    assert approve_response.status_code == 200, f"Approve failed: {approve_response.text}"

    order_payload = {
        "request_id": request_id,
        "supplier_name": "مورد اختبار",
        "selected_items": [0],
        "notes": "أمر شراء للاختبار",
    }
    order_response = requests.post(
        f"{BASE_URL}/api/pg/purchase-orders",
        headers={"Authorization": f"Bearer {pm_token}"},
        json=order_payload,
    )
    assert order_response.status_code == 200, f"Order create failed: {order_response.text}"
    return {
        "order_id": order_response.json()["id"],
        "request_id": request_id,
        "project_id": project_id,
    }


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

    def test_request_status_updated_after_order(self, pm_token, test_order_context):
        """Request status should update after creating order"""
        response = requests.get(
            f"{BASE_URL}/api/pg/requests/{test_order_context['request_id']}",
            headers={"Authorization": f"Bearer {pm_token}"},
        )
        assert response.status_code == 200, f"Failed to get request: {response.text}"
        data = response.json()
        assert data.get("status") in ["purchase_order_issued", "partially_ordered"]
    
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
    
    def test_procurement_manager_cannot_update_invoice(self, pm_token, test_order_context):
        """Procurement Manager should get 403 when updating supplier invoice"""
        response = requests.put(
            f"{BASE_URL}/api/pg/purchase-orders/{test_order_context['order_id']}/supplier-invoice",
            headers={"Authorization": f"Bearer {pm_token}", "Content-Type": "application/json"},
            json={"supplier_invoice_number": "INV-PM-TEST"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "متتبع التسليم" in response.json().get("detail", ""), "Error message should mention delivery tracker"
    
    def test_engineer_cannot_update_invoice(self, eng_token, test_order_context):
        """Engineer should get 403 when updating supplier invoice"""
        response = requests.put(
            f"{BASE_URL}/api/pg/purchase-orders/{test_order_context['order_id']}/supplier-invoice",
            headers={"Authorization": f"Bearer {eng_token}", "Content-Type": "application/json"},
            json={"supplier_invoice_number": "INV-ENG-TEST"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_delivery_tracker_can_update_invoice(self, dt_token, test_order_context):
        """Delivery Tracker should be able to update supplier invoice"""
        response = requests.put(
            f"{BASE_URL}/api/pg/purchase-orders/{test_order_context['order_id']}/supplier-invoice",
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
