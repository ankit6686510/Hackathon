"""
Configuration management for FixGenie API
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = "FixGenie API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=True, env="RELOAD")
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS
    cors_origins_str: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
        env="CORS_ORIGINS"
    )
    
    # AI Services
    gemini_api_key: str = Field(env="GEMINI_API_KEY")
    gemini_embed_model: str = Field(default="text-embedding-004", env="GEMINI_EMBED_MODEL")
    gemini_chat_model: str = Field(default="gemini-1.5-flash", env="GEMINI_CHAT_MODEL")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # Vector Database
    pinecone_api_key: str = Field(env="PINECONE_API_KEY")
    pinecone_index: str = Field(default="juspay-issues", env="PINECONE_INDEX")
    pinecone_environment: str = Field(default="gcp-starter", env="PINECONE_ENVIRONMENT")
    
    # Database
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    postgres_user: str = Field(default="fixgenie", env="POSTGRES_USER")
    postgres_password: str = Field(default="password", env="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="fixgenie", env="POSTGRES_DB")
    
    # Redis Cache
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Search Configuration
    default_top_k: int = Field(default=3, env="DEFAULT_TOP_K")
    max_top_k: int = Field(default=10, env="MAX_TOP_K")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    
    # Cache TTL (seconds)
    cache_ttl_search: int = Field(default=300, env="CACHE_TTL_SEARCH")  # 5 minutes
    cache_ttl_embeddings: int = Field(default=3600, env="CACHE_TTL_EMBEDDINGS")  # 1 hour
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from string"""
        return [origin.strip() for origin in self.cors_origins_str.split(",")]
    
    @property
    def database_url_computed(self) -> str:
        """Compute database URL if not provided directly"""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def redis_url_computed(self) -> str:
        """Compute Redis URL if not provided directly"""
        if self.redis_url:
            return self.redis_url
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env


# Global settings instance
settings = Settings()
