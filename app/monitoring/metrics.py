"""
Prometheus metrics collection for SherlockAI
"""

import time
from typing import Dict, Any, Optional
from functools import wraps
from prometheus_client import (
    Counter, Histogram, Gauge, Info, 
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, REGISTRY
)
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse
import structlog

logger = structlog.get_logger()

# Create custom registry for SherlockAI metrics
SherlockAI_registry = CollectorRegistry()

# Request metrics
http_requests_total = Counter(
    'SherlockAI_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=SherlockAI_registry
)

http_request_duration_seconds = Histogram(
    'SherlockAI_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=SherlockAI_registry
)

# Search metrics
search_requests_total = Counter(
    'SherlockAI_search_requests_total',
    'Total search requests',
    ['search_type', 'status'],
    registry=SherlockAI_registry
)

search_duration_seconds = Histogram(
    'SherlockAI_search_duration_seconds',
    'Search request duration in seconds',
    ['search_type'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0],
    registry=SherlockAI_registry
)

search_results_count = Histogram(
    'SherlockAI_search_results_count',
    'Number of search results returned',
    ['search_type'],
    buckets=[0, 1, 3, 5, 10, 20],
    registry=SherlockAI_registry
)

# AI service metrics
ai_requests_total = Counter(
    'SherlockAI_ai_requests_total',
    'Total AI service requests',
    ['service', 'model', 'status'],
    registry=SherlockAI_registry
)

