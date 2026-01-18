"""
Test Suite for Database Setup Wizard APIs
Tests: /api/setup/status, /api/setup/presets, /api/setup/test-connection, /api/setup/complete-setup
"""
import pytest
import requests
import os

from tests.test_config import get_db_config

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://procure-hub-19.preview.emergentagent.com').rstrip('/')

VALID_DB_CONFIG = get_db_config()


def require_db_config():
    if not VALID_DB_CONFIG:
        pytest.skip("TEST_DB_CONFIG_JSON not set for setup connection tests")


class TestSetupStatus:
    """Tests for GET /api/setup/status"""
    
    def test_get_setup_status_returns_200(self):
        """Test that setup status endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/setup/status")
        assert response.status_code == 200
        
    def test_setup_status_response_structure(self):
        """Test that setup status has correct response structure"""
        response = requests.get(f"{BASE_URL}/api/setup/status")
        data = response.json()
        
        # Verify required fields exist
        assert "is_configured" in data
        assert "needs_setup" in data
        assert isinstance(data["is_configured"], bool)
        assert isinstance(data["needs_setup"], bool)
        
    def test_setup_status_shows_configured(self):
        """Test that system shows as configured (since DB is already connected)"""
        response = requests.get(f"{BASE_URL}/api/setup/status")
        data = response.json()
        
        # System should be configured since we have POSTGRES_HOST in env
        assert data["is_configured"] == True
        assert data["needs_setup"] == False
        
    def test_setup_status_includes_db_info(self):
        """Test that configured status includes database info"""
        response = requests.get(f"{BASE_URL}/api/setup/status")
        data = response.json()
        
        if data["is_configured"]:
            # Should have db_type and host when configured
            assert "db_type" in data
            assert "host" in data


class TestSetupPresets:
    """Tests for GET /api/setup/presets"""
    
    def test_get_presets_returns_200(self):
        """Test that presets endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/setup/presets")
        assert response.status_code == 200
        
    def test_presets_response_structure(self):
        """Test that presets has correct response structure"""
        response = requests.get(f"{BASE_URL}/api/setup/presets")
        data = response.json()
        
        assert "presets" in data
        assert isinstance(data["presets"], list)
        assert len(data["presets"]) > 0
        
    def test_presets_contain_required_fields(self):
        """Test that each preset has required fields"""
        response = requests.get(f"{BASE_URL}/api/setup/presets")
        data = response.json()
        
        for preset in data["presets"]:
            assert "name" in preset
            assert "host" in preset
            assert "port" in preset
            assert "ssl_mode" in preset
            assert "notes" in preset
            
    def test_presets_include_common_providers(self):
        """Test that presets include common cloud providers"""
        response = requests.get(f"{BASE_URL}/api/setup/presets")
        data = response.json()
        
        preset_names = [p["name"] for p in data["presets"]]
        
        # Should include at least some common providers
        assert "Supabase" in preset_names
        assert "AWS RDS" in preset_names
        assert "Local PostgreSQL" in preset_names


class TestConnectionTest:
    """Tests for POST /api/setup/test-connection"""
    
    def test_valid_connection_returns_success(self):
        """Test that valid credentials return success"""
        require_db_config()
        response = requests.post(
            f"{BASE_URL}/api/setup/test-connection",
            json=VALID_DB_CONFIG
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "message" in data
        assert "version" in data
        
    def test_valid_connection_returns_postgres_version(self):
        """Test that successful connection returns PostgreSQL version"""
        require_db_config()
        response = requests.post(
            f"{BASE_URL}/api/setup/test-connection",
            json=VALID_DB_CONFIG
        )
        data = response.json()
        
        assert "PostgreSQL" in data.get("version", "")
        
    def test_invalid_host_returns_failure(self):
        """Test that invalid host returns connection failure"""
        invalid_config = {
            "db_type": "local",
            "host": "invalid-host-that-does-not-exist",
            "port": 5432,
            "database": "test",
            "username": "test",
            "password": "test",
            "ssl_mode": "disable"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/setup/test-connection",
            json=invalid_config
        )
        assert response.status_code == 200  # API returns 200 with success=false
        
        data = response.json()
        assert data["success"] == False
        assert "message" in data
        assert data["error_type"] == "connection_failed"
        
    def test_invalid_credentials_returns_auth_error(self):
        """Test that invalid credentials return auth failure"""
        invalid_config = {
            "db_type": "cloud",
            "host": "eu-central-2.pg.psdb.cloud",
            "port": 6432,
            "database": "postgres",
            "username": "wrong_user",
            "password": "wrong_password",
            "ssl_mode": "require"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/setup/test-connection",
            json=invalid_config
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == False
        assert "message" in data
        
    def test_missing_required_fields_returns_422(self):
        """Test that missing required fields return validation error"""
        incomplete_config = {
            "db_type": "local",
            "host": "localhost"
            # Missing: port, database, username, password
        }
        
        response = requests.post(
            f"{BASE_URL}/api/setup/test-connection",
            json=incomplete_config
        )
        assert response.status_code == 422  # Validation error


class TestCompleteSetup:
    """Tests for POST /api/setup/complete-setup"""
    
    def test_complete_setup_without_admin_returns_success(self):
        """Test that complete setup without admin user works"""
        require_db_config()
        setup_config = {
            "database": VALID_DB_CONFIG,
            "admin_user": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/setup/complete-setup",
            json=setup_config
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["admin_created"] == False
        assert data["restart_required"] == True
        
    def test_complete_setup_response_structure(self):
        """Test that complete setup has correct response structure"""
        require_db_config()
        setup_config = {
            "database": VALID_DB_CONFIG,
            "admin_user": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/setup/complete-setup",
            json=setup_config
        )
        data = response.json()
        
        assert "success" in data
        assert "message" in data
        assert "admin_created" in data
        assert "restart_required" in data
        
    def test_complete_setup_with_invalid_db_returns_400(self):
        """Test that invalid database config returns 400"""
        setup_config = {
            "database": {
                "db_type": "local",
                "host": "invalid-host",
                "port": 5432,
                "database": "test",
                "username": "test",
                "password": "test",
                "ssl_mode": "disable"
            },
            "admin_user": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/setup/complete-setup",
            json=setup_config
        )
        assert response.status_code == 400
        
    def test_complete_setup_missing_database_returns_422(self):
        """Test that missing database config returns validation error"""
        setup_config = {
            "admin_user": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/setup/complete-setup",
            json=setup_config
        )
        assert response.status_code == 422


class TestSetupReset:
    """Tests for DELETE /api/setup/reset"""
    
    def test_reset_endpoint_exists(self):
        """Test that reset endpoint exists and responds"""
        response = requests.delete(f"{BASE_URL}/api/setup/reset")
        # Should return 200 regardless of whether config exists
        assert response.status_code == 200
        
    def test_reset_response_structure(self):
        """Test that reset has correct response structure"""
        response = requests.delete(f"{BASE_URL}/api/setup/reset")
        data = response.json()
        
        assert "success" in data
        assert "message" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
