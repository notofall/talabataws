import os
import uuid

import pytest
import requests

from tests.test_config import get_credentials


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

SUPERVISOR = get_credentials("supervisor")
ENGINEER = get_credentials("engineer")
PROCUREMENT_MANAGER = get_credentials("procurement_manager")
DELIVERY_TRACKER = get_credentials("delivery_tracker")


def login(creds):
    response = requests.post(f"{BASE_URL}/api/pg/auth/login", json=creds)
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


def get_engineer_id(token):
    response = requests.get(
        f"{BASE_URL}/api/pg/users/list",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, f"Failed to fetch users: {response.text}"
    engineers = [u for u in response.json() if u.get("role") == "engineer"]
    if not engineers:
        pytest.skip("No engineer users available")
    return engineers[0]["id"]


def create_project(token):
    payload = {
        "name": f"مشروع Edge {uuid.uuid4().hex[:6]}",
        "owner_name": "مالك اختبارات Edge",
        "description": "مشروع لإنشاء طلبات الاختبار",
    }
    response = requests.post(
        f"{BASE_URL}/api/pg/projects",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200, f"Project create failed: {response.text}"
    return response.json()["id"]


def create_request(token, project_id, engineer_id, quantity=5):
    payload = {
        "items": [
            {
                "name": "صنف Edge",
                "quantity": quantity,
                "unit": "قطعة",
                "estimated_price": 10.0,
            }
        ],
        "project_id": project_id,
        "reason": "طلب Edge",
        "engineer_id": engineer_id,
    }
    response = requests.post(
        f"{BASE_URL}/api/pg/requests",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200, f"Request create failed: {response.text}"
    return response.json()["id"]


def approve_request(token, request_id):
    response = requests.post(
        f"{BASE_URL}/api/pg/requests/{request_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, f"Request approve failed: {response.text}"


def create_order(token, request_id):
    payload = {
        "request_id": request_id,
        "supplier_name": "مورد Edge",
        "selected_items": [0],
        "notes": "أمر شراء Edge",
    }
    response = requests.post(
        f"{BASE_URL}/api/pg/purchase-orders",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200, f"Order create failed: {response.text}"
    return response.json()["id"]


class TestRequestEdgeCases:
    def test_create_request_with_empty_items(self):
        supervisor_token = login(SUPERVISOR)
        engineer_id = get_engineer_id(supervisor_token)
        project_id = create_project(supervisor_token)

        payload = {
            "items": [],
            "project_id": project_id,
            "reason": "طلب ناقص",
            "engineer_id": engineer_id,
        }
        response = requests.post(
            f"{BASE_URL}/api/pg/requests",
            headers={"Authorization": f"Bearer {supervisor_token}"},
            json=payload,
        )
        assert response.status_code == 400


class TestPurchaseOrderEdgeCases:
    def test_create_order_with_duplicate_items(self):
        supervisor_token = login(SUPERVISOR)
        engineer_token = login(ENGINEER)
        pm_token = login(PROCUREMENT_MANAGER)

        engineer_id = get_engineer_id(supervisor_token)
        project_id = create_project(supervisor_token)
        request_id = create_request(supervisor_token, project_id, engineer_id)
        approve_request(engineer_token, request_id)

        payload = {
            "request_id": request_id,
            "supplier_name": "مورد مكرر",
            "selected_items": [0, 0],
        }
        response = requests.post(
            f"{BASE_URL}/api/pg/purchase-orders",
            headers={"Authorization": f"Bearer {pm_token}"},
            json=payload,
        )
        assert response.status_code == 400


class TestDeliveryEdgeCases:
    def test_confirm_receipt_over_delivery(self):
        supervisor_token = login(SUPERVISOR)
        engineer_token = login(ENGINEER)
        pm_token = login(PROCUREMENT_MANAGER)
        delivery_token = login(DELIVERY_TRACKER)

        engineer_id = get_engineer_id(supervisor_token)
        project_id = create_project(supervisor_token)
        request_id = create_request(supervisor_token, project_id, engineer_id, quantity=3)
        approve_request(engineer_token, request_id)
        order_id = create_order(pm_token, request_id)

        approve_response = requests.post(
            f"{BASE_URL}/api/pg/purchase-orders/{order_id}/approve",
            headers={"Authorization": f"Bearer {pm_token}"},
        )
        assert approve_response.status_code == 200, f"Order approve failed: {approve_response.text}"

        order_response = requests.get(
            f"{BASE_URL}/api/pg/purchase-orders/{order_id}",
            headers={"Authorization": f"Bearer {pm_token}"},
        )
        assert order_response.status_code == 200, f"Order fetch failed: {order_response.text}"
        item_id = order_response.json()["items"][0]["id"]

        payload = {
            "supplier_receipt_number": f"RC-{uuid.uuid4().hex[:6]}",
            "items": [{"item_id": item_id, "quantity_delivered": 10}],
            "notes": "تسليم زائد",
        }
        response = requests.put(
            f"{BASE_URL}/api/pg/delivery-tracker/orders/{order_id}/confirm-receipt",
            headers={"Authorization": f"Bearer {delivery_token}"},
            json=payload,
        )
        assert response.status_code == 400
