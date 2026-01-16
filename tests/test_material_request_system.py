"""
Test Suite for Material Request Management System APIs
Tests: Authentication, Users, Projects, Suppliers, Requests, Orders, Domain Settings
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://planner-tool-6.preview.emergentagent.com').rstrip('/')

# Test credentials from the request
TEST_CREDENTIALS = {
    "system_admin": {"email": "admin@system.com", "password": "123456"},
    "procurement_manager": {"email": "notofall@gmail.com", "password": "123456"},
    "general_manager": {"email": "md@gmail.com", "password": "123456"},
    "engineer": {"email": "engineer1@test.com", "password": "123456"},
    "supervisor": {"email": "supervisor1@test.com", "password": "123456"}
}


class TestHealthCheck:
    """Tests for health check endpoints"""
    
    def test_root_health_check(self):
        """Test root health endpoint - returns HTML (frontend) or JSON"""
        response = requests.get(f"{BASE_URL}/health")
        # Root /health may return frontend HTML or backend JSON depending on routing
        assert response.status_code == 200
        
    def test_pg_health_check(self):
        """Test PostgreSQL health endpoint"""
        response = requests.get(f"{BASE_URL}/api/pg/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "postgresql"


class TestAuthentication:
    """Tests for authentication endpoints"""
    
    def test_login_system_admin(self):
        """Test login as system admin"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["system_admin"]
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "system_admin"
        
    def test_login_procurement_manager(self):
        """Test login as procurement manager"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["procurement_manager"]
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "procurement_manager"
        
    def test_login_general_manager(self):
        """Test login as general manager"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["general_manager"]
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "general_manager"
        
    def test_login_engineer(self):
        """Test login as engineer"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["engineer"]
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "engineer"
        
    def test_login_supervisor(self):
        """Test login as supervisor"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["supervisor"]
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "supervisor"
        
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        
    def test_get_current_user(self):
        """Test getting current user info"""
        # First login
        login_response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["system_admin"]
        )
        token = login_response.json()["access_token"]
        
        # Get current user
        response = requests.get(
            f"{BASE_URL}/api/pg/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_CREDENTIALS["system_admin"]["email"]


class TestSystemAdminDashboard:
    """Tests for system admin dashboard APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as system admin before each test"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["system_admin"]
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_system_stats(self):
        """Test getting system statistics"""
        response = requests.get(
            f"{BASE_URL}/api/pg/sysadmin/stats",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "users_count" in data
        assert "projects_count" in data
        assert "suppliers_count" in data
        assert "requests_count" in data
        assert "orders_count" in data
        assert "total_amount" in data
        
    def test_get_all_users(self):
        """Test getting all users list"""
        response = requests.get(
            f"{BASE_URL}/api/pg/admin/users",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_get_company_settings(self):
        """Test getting company settings"""
        response = requests.get(
            f"{BASE_URL}/api/pg/sysadmin/company-settings",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should have company setting keys
        assert isinstance(data, dict)


class TestDomainSettings:
    """Tests for domain configuration APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as system admin before each test"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["system_admin"]
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_domain_status(self):
        """Test getting domain status"""
        response = requests.get(
            f"{BASE_URL}/api/pg/domain/status",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_configured" in data
        
    def test_get_dns_instructions(self):
        """Test getting DNS instructions"""
        response = requests.get(
            f"{BASE_URL}/api/pg/domain/dns-instructions",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "instructions" in data


class TestProjects:
    """Tests for project management APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as supervisor before each test (only supervisor can create projects)"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["supervisor"]
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_projects_list(self):
        """Test getting projects list"""
        response = requests.get(
            f"{BASE_URL}/api/pg/projects",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_create_project(self):
        """Test creating a new project - supervisor only"""
        project_data = {
            "name": f"TEST_Project_{uuid.uuid4().hex[:8]}",
            "owner_name": "Test Owner",
            "description": "Test project description",
            "location": "Test Location"
        }
        response = requests.post(
            f"{BASE_URL}/api/pg/projects",
            json=project_data,
            headers=self.headers
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == project_data["name"]


class TestSuppliers:
    """Tests for supplier management APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as procurement manager before each test"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["procurement_manager"]
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_suppliers_list(self):
        """Test getting suppliers list"""
        response = requests.get(
            f"{BASE_URL}/api/pg/suppliers",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_create_supplier(self):
        """Test creating a new supplier"""
        supplier_data = {
            "name": f"TEST_Supplier_{uuid.uuid4().hex[:8]}",
            "contact_person": "Test Contact",
            "phone": "0501234567",
            "email": "test@supplier.com",
            "address": "Test Address"
        }
        response = requests.post(
            f"{BASE_URL}/api/pg/suppliers",
            json=supplier_data,
            headers=self.headers
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == supplier_data["name"]


class TestBudgetCategories:
    """Tests for budget category APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as procurement manager before each test"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["procurement_manager"]
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_default_budget_categories(self):
        """Test getting default budget categories"""
        response = requests.get(
            f"{BASE_URL}/api/pg/default-budget-categories",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_get_budget_categories(self):
        """Test getting budget categories"""
        response = requests.get(
            f"{BASE_URL}/api/pg/budget-categories",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestMaterialRequests:
    """Tests for material request APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as supervisor before each test"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["supervisor"]
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_requests_list(self):
        """Test getting material requests list"""
        response = requests.get(
            f"{BASE_URL}/api/pg/requests",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestEngineerDashboard:
    """Tests for engineer dashboard APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as engineer before each test"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["engineer"]
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_engineer_requests(self):
        """Test getting requests assigned to engineer"""
        response = requests.get(
            f"{BASE_URL}/api/pg/requests",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestProcurementDashboard:
    """Tests for procurement manager dashboard APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as procurement manager before each test"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["procurement_manager"]
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_requests_list(self):
        """Test getting requests list for procurement manager"""
        response = requests.get(
            f"{BASE_URL}/api/pg/requests",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_get_purchase_orders(self):
        """Test getting purchase orders list"""
        response = requests.get(
            f"{BASE_URL}/api/pg/purchase-orders",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestGeneralManagerDashboard:
    """Tests for general manager dashboard APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as general manager before each test"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["general_manager"]
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_pending_orders(self):
        """Test getting orders pending GM approval"""
        response = requests.get(
            f"{BASE_URL}/api/pg/gm/pending-orders",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_get_all_orders_gm_approved(self):
        """Test getting GM approved orders"""
        response = requests.get(
            f"{BASE_URL}/api/pg/gm/all-orders?approval_type=gm_approved",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_get_all_orders_manager_approved(self):
        """Test getting manager approved orders"""
        response = requests.get(
            f"{BASE_URL}/api/pg/gm/all-orders?approval_type=manager_approved",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestSystemTools:
    """Tests for system tools APIs - routes under /api/pg/system/"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as system admin before each test"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["system_admin"]
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_system_info(self):
        """Test getting system information"""
        response = requests.get(
            f"{BASE_URL}/api/pg/system/info",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        
    def test_get_database_stats(self):
        """Test getting database statistics"""
        response = requests.get(
            f"{BASE_URL}/api/pg/system/database-stats",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "tables" in data
        
    def test_get_system_logs(self):
        """Test getting system logs"""
        response = requests.get(
            f"{BASE_URL}/api/pg/system/logs",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        
    def test_check_updates(self):
        """Test checking for updates"""
        response = requests.get(
            f"{BASE_URL}/api/pg/system/check-updates",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "current_version" in data


class TestAuditLogs:
    """Tests for audit log APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as system admin before each test"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["system_admin"]
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_audit_logs(self):
        """Test getting audit logs"""
        response = requests.get(
            f"{BASE_URL}/api/pg/audit-logs",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestSettings:
    """Tests for settings APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as procurement manager before each test"""
        response = requests.post(
            f"{BASE_URL}/api/pg/auth/login",
            json=TEST_CREDENTIALS["procurement_manager"]
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_settings(self):
        """Test getting system settings"""
        response = requests.get(
            f"{BASE_URL}/api/pg/settings",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
