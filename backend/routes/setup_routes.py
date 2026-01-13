"""
Database Setup Wizard API
Allows configuring database connection on first run
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import json
from pathlib import Path
from datetime import datetime

setup_router = APIRouter(prefix="/api/setup", tags=["Setup"])

# Configuration file paths
CONFIG_FILE = Path("/app/backend/db_config.json")
ENV_FILE = Path("/app/backend/.env")
SETUP_COMPLETE_FILE = Path("/app/backend/.setup_complete")

class DatabaseConfig(BaseModel):
    """Database configuration model"""
    db_type: str  # "local" or "cloud"
    host: str
    port: int = 5432
    database: str
    username: str
    password: str
    ssl_mode: str = "require"  # "require" for cloud, "disable" for local
    
class AdminUserConfig(BaseModel):
    """Initial admin user configuration"""
    name: str = "مدير النظام"
    email: str
    password: str
    
class FullSetupConfig(BaseModel):
    """Complete setup configuration"""
    database: DatabaseConfig
    admin_user: Optional[AdminUserConfig] = None
    
class SetupStatus(BaseModel):
    """Setup status response"""
    is_configured: bool
    needs_setup: bool
    db_type: Optional[str] = None
    host: Optional[str] = None
    database: Optional[str] = None
    setup_date: Optional[str] = None


def get_config() -> Optional[dict]:
    """Read saved database configuration"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None


def save_config(config: dict) -> bool:
    """Save database configuration to JSON and .env"""
    try:
        # Save to JSON for reference
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Also update .env file for persistence across restarts
        env_content = []
        if ENV_FILE.exists():
            with open(ENV_FILE, 'r') as f:
                for line in f:
                    # Keep non-postgres lines
                    if not line.strip().startswith(('POSTGRES_', 'DATABASE_URL')):
                        env_content.append(line)
        
        # Add new database config
        ssl_param = "?sslmode=require" if config.get("ssl_mode") == "require" else ""
        db_url = f"postgresql+asyncpg://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}{ssl_param}"
        
        env_content.append(f"\n# Database Configuration - Auto-generated on {datetime.now().isoformat()}\n")
        env_content.append(f"POSTGRES_HOST={config['host']}\n")
        env_content.append(f"POSTGRES_PORT={config['port']}\n")
        env_content.append(f"POSTGRES_DB={config['database']}\n")
        env_content.append(f"POSTGRES_USER={config['username']}\n")
        env_content.append(f"POSTGRES_PASSWORD={config['password']}\n")
        env_content.append(f"POSTGRES_SSLMODE={config.get('ssl_mode', 'require')}\n")
        env_content.append(f"DATABASE_URL={db_url}\n")
        
        with open(ENV_FILE, 'w') as f:
            f.writelines(env_content)
        
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def mark_setup_complete():
    """Mark setup as complete"""
    with open(SETUP_COMPLETE_FILE, 'w') as f:
        f.write(datetime.now().isoformat())


def is_setup_complete() -> bool:
    """Check if setup has been completed"""
    return SETUP_COMPLETE_FILE.exists() or CONFIG_FILE.exists() or os.environ.get("POSTGRES_HOST")


@setup_router.get("/status")
async def get_setup_status():
    """Check if database is configured"""
    config = get_config()
    
    # Get setup date if available
    setup_date = None
    if SETUP_COMPLETE_FILE.exists():
        try:
            with open(SETUP_COMPLETE_FILE, 'r') as f:
                setup_date = f.read().strip()
        except:
            pass
    
    if config:
        return SetupStatus(
            is_configured=True,
            needs_setup=False,
            db_type=config.get("db_type"),
            host=config.get("host"),
            database=config.get("database"),
            setup_date=setup_date
        )
    
    # Check if using environment variables (backward compatibility)
    if os.environ.get("POSTGRES_HOST"):
        return SetupStatus(
            is_configured=True,
            needs_setup=False,
            db_type="env",
            host=os.environ.get("POSTGRES_HOST"),
            database=os.environ.get("POSTGRES_DB"),
            setup_date=setup_date
        )
    
    return SetupStatus(is_configured=False, needs_setup=True)


