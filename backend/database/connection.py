"""
PostgreSQL Database Connection Manager
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
from sqlalchemy.orm import declarative_base
import os
import logging

from .config import postgres_settings

logger = logging.getLogger(__name__)

# Create Base class for models
Base = declarative_base()

# Determine pool class based on environment
# Use NullPool for serverless/constrained environments
USE_NULL_POOL = os.environ.get("USE_NULL_POOL", "false").lower() == "true"

try:
    # Create async engine with connection pooling
    engine = create_async_engine(
        postgres_settings.database_url,
        poolclass=NullPool if USE_NULL_POOL else AsyncAdaptedQueuePool,
        pool_size=postgres_settings.pool_size if not USE_NULL_POOL else None,
        max_overflow=postgres_settings.max_overflow if not USE_NULL_POOL else None,
        pool_pre_ping=postgres_settings.pool_pre_ping,
        pool_recycle=postgres_settings.pool_recycle if not USE_NULL_POOL else None,
        echo=False,  # Set to True for SQL debugging
        connect_args={
            "ssl": "require" if "ssl" not in postgres_settings.database_url else None
        } if "ssl" not in postgres_settings.database_url else {}
    )
    logger.info(f"Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Alias for backward compatibility
async_session_pg = async_session_maker


async def init_postgres_db() -> None:
    """
    Initialize database by creating all tables defined in models.
    This should be called during application startup.
    """
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
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


async def close_postgres_db() -> None:
    """Close the database connection pool when the application shuts down."""
    await engine.dispose()
    logger.info("✅ PostgreSQL connection pool closed")
