"""
Health checking and system monitoring for FixGenie
"""

import asyncio
import time
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import aiohttp
import structlog

logger = structlog.get_logger()


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result"""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    timestamp: datetime
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details or {}
        }


class HealthChecker:
    """Comprehensive health checking system"""
    
    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.check_history: List[HealthCheck] = []
        self.max_history = 1000
        
    async def check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        start_time = time.time()
        
        # Run all health checks
        checks = await asyncio.gather(
            self._check_system_resources(),
            self._check_database_health(),
            self._check_ai_services(),
            self._check_vector_database(),
            self._check_cache_health(),
            self._check_external_dependencies(),
            return_exceptions=True
        )
        
        # Process results
        health_checks = {}
        overall_status = HealthStatus.HEALTHY
        
        for check in checks:
            if isinstance(check, HealthCheck):
                health_checks[check.name] = check
                self.checks[check.name] = check
                self.check_history.append(check)
                
                # Update overall status
                if check.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif check.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
            elif isinstance(check, Exception):
                logger.error("Health check failed", error=str(check))
                overall_status = HealthStatus.UNHEALTHY
        
        # Trim history
        if len(self.check_history) > self.max_history:
            self.check_history = self.check_history[-self.max_history:]
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": total_time,
            "checks": {name: check.to_dict() for name, check in health_checks.items()},
            "summary": self._generate_summary(health_checks)
        }
    
    async def _check_system_resources(self) -> HealthCheck:
        """Check system resource usage"""
        start_time = time.time()
        
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine status based on thresholds
            status = HealthStatus.HEALTHY
            issues = []
            
            if cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                issues.append(f"CPU usage critical: {cpu_percent:.1f}%")
            elif cpu_percent > 75:
                status = HealthStatus.DEGRADED
                issues.append(f"CPU usage high: {cpu_percent:.1f}%")
            
            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                issues.append(f"Memory usage critical: {memory.percent:.1f}%")
            elif memory.percent > 80:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                issues.append(f"Memory usage high: {memory.percent:.1f}%")
            
            if disk.percent > 95:
                status = HealthStatus.UNHEALTHY
                issues.append(f"Disk usage critical: {disk.percent:.1f}%")
            elif disk.percent > 85:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                issues.append(f"Disk usage high: {disk.percent:.1f}%")
            
            message = "System resources healthy" if not issues else "; ".join(issues)
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                response_time_ms=response_time,
                timestamp=datetime.utcnow(),
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free / (1024**3)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check system resources: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.utcnow()
            )
    
    async def _check_database_health(self) -> HealthCheck:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            from app.database import get_database
            from sqlalchemy import text
            
            # Test database connection
            async for db in get_database():
                # Simple query to test connectivity
                result = await db.execute(text("SELECT 1"))
                await result.fetchone()
                break
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on response time
            if response_time > 1000:  # 1 second
                status = HealthStatus.DEGRADED
                message = f"Database responding slowly: {response_time:.0f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "Database healthy"
            
            return HealthCheck(
                name="database",
                status=status,
                message=message,
                response_time_ms=response_time,
                timestamp=datetime.utcnow(),
                details={"connection_time_ms": response_time}
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.utcnow()
            )
    
    async def _check_ai_services(self) -> HealthCheck:
        """Check AI service connectivity"""
        start_time = time.time()
        
        try:
            from app.services.ai_service import AIService
            
            # Test AI service with a simple embedding request
            ai_service = AIService()
            
            # Test embedding generation
            embedding_start = time.time()
            await ai_service.generate_embedding("health check")
            embedding_time = (time.time() - embedding_start) * 1000
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on response time
            if response_time > 5000:  # 5 seconds
                status = HealthStatus.DEGRADED
                message = f"AI services responding slowly: {response_time:.0f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "AI services healthy"
            
            return HealthCheck(
                name="ai_services",
                status=status,
                message=message,
                response_time_ms=response_time,
                timestamp=datetime.utcnow(),
                details={
                    "embedding_time_ms": embedding_time,
                    "total_time_ms": response_time
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name="ai_services",
                status=HealthStatus.UNHEALTHY,
                message=f"AI services failed: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.utcnow()
            )
    
    async def _check_vector_database(self) -> HealthCheck:
        """Check vector database (Pinecone) connectivity"""
        start_time = time.time()
        
        try:
            import pinecone
            from app.config import settings
            
            # Initialize Pinecone
            pinecone.init(
                api_key=settings.pinecone_api_key,
                environment=settings.pinecone_environment
            )
            
            # Test index connectivity
            index = pinecone.Index(settings.pinecone_index)
            stats = index.describe_index_stats()
            
            response_time = (time.time() - start_time) * 1000
            
            # Check if index has vectors
            total_vectors = stats.get('total_vector_count', 0)
            
            if total_vectors == 0:
                status = HealthStatus.DEGRADED
                message = "Vector database empty"
            else:
                status = HealthStatus.HEALTHY
                message = f"Vector database healthy ({total_vectors} vectors)"
            
            return HealthCheck(
                name="vector_database",
                status=status,
                message=message,
                response_time_ms=response_time,
                timestamp=datetime.utcnow(),
                details={
                    "total_vectors": total_vectors,
                    "index_stats": stats
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name="vector_database",
                status=HealthStatus.UNHEALTHY,
                message=f"Vector database failed: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.utcnow()
            )
    
    async def _check_cache_health(self) -> HealthCheck:
        """Check Redis cache connectivity"""
        start_time = time.time()
        
        try:
            import redis.asyncio as redis
            from app.config import settings
            
            # Test Redis connection
            redis_client = redis.from_url(settings.redis_url_computed)
            
            # Test basic operations
            await redis_client.ping()
            await redis_client.set("health_check", "ok", ex=10)
            result = await redis_client.get("health_check")
            await redis_client.delete("health_check")
            
            response_time = (time.time() - start_time) * 1000
            
            if result == b"ok":
                status = HealthStatus.HEALTHY
                message = "Cache healthy"
            else:
                status = HealthStatus.DEGRADED
                message = "Cache operations inconsistent"
            
            await redis_client.close()
            
            return HealthCheck(
                name="cache",
                status=status,
                message=message,
                response_time_ms=response_time,
                timestamp=datetime.utcnow(),
                details={"operation_time_ms": response_time}
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name="cache",
                status=HealthStatus.DEGRADED,  # Cache is optional
                message=f"Cache unavailable: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.utcnow()
            )
    
    async def _check_external_dependencies(self) -> HealthCheck:
        """Check external service dependencies"""
        start_time = time.time()
        
        try:
            # Test external services (example: Google AI API)
            async with aiohttp.ClientSession() as session:
                # Test Google AI API endpoint
                headers = {"Content-Type": "application/json"}
                
                # Simple health check to AI service
                try:
                    async with session.get(
                        "https://generativelanguage.googleapis.com/v1beta/models",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200 or response.status == 401:  # 401 is expected without API key
                            ai_status = "reachable"
                        else:
                            ai_status = f"error_{response.status}"
                except Exception:
                    ai_status = "unreachable"
            
            response_time = (time.time() - start_time) * 1000
            
            if ai_status == "reachable":
                status = HealthStatus.HEALTHY
                message = "External dependencies healthy"
            else:
                status = HealthStatus.DEGRADED
                message = f"Some external services unavailable: AI API {ai_status}"
            
            return HealthCheck(
                name="external_dependencies",
                status=status,
                message=message,
                response_time_ms=response_time,
                timestamp=datetime.utcnow(),
                details={
                    "ai_api_status": ai_status,
                    "check_time_ms": response_time
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name="external_dependencies",
                status=HealthStatus.DEGRADED,
                message=f"External dependency check failed: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.utcnow()
            )
    
    def _generate_summary(self, checks: Dict[str, HealthCheck]) -> Dict[str, Any]:
        """Generate health check summary"""
        total_checks = len(checks)
        healthy_count = sum(1 for check in checks.values() if check.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for check in checks.values() if check.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for check in checks.values() if check.status == HealthStatus.UNHEALTHY)
        
        avg_response_time = sum(check.response_time_ms for check in checks.values()) / total_checks if total_checks > 0 else 0
        
        return {
            "total_checks": total_checks,
            "healthy": healthy_count,
            "degraded": degraded_count,
            "unhealthy": unhealthy_count,
            "average_response_time_ms": avg_response_time,
            "health_score": (healthy_count + degraded_count * 0.5) / total_checks * 100 if total_checks > 0 else 0
        }
    
    def get_check_history(self, check_name: Optional[str] = None, limit: int = 100) -> List[HealthCheck]:
        """Get health check history"""
        if check_name:
            history = [check for check in self.check_history if check.name == check_name]
        else:
            history = self.check_history
        
        return history[-limit:]
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current health status"""
        if not self.checks:
            return {"status": "unknown", "message": "No health checks performed yet"}
        
        # Determine overall status
        statuses = [check.status for check in self.checks.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            "status": overall_status.value,
            "last_check": max(check.timestamp for check in self.checks.values()).isoformat(),
            "checks": {name: check.status.value for name, check in self.checks.items()}
        }


