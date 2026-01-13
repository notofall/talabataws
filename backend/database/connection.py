"""
PostgreSQL Database Connection Manager
Supports dynamic configuration from setup wizard
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
from sqlalchemy.orm import declarative_base
import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Create Base class for models
Base = declarative_base()

# Path to saved configuration
CONFIG_DIR = Path(__file__).parent.parent / "data"
CONFIG_FILE = CONFIG_DIR / "config.json"

def get_database_url():
    """Get database URL from saved config or environment variables"""
    
    # First check for saved configuration from setup wizard
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                db_config = config.get('database', {})
                
                if db_config.get('host'):
                    host = db_config.get('host')
                    port = db_config.get('port', 5432)
                    database = db_config.get('database', 'talabat_db')
                    username = db_config.get('username', 'postgres')
                    password = db_config.get('password', '')
                    ssl_mode = db_config.get('ssl_mode', 'disable')
                    
                    ssl_param = f"?ssl={ssl_mode}" if ssl_mode != "disable" else ""
                    url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}{ssl_param}"
                    logger.info(f"Using saved database config: {host}:{port}/{database}")
                    return url
        except Exception as e:
            logger.warning(f"Could not load saved config: {e}")
    
    # Fall back to environment variables
    from .config import postgres_settings
    logger.info("Using environment variables for database config")
    return postgres_settings.database_url


# Determine pool class based on environment
USE_NULL_POOL = os.environ.get("USE_NULL_POOL", "false").lower() == "true"

# Global engine variable - will be created on first use or after setup
_engine = None
_async_session_maker = None


def get_engine():
    """Get or create the database engine"""
    global _engine
    
    if _engine is None:
        database_url = get_database_url()
        
        try:
            from .config import postgres_settings
            
            _engine = create_async_engine(
                database_url,
                poolclass=NullPool if USE_NULL_POOL else AsyncAdaptedQueuePool,
                pool_size=postgres_settings.pool_size if not USE_NULL_POOL else None,
                max_overflow=postgres_settings.max_overflow if not USE_NULL_POOL else None,
                pool_pre_ping=postgres_settings.pool_pre_ping,
                pool_recycle=postgres_settings.pool_recycle if not USE_NULL_POOL else None,
                echo=False,
            )
            logger.info("Database engine created successfully")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise
    
    return _engine


def get_session_maker():
    """Get or create the session maker"""
    global _async_session_maker
    
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    
    return _async_session_maker


def reset_engine():
    """Reset the engine to reload configuration"""
    global _engine, _async_session_maker
    if _engine:
        # Note: This should be done carefully in async context
        pass
    _engine = None
    _async_session_maker = None
    logger.info("Database engine reset - will reload config on next connection")


# Create initial engine
try:
    engine = get_engine()
except Exception as e:
    logger.warning(f"Initial engine creation failed (may need setup): {e}")
    engine = None

# Session maker - will be created when engine is available
async_session_maker = None
if engine:
    async_session_maker = get_session_maker()

# Alias for backward compatibility
async_session_pg = async_session_maker


async def init_postgres_db() -> None:
    """
    Initialize database by creating all tables defined in models.
    This should be called during application startup.
    """
    global engine, async_session_maker, async_session_pg
    
    # Ensure engine exists
    if engine is None:
        engine = get_engine()
        async_session_maker = get_session_maker()
        async_session_pg = async_session_maker
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ PostgreSQL tables initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize PostgreSQL tables: {e}")
        raise


async def get_postgres_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that provides a database session to routes.
    The session is automatically closed after the request completes.
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


async def close_postgres_db() -> None:
    """Close the database connection pool when the application shuts down."""
    global engine
    if engine:
        await engine.dispose()
        logger.info("✅ PostgreSQL connection pool closed")
