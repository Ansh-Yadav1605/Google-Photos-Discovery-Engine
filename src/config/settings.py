"""Application configuration and settings management using modern Pydantic V2."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project paths
    BASE_DIR: Path = BASE_DIR
    DATA_RAW_DIR: Path = BASE_DIR / "data" / "raw"
    DATA_PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    DATA_ANALYSIS_DIR: Path = BASE_DIR / "data" / "analysis"

    # Database
    DATABASE_URL: str = Field(
        default=f"sqlite:///{BASE_DIR / 'data' / 'analysis' / 'discovery.db'}"
    )

    # Groq LLM API
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")

    # Optional Live Credentials
    REDDIT_CLIENT_ID: str = Field(default="")
    REDDIT_CLIENT_SECRET: str = Field(default="")
    REDDIT_USER_AGENT: str = Field(
        default="GooglePhotosResearchBot/1.0 (NextLeap Graduation Project)"
    )
    YOUTUBE_API_KEY: str = Field(default="")

    # API Server Settings
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")
    CORS_ORIGINS: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173"
    )
    LOG_LEVEL: str = Field(default="INFO")


settings = Settings()
