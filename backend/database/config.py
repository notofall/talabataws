"""
PostgreSQL Database Configuration for PlanetScale
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    """PostgreSQL configuration loaded from environment variables."""
    
    # Direct DATABASE_URL support (for deployment)
    database_url_direct: str = ""
    
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
        """Construct the database URL from individual components or use direct URL."""
        # Check for direct DATABASE_URL first (useful for deployment)
        direct_url = os.environ.get("DATABASE_URL", self.database_url_direct)
        if direct_url:
            # Convert postgres:// to postgresql+asyncpg://
            if direct_url.startswith("postgres://"):
                direct_url = direct_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif direct_url.startswith("postgresql://") and "+asyncpg" not in direct_url:
                direct_url = direct_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            # Replace sslmode with ssl for asyncpg compatibility
            direct_url = direct_url.replace("sslmode=require", "ssl=require")
            direct_url = direct_url.replace("sslmode=disable", "ssl=disable")
            return direct_url
        
        # Construct from individual components
        ssl_param = f"?ssl={self.postgres_sslmode}" if self.postgres_sslmode != "disable" else ""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            f"{ssl_param}"
        )


postgres_settings = PostgresSettings()
