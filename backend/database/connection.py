"""
PostgreSQL Database Connection Manager
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy.orm import declarative_base

from .config import postgres_settings

# Create Base class for models
Base = declarative_base()

# Create async engine with connection pooling
engine = create_async_engine(
    postgres_settings.database_url,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=postgres_settings.pool_size,
    max_overflow=postgres_settings.max_overflow,
    pool_pre_ping=postgres_settings.pool_pre_ping,
    pool_recycle=postgres_settings.pool_recycle,
    echo=False,  # Set to True for SQL debugging
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_postgres_db() -> None:
    """
    Initialize database by creating all tables defined in models.
    This should be called during application startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ PostgreSQL tables initialized successfully")


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
    print("✅ PostgreSQL connection pool closed")