@setup_router.post("/test-connection")
async def test_database_connection(config: DatabaseConfig):
    """Test database connection without saving"""
    try:
        import asyncpg
        
        ssl_context = None
        if config.ssl_mode == "require":
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        # Try to connect
        conn = await asyncpg.connect(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.username,
            password=config.password,
            ssl=ssl_context if config.ssl_mode == "require" else None,
            timeout=10
        )
        
        # Test query
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        
        return {
            "success": True,
            "message": "تم الاتصال بنجاح!",
            "version": version
        }
        
    except asyncpg.InvalidCatalogNameError:
        return {
            "success": False,
            "message": f"قاعدة البيانات '{config.database}' غير موجودة",
            "error_type": "database_not_found"
        }
    except asyncpg.InvalidPasswordError:
        return {
            "success": False,
            "message": "اسم المستخدم أو كلمة المرور غير صحيحة",
            "error_type": "auth_failed"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"فشل الاتصال: {str(e)}",
            "error_type": "connection_failed"
        }


@setup_router.post("/configure")
async def configure_database(config: DatabaseConfig):
    """Save database configuration and initialize tables"""
    
    # First test the connection
    test_result = await test_database_connection(config)
    if not test_result["success"]:
        raise HTTPException(status_code=400, detail=test_result["message"])
    
    # Save configuration
    config_dict = {
        "db_type": config.db_type,
        "host": config.host,
        "port": config.port,
        "database": config.database,
        "username": config.username,
        "password": config.password,
        "ssl_mode": config.ssl_mode
    }
    
    if not save_config(config_dict):
        raise HTTPException(status_code=500, detail="فشل في حفظ الإعدادات")
    
    # Update environment variables for current session
    os.environ["POSTGRES_HOST"] = config.host
    os.environ["POSTGRES_PORT"] = str(config.port)
    os.environ["POSTGRES_DB"] = config.database
    os.environ["POSTGRES_USER"] = config.username
    os.environ["POSTGRES_PASSWORD"] = config.password
    os.environ["POSTGRES_SSLMODE"] = config.ssl_mode
    
    # Initialize database tables
    try:
        from database.models import Base
        
        # Recreate engine with new settings
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import AsyncAdaptedQueuePool
        
        ssl_param = "?ssl=require" if config.ssl_mode == "require" else ""
        db_url = f"postgresql+asyncpg://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}{ssl_param}"
        
        new_engine = create_async_engine(
            db_url,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            echo=False
        )
        
        # Create all tables
        async with new_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        await new_engine.dispose()
        
        # Mark setup as complete
        mark_setup_complete()
        
        return {
            "success": True,
            "message": "تم إعداد قاعدة البيانات بنجاح! يرجى إعادة تشغيل التطبيق.",
            "restart_required": True
        }
        
    except Exception as e:
        # Remove saved config on failure
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
        raise HTTPException(status_code=500, detail=f"فشل في إنشاء الجداول: {str(e)}")


