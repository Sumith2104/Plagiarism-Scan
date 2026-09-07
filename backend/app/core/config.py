from pydantic_settings import BaseSettings
from typing import Optional

import os

def _get_default_database_url() -> str:
    env_val = os.getenv("DATABASE_URL")
    if env_val and env_val.strip():
        return env_val.strip()
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))
    if not os.path.exists(data_dir):
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
    try:
        os.makedirs(data_dir, exist_ok=True)
    except Exception:
        pass
    if os.path.exists(data_dir):
        db_path = os.path.join(data_dir, "plagiascan.db").replace("\\", "/")
        return f"sqlite:///{db_path}"
    return "sqlite:///./plagiascan.db"

class Settings(BaseSettings):
    PROJECT_NAME: str = "PlagiaScan"
    API_V1_STR: str = "/api/v1"
    
    # --- Fluxbase Database (primary) ---
    FLUXBASE_URL: str = "https://www.fluxbasedb.me/api/execute-sql"
    FLUXBASE_API_KEY: Optional[str] = None
    FLUXBASE_PROJECT_ID: Optional[str] = None

    # --- SQLite fallback (persisted in ./data/ if available) ---
    DATABASE_URL: str = _get_default_database_url()
    
    REDIS_URL: str = "redis://localhost:6379/0" 
    
    # Qdrant Vector DB
    QDRANT_URL: str = "local"
    QDRANT_API_KEY: Optional[str] = None
    
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # --- Email (for notifications) ---
    EMAIL_ADDRESS: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USE_SSL: bool = False

    @property
    def use_fluxbase(self) -> bool:
        """True if Fluxbase credentials are configured."""
        return bool(self.FLUXBASE_API_KEY and self.FLUXBASE_PROJECT_ID and
                    "YOUR_API_KEY" not in (self.FLUXBASE_API_KEY or ""))

    class Config:
        env_file = ".env"

settings = Settings()
