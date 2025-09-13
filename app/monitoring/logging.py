"""
Enhanced logging middleware and utilities for SherlockAI
"""

import time
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import structlog
from contextlib import asynccontextmanager
import asyncio
import psutil
import os

logger = structlog.get_logger()


class LogContext:
    """Thread-local log context for request correlation"""
    
    def __init__(self):
        self._context = {}
        
    def set(self, key: str, value: Any):
        """Set context value"""
        self._context[key] = value
        
    def get(self, key: str, default: Any = None):
        """Get context value"""
        return self._context.get(key, default)
        
    def clear(self):
        """Clear all context"""
        self._context.clear()
        
    def update(self, data: Dict[str, Any]):
        """Update context with dictionary"""
        self._context.update(data)
        
    def to_dict(self) -> Dict[str, Any]:
        """Get context as dictionary"""
        return self._context.copy()


# Global log context
log_context = LogContext()


class SecurityLogger:
    """Security-focused logging for audit trails"""
    
    def __init__(self):
        self.security_logger = structlog.get_logger("security")
        
    def log_authentication_attempt(self, request: Request, user_id: Optional[str] = None, success: bool = False):
        """Log authentication attempts"""
        self.security_logger.info(
            "Authentication attempt",
            user_id=user_id,
            success=success,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            timestamp=datetime.utcnow().isoformat(),
            event_type="auth_attempt"
        )
        
    def log_authorization_failure(self, request: Request, user_id: Optional[str] = None, resource: str = ""):
        """Log authorization failures"""
        self.security_logger.warning(
            "Authorization failure",
            user_id=user_id,
            resource=resource,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            timestamp=datetime.utcnow().isoformat(),
            event_type="auth_failure"
        )
        
    def log_suspicious_activity(self, request: Request, activity_type: str, details: Dict[str, Any]):
        """Log suspicious activities"""
        self.security_logger.warning(
            "Suspicious activity detected",
            activity_type=activity_type,
            details=details,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            timestamp=datetime.utcnow().isoformat(),
            event_type="suspicious_activity"
        )
        
    def log_data_access(self, request: Request, user_id: Optional[str] = None, resource: str = "", action: str = ""):
        """Log data access for compliance"""
        self.security_logger.info(
            "Data access",
            user_id=user_id,
            resource=resource,
            action=action,
            ip_address=request.client.host if request.client else None,
            timestamp=datetime.utcnow().isoformat(),
            event_type="data_access"
        )


class BusinessLogger:
    """Business metrics and events logging"""
    
    def __init__(self):
        self.business_logger = structlog.get_logger("business")
        
    def log_search_event(self, query: str, results_count: int, user_id: Optional[str] = None, 
                        search_type: str = "semantic", execution_time: float = 0.0):
        """Log search events for business analytics"""
        self.business_logger.info(
            "Search event",
            query=query,
            results_count=results_count,
            user_id=user_id,
            search_type=search_type,
            execution_time_ms=execution_time * 1000,
            timestamp=datetime.utcnow().isoformat(),
            event_type="search"
        )
        
    def log_feedback_event(self, query: str, result_id: str, rating: int, helpful: bool, 
                          user_id: Optional[str] = None):
        """Log feedback events"""
        self.business_logger.info(
            "Feedback event",
            query=query,
            result_id=result_id,
            rating=rating,
            helpful=helpful,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            event_type="feedback"
        )
        
    def log_user_session(self, user_id: str, action: str, session_duration: Optional[float] = None):
        """Log user session events"""
        self.business_logger.info(
            "User session event",
            user_id=user_id,
            action=action,
            session_duration_minutes=session_duration / 60 if session_duration else None,
            timestamp=datetime.utcnow().isoformat(),
            event_type="user_session"
        )


