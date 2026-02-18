import os
from pathlib import Path
from typing import Optional
from functools import lru_cache
from pydantic import BaseModel, Field

class Settings(BaseModel):
    # App
    APP_NAME: str = "QuantLogic Framework"
    VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8010
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATA_DIR: Path = Path("data")
    DB_NAME: str = "qlm.db"

    # Security
    SECRET_KEY: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", "dev_secret_key"))

    # AI Defaults (if env vars are used instead of DB)
    DEFAULT_PROVIDER: Optional[str] = os.getenv("DEFAULT_PROVIDER")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    @property
    def DB_PATH(self) -> str:
        return str(self.DATA_DIR / self.DB_NAME)

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
