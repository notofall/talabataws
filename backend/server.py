"""
نظام إدارة طلبات المواد - Material Request Management System
PostgreSQL Backend - Clean Version
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
import os
import logging

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app
app = FastAPI(
    title="نظام إدارة طلبات المواد",
    description="Material Request Management System - PostgreSQL Backend",
    version="2.0.0"
)

# Health check endpoint at root level (for Kubernetes)
@app.get("/health")
async def root_health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes"""
    return {"status": "healthy", "database": "PostgreSQL"}

# ==================== PostgreSQL Routes ====================
from routes.pg_auth_routes import pg_auth_router
from routes.pg_projects_routes import pg_projects_router
from routes.pg_suppliers_routes import pg_suppliers_router
from routes.pg_budget_routes import pg_budget_router
from routes.pg_requests_routes import pg_requests_router
from routes.pg_orders_routes import pg_orders_router
from routes.pg_settings_routes import pg_settings_router
from routes.pg_sysadmin_routes import pg_sysadmin_router
from routes.pg_catalog_routes import pg_catalog_router

# Include all PostgreSQL routers
app.include_router(pg_auth_router)
app.include_router(pg_projects_router)
app.include_router(pg_suppliers_router)
app.include_router(pg_budget_router)
app.include_router(pg_requests_router)
app.include_router(pg_orders_router)
app.include_router(pg_settings_router)
app.include_router(pg_sysadmin_router)
app.include_router(pg_catalog_router)

# ==================== CORS Configuration ====================
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Logging Configuration ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== Startup & Shutdown Events ====================
@app.on_event("startup")
async def startup_db_client():
    """Initialize PostgreSQL database on startup"""
    logger.info("🚀 Starting Material Request Management System...")
    
    # Initialize PostgreSQL tables
    from database import init_postgres_db
    await init_postgres_db()
    
    logger.info("✅ PostgreSQL database initialized successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connections on shutdown"""
    logger.info("🛑 Shutting down...")
    
    # Close PostgreSQL connection
    from database import close_postgres_db
    await close_postgres_db()
    
    logger.info("✅ Database connections closed")
