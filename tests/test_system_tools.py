"""
System Tools API Tests
Tests for System Admin Dashboard - System Tools Tab
Endpoints: /api/pg/system/info, /api/pg/system/check-updates, /api/pg/system/database-stats, /api/pg/system/logs
"""
import pytest
import requests
import os

from tests.test_config import get_credentials

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials for system admin
SYSTEM_ADMIN = get_credentials("system_admin")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for system admin"""
    response = requests.post(
        f"{BASE_URL}/api/pg/auth/login",
        json=SYSTEM_ADMIN
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    assert data["user"]["role"] == "system_admin", "User is not system_admin"
    return data["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Get authorization headers"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestSystemAdminLogin:
    """Test system admin authentication"""
    
    def test_login_success(self):
        """Test successful login as system admin"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=SYSTEM_ADMIN
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == SYSTEM_ADMIN["email"]
        assert data["user"]["role"] == "system_admin"
        assert data["user"]["is_active"] == True
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json={"email": "wrong@email.com", "password": "wrongpassword"}
        )
        assert response.status_code in [401, 400]


class TestSystemInfo:
    """Test GET /api/pg/system/info endpoint"""
    
    def test_get_system_info_success(self, auth_headers):
        """Test getting system information"""
        response = requests.get(
            f"{BASE_URL}/api/pg/system/info",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify version info
        assert "version" in data
        assert "build_date" in data
        assert "release_notes" in data
        assert isinstance(data["release_notes"], list)
        
        # Verify server info
        assert "server" in data
        server = data["server"]
        assert "os" in server
        assert "os_version" in server
        assert "python_version" in server
        assert "hostname" in server
        
        # Verify resources info
        assert "resources" in data
        resources = data["resources"]
        assert "cpu_percent" in resources
        assert "memory_total_gb" in resources
        assert "memory_used_gb" in resources
        assert "memory_percent" in resources
        assert "disk_total_gb" in resources
        assert "disk_used_gb" in resources
        assert "disk_percent" in resources
        
        # Verify data types
        assert isinstance(resources["cpu_percent"], (int, float))
        assert isinstance(resources["memory_percent"], (int, float))
        assert isinstance(resources["disk_percent"], (int, float))
    
    def test_get_system_info_unauthorized(self):
        """Test getting system info without authentication"""
        response = requests.get(f"{BASE_URL}/api/pg/system/info")
        assert response.status_code in [401, 403]


class TestCheckUpdates:
    """Test GET /api/pg/system/check-updates endpoint"""
    
    def test_check_updates_success(self, auth_headers):
        """Test checking for system updates"""
        response = requests.get(
            f"{BASE_URL}/api/pg/system/check-updates",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify update info structure
        assert "current_version" in data
        assert "latest_version" in data
        assert "update_available" in data
        assert "release_notes" in data
        
        # Verify data types
        assert isinstance(data["current_version"], str)
        assert isinstance(data["latest_version"], str)
        assert isinstance(data["update_available"], bool)
        assert isinstance(data["release_notes"], list)
        
        # If update available, download_url should be present
        if data["update_available"]:
            assert "download_url" in data
    
    def test_check_updates_unauthorized(self):
        """Test checking updates without authentication"""
        response = requests.get(f"{BASE_URL}/api/pg/system/check-updates")
        assert response.status_code in [401, 403]


class TestDatabaseStats:
    """Test GET /api/pg/system/database-stats endpoint"""
    
    def test_get_database_stats_success(self, auth_headers):
        """Test getting database statistics"""
        response = requests.get(
            f"{BASE_URL}/api/pg/system/database-stats",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify tables stats
        assert "tables" in data
        tables = data["tables"]
        assert "users" in tables
        assert "purchase_orders" in tables
        assert "material_requests" in tables
        assert "projects" in tables
        assert "suppliers" in tables
        
        # Verify data types - all should be integers
        assert isinstance(tables["users"], int)
        assert isinstance(tables["purchase_orders"], int)
        assert isinstance(tables["material_requests"], int)
        assert isinstance(tables["projects"], int)
        assert isinstance(tables["suppliers"], int)
        
        # Verify database type
        assert "database_type" in data
        assert data["database_type"] == "PostgreSQL"
        
        # Verify connection pool info
        assert "connection_pool" in data
        pool = data["connection_pool"]
        assert "size" in pool
        assert "max_overflow" in pool
    
    def test_get_database_stats_unauthorized(self):
        """Test getting database stats without authentication"""
        response = requests.get(f"{BASE_URL}/api/pg/system/database-stats")
        assert response.status_code in [401, 403]


class TestSystemLogs:
    """Test GET /api/pg/system/logs endpoint"""
    
    def test_get_system_logs_success(self, auth_headers):
        """Test getting system logs"""
        response = requests.get(
            f"{BASE_URL}/api/pg/system/logs",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "logs" in data
        assert "stats" in data
        assert isinstance(data["logs"], list)
        
        # Verify stats structure
        stats = data["stats"]
        assert "total" in stats
        assert "errors" in stats
        assert "warnings" in stats
        assert "info" in stats
        assert "today" in stats
        
        # Verify data types
        assert isinstance(stats["total"], int)
        assert isinstance(stats["errors"], int)
        assert isinstance(stats["warnings"], int)
        assert isinstance(stats["info"], int)
        assert isinstance(stats["today"], int)
    
    def test_get_system_logs_with_level_filter(self, auth_headers):
        """Test getting system logs with level filter"""
        response = requests.get(
            f"{BASE_URL}/api/pg/system/logs?level=ERROR",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "stats" in data
    
    def test_get_system_logs_with_limit(self, auth_headers):
        """Test getting system logs with limit"""
        response = requests.get(
            f"{BASE_URL}/api/pg/system/logs?limit=50",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert len(data["logs"]) <= 50
    
    def test_get_system_logs_unauthorized(self):
        """Test getting system logs without authentication"""
        response = requests.get(f"{BASE_URL}/api/pg/system/logs")
        assert response.status_code in [401, 403]


class TestAddLogEntry:
    """Test POST /api/pg/system/logs/add endpoint"""
    
    def test_add_log_entry_info(self):
        """Test adding an INFO log entry"""
        response = requests.post(
            f"{BASE_URL}/api/pg/system/logs/add",
            params={
                "level": "INFO",
                "source": "TestSuite",
                "message": "Test log entry from pytest"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_add_log_entry_warning(self):
        """Test adding a WARNING log entry"""
        response = requests.post(
            f"{BASE_URL}/api/pg/system/logs/add",
            params={
                "level": "WARNING",
                "source": "TestSuite",
                "message": "Test warning from pytest"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_add_log_entry_error(self):
        """Test adding an ERROR log entry"""
        response = requests.post(
            f"{BASE_URL}/api/pg/system/logs/add",
            params={
                "level": "ERROR",
                "source": "TestSuite",
                "message": "Test error from pytest",
                "details": "This is a test error detail"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


class TestApplyUpdate:
    """Test POST /api/pg/system/apply-update endpoint"""
    
    def test_apply_update_success(self, auth_headers):
        """Test applying system update (placeholder functionality)"""
        response = requests.post(
            f"{BASE_URL}/api/pg/system/apply-update",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data
        # Since this is a placeholder, it should return manual steps
        if "manual_steps" in data:
            assert isinstance(data["manual_steps"], list)
    
    def test_apply_update_unauthorized(self):
        """Test applying update without authentication"""
        response = requests.post(f"{BASE_URL}/api/pg/system/apply-update")
        assert response.status_code in [401, 403]


class TestNonAdminAccess:
    """Test that non-admin users cannot access system endpoints"""
    
    @pytest.fixture
    def non_admin_token(self):
        """Try to get a non-admin token (if available)"""
        # Try to login as a supervisor or engineer
        test_users = [
            get_credentials("supervisor"),
            get_credentials("engineer"),
        ]
        for user in test_users:
            response = requests.post(
                f"{BASE_URL}/api/pg/auth/login",
                json=user
            )
            if response.status_code == 200:
                data = response.json()
                if data["user"]["role"] != "system_admin":
                    return data["access_token"]
        pytest.skip("No non-admin user available for testing")
    
    def test_system_info_forbidden_for_non_admin(self, non_admin_token):
        """Test that non-admin cannot access system info"""
        response = requests.get(
            f"{BASE_URL}/api/pg/system/info",
            headers={"Authorization": f"Bearer {non_admin_token}"}
        )
        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
