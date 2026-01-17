import json
import os


DEFAULT_PASSWORD = os.environ.get("TEST_DEFAULT_PASSWORD", "123456")

ROLE_EMAILS = {
    "system_admin": os.environ.get("TEST_SYSTEM_ADMIN_EMAIL", "admin@system.com"),
    "procurement_manager": os.environ.get("TEST_PROCUREMENT_MANAGER_EMAIL", "notofall@gmail.com"),
    "general_manager": os.environ.get("TEST_GENERAL_MANAGER_EMAIL", "md@test.com"),
    "quantity_engineer": os.environ.get("TEST_QUANTITY_ENGINEER_EMAIL", "q1@test.com"),
    "engineer": os.environ.get("TEST_ENGINEER_EMAIL", "en1@test.com"),
    "supervisor": os.environ.get("TEST_SUPERVISOR_EMAIL", "a223@test.com"),
    "printer": os.environ.get("TEST_PRINTER_EMAIL", "p1@test.com"),
    "delivery_tracker": os.environ.get("TEST_DELIVERY_TRACKER_EMAIL", "d1@test.com"),
}

ROLE_PASSWORDS = {
    "system_admin": os.environ.get("TEST_SYSTEM_ADMIN_PASSWORD", DEFAULT_PASSWORD),
    "procurement_manager": os.environ.get("TEST_PROCUREMENT_MANAGER_PASSWORD", DEFAULT_PASSWORD),
    "general_manager": os.environ.get("TEST_GENERAL_MANAGER_PASSWORD", DEFAULT_PASSWORD),
    "quantity_engineer": os.environ.get("TEST_QUANTITY_ENGINEER_PASSWORD", DEFAULT_PASSWORD),
    "engineer": os.environ.get("TEST_ENGINEER_PASSWORD", DEFAULT_PASSWORD),
    "supervisor": os.environ.get("TEST_SUPERVISOR_PASSWORD", DEFAULT_PASSWORD),
    "printer": os.environ.get("TEST_PRINTER_PASSWORD", DEFAULT_PASSWORD),
    "delivery_tracker": os.environ.get("TEST_DELIVERY_TRACKER_PASSWORD", DEFAULT_PASSWORD),
}


def get_credentials(role: str) -> dict:
    email = ROLE_EMAILS.get(role)
    password = ROLE_PASSWORDS.get(role, DEFAULT_PASSWORD)
    return {"email": email, "password": password}


def get_db_config() -> dict | None:
    raw = os.environ.get("TEST_DB_CONFIG_JSON")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
