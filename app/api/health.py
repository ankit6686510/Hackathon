"""
Health check and monitoring endpoints
"""

import time
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog
import psutil

from app.models import HealthCheck, MetricsResponse, SearchLog, Issue, User
from app.database import get_database, health_check_database, health_check_redis
from app.services.ai_service import ai_service
from app.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Comprehensive health check for all system components
    """
    start_time = time.time()
    
    try:
        # Check all services
        db_health = await health_check_database()
        redis_health = await health_check_redis()
        ai_health = await ai_service.health_check()
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Determine overall status
        all_services_healthy = (
            db_health["status"] == "healthy" and
            redis_health["status"] == "healthy" and
            all(service["status"] == "healthy" for service in ai_health.values())
        )
        
        overall_status = "healthy" if all_services_healthy else "degraded"
        
        # If any critical service is down, mark as unhealthy
        if db_health["status"] == "unhealthy":
            overall_status = "unhealthy"
        
        services = {
            "database": db_health,
            "redis": redis_health,
            "ai_services": ai_health,
            "system": {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": (disk.used / disk.total) * 100,
                "uptime_seconds": time.time() - start_time
            }
        }
        
        response = HealthCheck(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=settings.app_version,
            environment=settings.environment,
            services=services
        )
        
        logger.info(
            "Health check completed",
            status=overall_status,
            response_time_ms=(time.time() - start_time) * 1000
        )
        
        return response
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthCheck(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version=settings.app_version,
            environment=settings.environment,
            services={"error": str(e)}
        )


@router.get("/health/live")
async def liveness_probe():
    """
    Simple liveness probe for Kubernetes/Docker
    """
    return {"status": "alive", "timestamp": datetime.utcnow()}


@router.get("/health/ready")
async def readiness_probe():
    """
    Readiness probe - checks if service can handle requests
    """
    try:
        # Quick database check
        db_health = await health_check_database()
        if db_health["status"] != "healthy":
            return {"status": "not_ready", "reason": "database_unavailable"}
        
        # Quick AI service check
        try:
            await ai_service.embed_text("health", use_cache=False)
        except Exception:
            return {"status": "not_ready", "reason": "ai_service_unavailable"}
        
        return {"status": "ready", "timestamp": datetime.utcnow()}
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return {"status": "not_ready", "reason": str(e)}


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(db: AsyncSession = Depends(get_database)):
    """
    Get application metrics for monitoring and analytics
    """
    try:
        # Get basic counts
        total_searches_result = await db.execute(select(func.count(SearchLog.id)))
        total_searches = total_searches_result.scalar() or 0
        
        total_issues_result = await db.execute(select(func.count(Issue.id)))
        total_issues = total_issues_result.scalar() or 0
        
        total_users_result = await db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar() or 0
        
        # Get average response time
        avg_time_result = await db.execute(
            select(func.avg(SearchLog.execution_time_ms))
            .where(SearchLog.execution_time_ms.isnot(None))
        )
        avg_response_time = avg_time_result.scalar() or 0.0
        
        # Get top queries (last 24 hours)
        from sqlalchemy import desc
        top_queries_result = await db.execute(
            select(SearchLog.query, func.count(SearchLog.query).label('count'))
            .where(SearchLog.timestamp >= func.now() - func.interval('24 hours'))
            .group_by(SearchLog.query)
            .order_by(desc('count'))
            .limit(10)
        )
        
        top_queries = [
            {"query": row.query, "count": row.count}
            for row in top_queries_result.fetchall()
        ]
        
        # Get recent feedback (placeholder)
        recent_feedback = []  # Would implement with actual feedback data
        
        metrics = MetricsResponse(
            total_searches=total_searches,
            total_issues=total_issues,
            total_users=total_users,
            avg_response_time_ms=float(avg_response_time),
            top_queries=top_queries,
            recent_feedback=recent_feedback
        )
        
        logger.info("Metrics retrieved successfully")
        return metrics
        
    except Exception as e:
        logger.error("Failed to retrieve metrics", error=str(e))
        # Return empty metrics on error
        return MetricsResponse(
            total_searches=0,
            total_issues=0,
            total_users=0,
            avg_response_time_ms=0.0,
            top_queries=[],
            recent_feedback=[]
        )


@router.get("/metrics/prometheus")
async def prometheus_metrics(db: AsyncSession = Depends(get_database)):
    """
    Prometheus-compatible metrics endpoint
    """
    try:
        # Get basic metrics
        total_searches_result = await db.execute(select(func.count(SearchLog.id)))
        total_searches = total_searches_result.scalar() or 0
        
        total_issues_result = await db.execute(select(func.count(Issue.id)))
        total_issues = total_issues_result.scalar() or 0
        
        avg_time_result = await db.execute(
            select(func.avg(SearchLog.execution_time_ms))
            .where(SearchLog.execution_time_ms.isnot(None))
        )
        avg_response_time = avg_time_result.scalar() or 0.0
        
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # Format as Prometheus metrics
        metrics_text = f"""# HELP fixgenie_searches_total Total number of searches performed
# TYPE fixgenie_searches_total counter
fixgenie_searches_total {total_searches}

# HELP fixgenie_issues_total Total number of issues in database
# TYPE fixgenie_issues_total gauge
fixgenie_issues_total {total_issues}

# HELP fixgenie_response_time_ms Average response time in milliseconds
# TYPE fixgenie_response_time_ms gauge
fixgenie_response_time_ms {avg_response_time}

# HELP fixgenie_cpu_percent CPU usage percentage
# TYPE fixgenie_cpu_percent gauge
fixgenie_cpu_percent {cpu_percent}

# HELP fixgenie_memory_percent Memory usage percentage
# TYPE fixgenie_memory_percent gauge
fixgenie_memory_percent {memory.percent}
"""
        
        return metrics_text
        
    except Exception as e:
        logger.error("Failed to generate Prometheus metrics", error=str(e))
        return "# Error generating metrics\n"
