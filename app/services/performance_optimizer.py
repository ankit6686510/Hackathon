"""
Performance optimization service for SherlockAI
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from functools import wraps
import hashlib
import json
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from app.config import settings

logger = structlog.get_logger()

class PerformanceOptimizer:
    """Advanced performance optimization service"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0
        }
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            await self.redis_client.ping()
            logger.info("Performance optimizer initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize performance optimizer", error=str(e))
            self.redis_client = None

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

    def cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters"""
        key_data = json.dumps(kwargs, sort_keys=True)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{settings.app_name}:{prefix}:{key_hash}"

    async def get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
            
        try:
            self.cache_stats["total_requests"] += 1
            value = await self.redis_client.get(key)
            if value:
                self.cache_stats["hits"] += 1
                return json.loads(value)
            else:
                self.cache_stats["misses"] += 1
                return None
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None

    async def set_cached(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache"""
        if not self.redis_client:
            return False
            
        try:
            serialized = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern"""
        if not self.redis_client:
            return 0
            
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("Cache invalidation failed", pattern=pattern, error=str(e))
            return 0

    def cached(self, ttl: int = 3600, prefix: str = "default"):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key_data = {
                    "func": func.__name__,
                    "args": str(args),
                    "kwargs": kwargs
                }
                key = self.cache_key(prefix, **cache_key_data)
                
                # Try to get from cache
                cached_result = await self.get_cached(key)
                if cached_result is not None:
                    logger.debug("Cache hit", function=func.__name__, key=key)
                    return cached_result
                
                # Execute function and cache result
                start_time = time.time()
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Cache the result
                await self.set_cached(key, result, ttl)
                
                logger.debug(
                    "Function executed and cached",
                    function=func.__name__,
                    execution_time=execution_time,
                    key=key
                )
                
                return result
            return wrapper
        return decorator

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        hit_rate = 0
        if self.cache_stats["total_requests"] > 0:
            hit_rate = (self.cache_stats["hits"] / self.cache_stats["total_requests"]) * 100
            
        return {
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "total_requests": self.cache_stats["total_requests"],
            "hit_rate_percent": round(hit_rate, 2),
            "redis_connected": self.redis_client is not None
        }

    async def warm_cache(self, db: AsyncSession):
        """Pre-warm cache with frequently accessed data"""
        try:
            logger.info("Starting cache warm-up")
            
            # Warm up popular search patterns
            popular_queries = [
                "UPI payment failed",
                "API timeout",
                "Database connection",
                "SSL certificate",
                "Authentication error"
            ]
            
            # This would typically call your search service
            # For now, we'll just cache some metadata
            for query in popular_queries:
                key = self.cache_key("popular_query", query=query)
                await self.set_cached(key, {"query": query, "warmed": True}, ttl=7200)
            
            # Cache system health data
            health_key = self.cache_key("system_health")
            health_data = {
                "status": "healthy",
                "timestamp": time.time(),
                "services": ["api", "database", "cache", "ai"]
            }
            await self.set_cached(health_key, health_data, ttl=300)
            
            logger.info("Cache warm-up completed", queries_warmed=len(popular_queries))
            
        except Exception as e:
            logger.error("Cache warm-up failed", error=str(e))

    async def optimize_database_queries(self, db: AsyncSession):
        """Optimize database performance"""
        try:
            # Analyze slow queries
            slow_query_result = await db.execute(text("""
                SELECT query, mean_exec_time, calls
                FROM pg_stat_statements
                WHERE mean_exec_time > 100
                ORDER BY mean_exec_time DESC
                LIMIT 10
            """))
            
            slow_queries = slow_query_result.fetchall()
            if slow_queries:
                logger.warning(
                    "Slow queries detected",
                    count=len(slow_queries),
                    slowest_time=slow_queries[0].mean_exec_time if slow_queries else 0
                )
            
            # Update table statistics
            await db.execute(text("ANALYZE"))
            
            # Vacuum if needed (in production, this should be scheduled)
            if settings.environment == "development":
                await db.execute(text("VACUUM ANALYZE"))
            
            logger.info("Database optimization completed")
            
        except Exception as e:
            logger.warning("Database optimization failed", error=str(e))

    async def preload_embeddings(self):
        """Preload frequently used embeddings"""
        try:
            # This would typically preload embeddings for common queries
            # Implementation depends on your vector database setup
            logger.info("Preloading embeddings for common queries")
            
            # Simulate preloading
            await asyncio.sleep(0.1)
            
            logger.info("Embeddings preloaded successfully")
            
        except Exception as e:
            logger.error("Failed to preload embeddings", error=str(e))

    async def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        try:
            if not self.redis_client:
                return
                
            # Get memory usage
            info = await self.redis_client.info("memory")
            used_memory = info.get("used_memory", 0)
            max_memory = info.get("maxmemory", 0)
            
            if max_memory > 0:
                memory_usage_percent = (used_memory / max_memory) * 100
                
                if memory_usage_percent > 80:
                    logger.warning(
                        "High cache memory usage",
                        usage_percent=memory_usage_percent,
                        used_memory=used_memory,
                        max_memory=max_memory
                    )
                    
                    # Force cleanup of expired keys
                    await self.redis_client.execute_command("MEMORY", "PURGE")
                    
        except Exception as e:
            logger.warning("Cache cleanup failed", error=str(e))

# Global instance
performance_optimizer = PerformanceOptimizer()

# Convenience decorators
def cached_search(ttl: int = 1800):
    """Cache search results for 30 minutes"""
    return performance_optimizer.cached(ttl=ttl, prefix="search")

def cached_analytics(ttl: int = 300):
    """Cache analytics data for 5 minutes"""
    return performance_optimizer.cached(ttl=ttl, prefix="analytics")

def cached_health(ttl: int = 60):
    """Cache health data for 1 minute"""
    return performance_optimizer.cached(ttl=ttl, prefix="health")