class PerformanceLogger:
    """Performance monitoring and logging"""
    
    def __init__(self):
        self.perf_logger = structlog.get_logger("performance")
        
    def log_slow_request(self, request: Request, duration: float, threshold: float = 5.0):
        """Log slow requests"""
        if duration > threshold:
            self.perf_logger.warning(
                "Slow request detected",
                method=request.method,
                url=str(request.url),
                duration_seconds=duration,
                threshold_seconds=threshold,
                timestamp=datetime.utcnow().isoformat(),
                event_type="slow_request"
            )
            
    def log_resource_usage(self):
        """Log system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            self.perf_logger.info(
                "System resource usage",
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available_gb=memory.available / (1024**3),
                disk_percent=disk.percent,
                disk_free_gb=disk.free / (1024**3),
                timestamp=datetime.utcnow().isoformat(),
                event_type="resource_usage"
            )
        except Exception as e:
            logger.error("Failed to collect resource usage", error=str(e))


class ErrorLogger:
    """Enhanced error logging with context"""
    
    def __init__(self):
        self.error_logger = structlog.get_logger("errors")
        
    def log_application_error(self, error: Exception, context: Dict[str, Any], severity: str = "error"):
        """Log application errors with full context"""
        self.error_logger.error(
            "Application error",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context,
            severity=severity,
            timestamp=datetime.utcnow().isoformat(),
            event_type="application_error"
        )
        
    def log_external_service_error(self, service: str, error: Exception, request_data: Optional[Dict] = None):
        """Log external service errors"""
        self.error_logger.error(
            "External service error",
            service=service,
            error_type=type(error).__name__,
            error_message=str(error),
            request_data=request_data,
            timestamp=datetime.utcnow().isoformat(),
            event_type="external_service_error"
        )


# Global logger instances
security_logger = SecurityLogger()
business_logger = BusinessLogger()
performance_logger = PerformanceLogger()
error_logger = ErrorLogger()


async def enhanced_logging_middleware(request: Request, call_next):
    """Enhanced logging middleware with comprehensive request/response logging"""
    
    # Generate correlation ID
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    # Set up log context
    log_context.clear()
    log_context.update({
        "correlation_id": correlation_id,
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "content_type": request.headers.get("content-type"),
        "content_length": request.headers.get("content-length"),
        "referer": request.headers.get("referer"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Log request start
    start_time = time.time()
    
    logger.info(
        "Request started",
        **log_context.to_dict(),
        event_type="request_start"
    )
    
    # Process request body for logging (if applicable)
    request_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            # Read body for logging (be careful with large payloads)
            body = await request.body()
            if len(body) < 10000:  # Only log small payloads
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    try:
                        request_body = json.loads(body.decode())
                        # Sanitize sensitive data
                        request_body = sanitize_sensitive_data(request_body)
                    except:
                        request_body = {"_raw_size": len(body)}
                else:
                    request_body = {"_content_type": content_type, "_size": len(body)}
        except Exception as e:
            logger.warning("Failed to read request body for logging", error=str(e))
    
    try:
        # Process the request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Update context with response info
        log_context.update({
            "status_code": response.status_code,
            "response_time_seconds": response_time,
            "response_size": response.headers.get("content-length"),
            "response_type": response.headers.get("content-type")
        })
        
        # Add response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time"] = f"{response_time:.3f}s"
        
        # Log successful response
        logger.info(
            "Request completed",
            **log_context.to_dict(),
            request_body=request_body,
            event_type="request_complete"
        )
        
        # Log slow requests
        performance_logger.log_slow_request(request, response_time)
        
        # Log business events for specific endpoints
        if request.url.path.startswith("/api/v1/search"):
            business_logger.log_search_event(
                query=request_body.get("query", "") if request_body else "",
                results_count=0,  # Will be updated by the endpoint
                execution_time=response_time
            )
            
        return response
        
    except Exception as e:
        # Calculate response time for errors
        response_time = time.time() - start_time
        
        # Update context with error info
        log_context.update({
            "error_type": type(e).__name__,
            "error_message": str(e),
            "response_time_seconds": response_time,
            "status_code": 500
        })
        
        # Log error
        logger.error(
            "Request failed",
            **log_context.to_dict(),
            request_body=request_body,
            event_type="request_error",
            exc_info=True
        )
        
        # Log to error logger with context
        error_logger.log_application_error(e, log_context.to_dict())
        
        # Re-raise the exception
        raise
    
    finally:
        # Clear context
        log_context.clear()


def sanitize_sensitive_data(data: Any) -> Any:
    """Remove sensitive information from log data"""
    if isinstance(data, dict):
        sanitized = {}
        sensitive_keys = {
            "password", "token", "secret", "key", "auth", "authorization",
            "api_key", "access_token", "refresh_token", "session_id",
            "credit_card", "ssn", "social_security", "phone", "email"
        }
        
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, (dict, list)):
                sanitized[key] = sanitize_sensitive_data(value)
            else:
                sanitized[key] = value
        return sanitized
    
    elif isinstance(data, list):
        return [sanitize_sensitive_data(item) for item in data]
    
    return data


def setup_log_rotation():
    """Set up log rotation configuration"""
    import logging.handlers
    
    # Create rotating file handler for application logs
    app_handler = logging.handlers.RotatingFileHandler(
        "logs/SherlockAI.log",
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=10
    )
    
    # Create rotating file handler for security logs
    security_handler = logging.handlers.RotatingFileHandler(
        "logs/security.log",
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=20
    )
    
    # Create rotating file handler for business logs
    business_handler = logging.handlers.RotatingFileHandler(
        "logs/business.log",
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=15
    )
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    logger.info("Log rotation configured")


async def log_system_startup(app_name: str, version: str, environment: str):
    """Log system startup information"""
    startup_info = {
        "app_name": app_name,
        "version": version,
        "environment": environment,
        "python_version": os.sys.version,
        "pid": os.getpid(),
        "hostname": os.uname().nodename if hasattr(os, 'uname') else 'unknown',
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": "system_startup"
    }
    
    logger.info("System startup", **startup_info)
    performance_logger.log_resource_usage()


async def log_system_shutdown():
    """Log system shutdown"""
    logger.info(
        "System shutdown",
        timestamp=datetime.utcnow().isoformat(),
        event_type="system_shutdown"
    )


# Background task for periodic resource logging
async def periodic_resource_logging(interval: int = 300):  # 5 minutes
    """Periodically log system resource usage"""
    while True:
        try:
            performance_logger.log_resource_usage()
            await asyncio.sleep(interval)
        except Exception as e:
            logger.error("Failed to log periodic resource usage", error=str(e))
            await asyncio.sleep(interval)


# Export all logging utilities
__all__ = [
    "enhanced_logging_middleware",
    "security_logger",
    "business_logger", 
    "performance_logger",
    "error_logger",
    "log_context",
    "setup_log_rotation",
    "log_system_startup",
    "log_system_shutdown",
    "periodic_resource_logging"
]
