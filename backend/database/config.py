"""
PostgreSQL Database Configuration for PlanetScale
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    """PostgreSQL configuration loaded from environment variables."""
    
    # Database Configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = ""
    postgres_db: str = "postgres"
    
    # SSL/TLS Configuration for PlanetScale
    postgres_sslmode: str = "require"
    
    # Connection Pool Configuration - Balanced for moderate usage
    pool_size: int = 10  # 10 connections ready
    max_overflow: int = 5  # 5 extra if needed
    pool_pre_ping: bool = True
    pool_recycle: int = 1800  # Recycle connections every 30 minutes
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def database_url(self) -> str:
        """Construct the database URL from individual components."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            f"?ssl=require"
        )


postgres_settings = PostgresSettings()
