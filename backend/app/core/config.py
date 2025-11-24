from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "PlagiaScan"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str = "postgresql://plagiascan:plagiascan_dev@localhost:5432/plagiascan"
    # DATABASE_URL: str = "sqlite:///./plagiascan.db"
    
    REDIS_URL: str = "redis://localhost:6379/0" 
    
    QDRANT_URL: str = "http://localhost:6333"
    # QDRANT_URL: str = ":memory:" # or path to local file
    QDRANT_API_KEY: Optional[str] = None
    
    SECRET_KEY: str = "supersecretkey" # Change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