@setup_router.post("/complete-setup")
async def complete_full_setup(setup_config: FullSetupConfig):
    """Complete setup with database config and optional admin user"""
    
    # First configure database
    db_config = setup_config.database
    
    # Test the connection
    test_result = await test_database_connection(db_config)
    if not test_result["success"]:
        raise HTTPException(status_code=400, detail=test_result["message"])
    
    # Save configuration
    config_dict = {
        "db_type": db_config.db_type,
        "host": db_config.host,
        "port": db_config.port,
        "database": db_config.database,
        "username": db_config.username,
        "password": db_config.password,
        "ssl_mode": db_config.ssl_mode
    }
    
    if not save_config(config_dict):
        raise HTTPException(status_code=500, detail="فشل في حفظ الإعدادات")
    
    # Update environment variables
    os.environ["POSTGRES_HOST"] = db_config.host
    os.environ["POSTGRES_PORT"] = str(db_config.port)
    os.environ["POSTGRES_DB"] = db_config.database
    os.environ["POSTGRES_USER"] = db_config.username
    os.environ["POSTGRES_PASSWORD"] = db_config.password
    os.environ["POSTGRES_SSLMODE"] = db_config.ssl_mode
    
    try:
        from database.models import Base, User
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from sqlalchemy.pool import AsyncAdaptedQueuePool
        from passlib.context import CryptContext
        from sqlalchemy import select
        import uuid
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        ssl_param = "?ssl=require" if db_config.ssl_mode == "require" else ""
        db_url = f"postgresql+asyncpg://{db_config.username}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}{ssl_param}"
        
        new_engine = create_async_engine(
            db_url,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            echo=False
        )
        
        # Create all tables
        async with new_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create admin user if provided
        admin_created = False
        access_token = None
        user_data = None
        if setup_config.admin_user:
            async_session = async_sessionmaker(new_engine, class_=AsyncSession, expire_on_commit=False)
            async with async_session() as session:
                # Check if user already exists
                result = await session.execute(
                    select(User).where(User.email == setup_config.admin_user.email)
                )
                existing_user = result.scalar_one_or_none()
                
                if not existing_user:
                    # Create admin user
                    user_id = str(uuid.uuid4())
                    admin_user = User(
                        id=user_id,
                        name=setup_config.admin_user.name,
                        email=setup_config.admin_user.email,
                        password_hash=pwd_context.hash(setup_config.admin_user.password),
                        role="system_admin",
                        is_active=True
                    )
                    session.add(admin_user)
                    await session.commit()
                    admin_created = True
                    
                    # Generate access token
                    from datetime import datetime, timedelta
                    from jose import jwt
                    
                    SECRET_KEY = os.environ.get("SECRET_KEY", "default-secret-key-change-in-production")
                    ALGORITHM = "HS256"
                    ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
                    
                    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                    token_data = {
                        "sub": setup_config.admin_user.email,
                        "user_id": user_id,
                        "role": "system_admin",
                        "name": setup_config.admin_user.name,
                        "exp": expire
                    }
                    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
                    user_data = {
                        "id": user_id,
                        "name": setup_config.admin_user.name,
                        "email": setup_config.admin_user.email,
                        "role": "system_admin"
                    }
        
        await new_engine.dispose()
        
        # Mark setup as complete
        mark_setup_complete()
        
        return {
            "success": True,
            "message": "تم إعداد النظام بنجاح!",
            "admin_created": admin_created,
            "access_token": access_token,
            "user": user_data,
            "restart_required": False
        }
        
    except Exception as e:
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
        raise HTTPException(status_code=500, detail=f"فشل في إعداد النظام: {str(e)}")


@setup_router.delete("/reset")
async def reset_configuration():
    """Reset database configuration (for troubleshooting)"""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
        return {"success": True, "message": "تم إعادة ضبط الإعدادات"}
    return {"success": False, "message": "لا توجد إعدادات محفوظة"}


# Cloud provider presets
@setup_router.get("/presets")
async def get_cloud_presets():
    """Get preset configurations for popular cloud providers"""
    return {
        "presets": [
            {
                "name": "PlanetScale",
                "host": "aws.connect.psdb.cloud",
                "port": 3306,
                "ssl_mode": "require",
                "notes": "استخدم بيانات الاتصال من لوحة PlanetScale"
            },
            {
                "name": "Supabase",
                "host": "db.xxxxx.supabase.co",
                "port": 5432,
                "ssl_mode": "require",
                "notes": "استبدل xxxxx بمعرف مشروعك"
            },
            {
                "name": "AWS RDS",
                "host": "your-instance.region.rds.amazonaws.com",
                "port": 5432,
                "ssl_mode": "require",
                "notes": "استخدم Endpoint من AWS Console"
            },
            {
                "name": "Google Cloud SQL",
                "host": "your-instance-ip",
                "port": 5432,
                "ssl_mode": "require",
                "notes": "فعّل Public IP واستخدم SSL"
            },
            {
                "name": "Local PostgreSQL",
                "host": "localhost",
                "port": 5432,
                "ssl_mode": "disable",
                "notes": "تأكد من تثبيت PostgreSQL على الخادم"
            }
        ]
    }
