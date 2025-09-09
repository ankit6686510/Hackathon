"""
Database connection and session management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import redis.asyncio as redis
from typing import AsyncGenerator
import structlog

from app.config import settings

logger = structlog.get_logger()

# Database Engine
engine = create_async_engine(
    settings.database_url_computed,
    echo=settings.debug,
    poolclass=NullPool if settings.environment == "test" else None,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Session Factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Redis Connection
redis_client = None


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis() -> redis.Redis:
    """Get Redis connection"""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.redis_url_computed,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return redis_client


async def init_database():
    """Initialize database tables"""
    from app.models import Base
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def close_database():
    """Close database connections"""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        redis_client = None
    
    await engine.dispose()
    logger.info("Database connections closed")


async def health_check_database() -> dict:
    """Check database health"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            return {"status": "healthy", "message": "Database connection successful"}
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {"status": "unhealthy", "message": f"Database error: {str(e)}"}


async def health_check_redis() -> dict:
    """Check Redis health"""
    try:
        redis_conn = await get_redis()
        await redis_conn.ping()
        return {"status": "healthy", "message": "Redis connection successful"}
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {"status": "unhealthy", "message": f"Redis error: {str(e)}"}
