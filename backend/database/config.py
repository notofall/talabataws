"""
PostgreSQL Database Configuration
Reads from saved config file first, then falls back to environment variables
"""
import os
import json
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Path to saved configuration
CONFIG_DIR = Path(__file__).parent.parent / "data"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_saved_config():
    """Load configuration from saved file if exists"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('database', {})
        except:
            pass
    return {}


class PostgresSettings(BaseSettings):
    """PostgreSQL configuration - reads from saved config or environment variables."""
    
    # Direct DATABASE_URL support (for deployment)
    database_url_direct: str = ""
    
    # Database Configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = ""
    postgres_db: str = "postgres"
    
    # SSL/TLS Configuration
    postgres_sslmode: str = "disable"
    
    # Connection Pool Configuration
    pool_size: int = 10
    max_overflow: int = 5
    pool_pre_ping: bool = True
    pool_recycle: int = 1800
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Load saved config and override if exists
        saved = load_saved_config()
        if saved:
            if saved.get('host'):
                self.postgres_host = saved['host']
            if saved.get('port'):
                self.postgres_port = int(saved['port'])
            if saved.get('database'):
                self.postgres_db = saved['database']
            if saved.get('username'):
                self.postgres_user = saved['username']
            if saved.get('password'):
                self.postgres_password = saved['password']
            if saved.get('ssl_mode'):
                self.postgres_sslmode = saved['ssl_mode']
    
    @property
    def database_url(self) -> str:
        """Construct the database URL from saved config or environment variables."""
        
        # First check for saved configuration
        saved = load_saved_config()
        if saved and saved.get('host'):
            host = saved.get('host', self.postgres_host)
            port = saved.get('port', self.postgres_port)
            database = saved.get('database', self.postgres_db)
            username = saved.get('username', self.postgres_user)
            password = saved.get('password', self.postgres_password)
            ssl_mode = saved.get('ssl_mode', self.postgres_sslmode)
            
            ssl_param = f"?ssl={ssl_mode}" if ssl_mode != "disable" else ""
            return (
                f"postgresql+asyncpg://{username}:{password}"
                f"@{host}:{port}/{database}"
                f"{ssl_param}"
            )
        
        # Check for direct DATABASE_URL (for deployment)
        direct_url = os.environ.get("DATABASE_URL", self.database_url_direct)
        if direct_url:
            if direct_url.startswith("postgres://"):
                direct_url = direct_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif direct_url.startswith("postgresql://") and "+asyncpg" not in direct_url:
                direct_url = direct_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            direct_url = direct_url.replace("sslmode=require", "ssl=require")
            direct_url = direct_url.replace("sslmode=disable", "ssl=disable")
            return direct_url
        
        # Construct from environment variables
        ssl_param = f"?ssl={self.postgres_sslmode}" if self.postgres_sslmode != "disable" else ""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            f"{ssl_param}"
        )


postgres_settings = PostgresSettings()
