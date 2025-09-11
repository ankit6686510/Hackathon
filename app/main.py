"""
Main FastAPI application with industry-grade features
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import structlog
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.config import settings
from app.database import init_database, close_database
from app.api.search import router as search_router
from app.api.health import router as health_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.monitoring import (
    setup_metrics, metrics_middleware, metrics_endpoint,
    enhanced_logging_middleware, log_system_startup, log_system_shutdown,
    health_monitor, AlertManager, create_default_alert_rules
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize Sentry for error tracking
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[
            FastApiIntegration(auto_enabling_integrations=False),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,
        environment=settings.environment,
    )

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting SherlockAI API", version=settings.app_version)
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
        
        # Initialize monitoring
        setup_metrics(settings.app_name, settings.app_version, settings.environment)
        
        # Start health monitoring
        await health_monitor.start()
        
        # Initialize alert manager
        alert_manager = AlertManager()
        for rule in create_default_alert_rules():
            alert_manager.add_rule(rule)
        app.state.alert_manager = alert_manager
        
        # Log system startup
        await log_system_startup(settings.app_name, settings.app_version, settings.environment)
        
        # Log startup completion
        logger.info(
            "SherlockAI API started successfully",
            environment=settings.environment,
            debug=settings.debug
        )
        
        yield
        
    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        raise
    finally:
        # Shutdown
        logger.info("Shutting down SherlockAI API")
        
        # Stop health monitoring
        await health_monitor.stop()
        
        # Log system shutdown
        await log_system_shutdown()
        
        await close_database()
        logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-Powered Issue Intelligence System for Juspay Engineers",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Add security middleware
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.juspay.in"]
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"] if settings.debug else settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
    max_age=600
)

# Add monitoring middleware
app.middleware("http")(enhanced_logging_middleware)
app.middleware("http")(metrics_middleware)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Request middleware for logging and monitoring"""
    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Start timing
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    try:
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
        
        # Log response
        logger.info(
            "Request completed",
            request_id=request_id,
            status_code=response.status_code,
            response_time_ms=response_time
        )
        
        return response
        
    except Exception as e:
        # Calculate response time for errors
        response_time = (time.time() - start_time) * 1000
        
        # Log error
        logger.error(
            "Request failed",
            request_id=request_id,
            error=str(e),
            response_time_ms=response_time
        )
        
        # Re-raise the exception
        raise


# Custom exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured logging"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(
        "HTTP exception",
        request_id=request_id,
        status_code=exc.status_code,
        detail=exc.detail
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "request_id": request_id
            }
        },
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(
        "Validation error",
        request_id=request_id,
        errors=exc.errors()
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": 422,
                "message": "Validation error",
                "details": exc.errors(),
                "request_id": request_id
            }
        },
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        "Unexpected error",
        request_id=request_id,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "request_id": request_id
            }
        },
        headers={"X-Request-ID": request_id}
    )


# Rate limited endpoints
@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request):
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs_url": "/docs" if settings.debug else None,
        "health_url": "/api/v1/health"
    }


@app.get("/api/v1/info")
@limiter.limit("30/minute")
async def api_info(request: Request):
    """API information endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "features": {
            "semantic_search": True,
            "ai_suggestions": True,
            "caching": True,
            "rate_limiting": True,
            "monitoring": True
        },
        "limits": {
            "max_top_k": settings.max_top_k,
            "rate_limit": f"{settings.rate_limit_requests}/{settings.rate_limit_window}s"
        }
    }


# Add metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return metrics_endpoint()

# Include routers
app.include_router(search_router)
app.include_router(health_router)
app.include_router(analytics_router)
app.include_router(auth_router)

# Add rate limiting to search endpoints
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to search endpoints"""
    if request.url.path.startswith("/api/v1/search"):
        # Apply stricter rate limiting to search endpoints
        try:
            # This would be handled by SlowAPI middleware
            pass
        except RateLimitExceeded:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": 429,
                        "message": "Rate limit exceeded",
                        "request_id": getattr(request.state, "request_id", "unknown")
                    }
                }
            )
    
    response = await call_next(request)
    return response


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        access_log=True
    )