ai_request_duration_seconds = Histogram(
    'SherlockAI_ai_request_duration_seconds',
    'AI service request duration in seconds',
    ['service', 'model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
    registry=SherlockAI_registry
)

ai_token_usage = Counter(
    'SherlockAI_ai_tokens_total',
    'Total AI tokens consumed',
    ['service', 'model', 'type'],
    registry=SherlockAI_registry
)

# Database metrics
db_connections_active = Gauge(
    'SherlockAI_db_connections_active',
    'Active database connections',
    registry=SherlockAI_registry
)

db_query_duration_seconds = Histogram(
    'SherlockAI_db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
    registry=SherlockAI_registry
)

# Cache metrics
cache_requests_total = Counter(
    'SherlockAI_cache_requests_total',
    'Total cache requests',
    ['operation', 'status'],
    registry=SherlockAI_registry
)

cache_hit_ratio = Gauge(
    'SherlockAI_cache_hit_ratio',
    'Cache hit ratio',
    registry=SherlockAI_registry
)

# Business metrics
feedback_submissions_total = Counter(
    'SherlockAI_feedback_submissions_total',
    'Total feedback submissions',
    ['rating', 'helpful'],
    registry=SherlockAI_registry
)

user_sessions_active = Gauge(
    'SherlockAI_user_sessions_active',
    'Active user sessions',
    registry=SherlockAI_registry
)

# System metrics
system_info = Info(
    'SherlockAI_system_info',
    'System information',
    registry=SherlockAI_registry
)

# Error metrics
errors_total = Counter(
    'SherlockAI_errors_total',
    'Total errors',
    ['error_type', 'component'],
    registry=SherlockAI_registry
)


class MetricsCollector:
    """Centralized metrics collection"""
    
    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0
        
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
    def record_search_request(self, search_type: str, duration: float, results_count: int, status: str = "success"):
        """Record search request metrics"""
        search_requests_total.labels(
            search_type=search_type,
            status=status
        ).inc()
        
        search_duration_seconds.labels(
            search_type=search_type
        ).observe(duration)
        
        search_results_count.labels(
            search_type=search_type
        ).observe(results_count)
        
    def record_ai_request(self, service: str, model: str, duration: float, status: str = "success", tokens: Optional[int] = None):
        """Record AI service request metrics"""
        ai_requests_total.labels(
            service=service,
            model=model,
            status=status
        ).inc()
        
        ai_request_duration_seconds.labels(
            service=service,
            model=model
        ).observe(duration)
        
        if tokens:
            ai_token_usage.labels(
                service=service,
                model=model,
                type="total"
            ).inc(tokens)
            
    def record_db_query(self, operation: str, duration: float):
        """Record database query metrics"""
        db_query_duration_seconds.labels(
            operation=operation
        ).observe(duration)
        
    def record_cache_operation(self, operation: str, hit: bool):
        """Record cache operation metrics"""
        status = "hit" if hit else "miss"
        cache_requests_total.labels(
            operation=operation,
            status=status
        ).inc()
        
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
            
        # Update hit ratio
        total = self.cache_hits + self.cache_misses
        if total > 0:
            cache_hit_ratio.set(self.cache_hits / total)
            
    def record_feedback(self, rating: int, helpful: bool):
        """Record feedback submission metrics"""
        feedback_submissions_total.labels(
            rating=str(rating),
            helpful=str(helpful).lower()
        ).inc()
        
    def record_error(self, error_type: str, component: str):
        """Record error metrics"""
        errors_total.labels(
            error_type=error_type,
            component=component
        ).inc()
        
    def update_active_connections(self, count: int):
        """Update active database connections"""
        db_connections_active.set(count)
        
    def update_active_sessions(self, count: int):
        """Update active user sessions"""
        user_sessions_active.set(count)


# Global metrics collector instance
metrics_collector = MetricsCollector()


def setup_metrics(app_name: str, version: str, environment: str):
    """Initialize system metrics"""
    system_info.info({
        'app_name': app_name,
        'version': version,
        'environment': environment
    })
    
    logger.info("Metrics collection initialized", 
                app_name=app_name, version=version, environment=environment)


async def metrics_middleware(request: Request, call_next):
    """Middleware to collect HTTP metrics"""
    start_time = time.time()
    
    # Extract endpoint pattern
    endpoint = request.url.path
    method = request.method
    
    try:
        response = await call_next(request)
        status_code = response.status_code
        
        # Record successful request
        duration = time.time() - start_time
        metrics_collector.record_http_request(method, endpoint, status_code, duration)
        
        return response
        
    except Exception as e:
        # Record failed request
        duration = time.time() - start_time
        metrics_collector.record_http_request(method, endpoint, 500, duration)
        metrics_collector.record_error(type(e).__name__, "http_middleware")
        
        logger.error("Request failed in metrics middleware", 
                    method=method, endpoint=endpoint, error=str(e))
        raise


def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return PlainTextResponse(
        generate_latest(SherlockAI_registry),
        media_type=CONTENT_TYPE_LATEST
    )


def track_search_metrics(func):
    """Decorator to track search operation metrics"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        search_type = kwargs.get('search_type', 'unknown')
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Extract results count from response
            results_count = 0
            if hasattr(result, 'results'):
                results_count = len(result.results)
            elif isinstance(result, dict) and 'results' in result:
                results_count = len(result['results'])
                
            metrics_collector.record_search_request(search_type, duration, results_count)
            
            logger.info("Search metrics recorded",
                       search_type=search_type, duration=duration, results_count=results_count)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            metrics_collector.record_search_request(search_type, duration, 0, "error")
            metrics_collector.record_error(type(e).__name__, "search")
            
            logger.error("Search operation failed",
                        search_type=search_type, duration=duration, error=str(e))
            raise
            
    return wrapper


def track_ai_metrics(service: str, model: str):
    """Decorator to track AI service metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                metrics_collector.record_ai_request(service, model, duration)
                
                logger.info("AI metrics recorded",
                           service=service, model=model, duration=duration)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_ai_request(service, model, duration, "error")
                metrics_collector.record_error(type(e).__name__, f"ai_{service}")
                
                logger.error("AI operation failed",
                            service=service, model=model, duration=duration, error=str(e))
                raise
                
        return wrapper
    return decorator


def track_db_metrics(operation: str):
    """Decorator to track database operation metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                metrics_collector.record_db_query(operation, duration)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_error(type(e).__name__, f"db_{operation}")
                
                logger.error("Database operation failed",
                            operation=operation, duration=duration, error=str(e))
                raise
                
        return wrapper
    return decorator


# Export the metrics collector for use in other modules
__all__ = [
    "metrics_middleware",
    "setup_metrics", 
    "metrics_endpoint",
    "metrics_collector",
    "track_search_metrics",
    "track_ai_metrics", 
    "track_db_metrics"
]