# Background health monitoring
class HealthMonitor:
    """Background health monitoring service"""
    
    def __init__(self, health_checker: HealthChecker, check_interval: int = 60):
        self.health_checker = health_checker
        self.check_interval = check_interval
        self.running = False
        self.task = None
        
    async def start(self):
        """Start background health monitoring"""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitoring started", interval=self.check_interval)
        
    async def stop(self):
        """Stop background health monitoring"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitoring stopped")
        
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                health_result = await self.health_checker.check_system_health()
                
                # Log health status
                logger.info(
                    "Health check completed",
                    status=health_result["status"],
                    response_time_ms=health_result["response_time_ms"],
                    health_score=health_result["summary"]["health_score"]
                )
                
                # Check for alerts
                if health_result["status"] == "unhealthy":
                    logger.warning("System health is unhealthy", checks=health_result["checks"])
                elif health_result["status"] == "degraded":
                    logger.warning("System health is degraded", checks=health_result["checks"])
                
            except Exception as e:
                logger.error("Health monitoring error", error=str(e))
            
            await asyncio.sleep(self.check_interval)


# Global health checker instance
health_checker = HealthChecker()
health_monitor = HealthMonitor(health_checker)

# Export health checking components
__all__ = [
    "HealthStatus",
    "HealthCheck",
    "HealthChecker",
    "HealthMonitor",
    "health_checker",
    "health_monitor"
]
