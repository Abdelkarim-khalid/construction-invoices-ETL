"""Application configuration and settings"""

import os
from typing import Optional


class Settings:
    """Application settings and configuration"""
    
    # Database
    SQLITE_FILE_NAME: str = "construction_system.db"
    DATABASE_URL: str = f"sqlite:///{SQLITE_FILE_NAME}"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Construction Cost Control API"
    
    # File Upload
    UPLOAD_DIR: str = "temp_uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # CORS
    ALLOWED_ORIGINS: list = ["*"]
    
    def __init__(self):
        """Initialize settings, can load from environment variables"""
        # يمكن تحميل من environment variables لاحقاً
        env_db_url = os.getenv("DATABASE_URL")
        if env_db_url:
            self.DATABASE_URL = env_db_url


# Singleton instance
settings = Settings()
