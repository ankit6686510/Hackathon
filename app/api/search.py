"""
Search API endpoints
"""

import time
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models import SearchRequest, SearchResponse, SearchResult, SearchLog
from app.database import get_database, get_redis
from app.services.ai_service import ai_service
from app.config import settings
import json
import hashlib

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["search"])


async def log_search_request(
    db: AsyncSession,
    request: Request,
    search_request: SearchRequest,
    results: List[dict],
    execution_time_ms: float
):
    """Log search request for analytics"""
    try:
        # Create search log entry
        search_log = SearchLog(
            query=search_request.query,
            search_type=search_request.search_type,
            top_k=search_request.top_k,
            results_count=len(results),
            execution_time_ms=execution_time_ms,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            top_result_id=results[0]["id"] if results else None,
            top_result_score=results[0]["score"] if results else None,
        )
        
        db.add(search_log)
        await db.commit()
        
        logger.info(
            "Search request logged",
            query=search_request.query,
            results_count=len(results),
            execution_time_ms=execution_time_ms
        )
    except Exception as e:
        logger.error("Failed to log search request", error=str(e))


def generate_search_cache_key(search_request: SearchRequest) -> str:
    """Generate cache key for search results"""
    cache_data = {
        "query": search_request.query,
        "top_k": search_request.top_k,
        "search_type": search_request.search_type.value,
        "include_resolved_only": search_request.include_resolved_only,
        "similarity_threshold": search_request.similarity_threshold,
        "filters": search_request.filters or {}
    }
    cache_string = json.dumps(cache_data, sort_keys=True)
    return f"search:{hashlib.md5(cache_string.encode()).hexdigest()}"


@router.post("/search", response_model=SearchResponse)
async def search_issues(
    search_request: SearchRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database)
):
    """
    Search for payment-related issues using AI-powered semantic search
    
    This endpoint performs semantic search across historical payment issues to find
    the most relevant solutions and generates AI-powered fix suggestions.
    PAYMENT DOMAIN ONLY - Non-payment queries will be rejected.
    """
    start_time = time.time()
    
    try:
        # Validate request
        if not search_request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if search_request.top_k > settings.max_top_k:
            raise HTTPException(
                status_code=400, 
                detail=f"top_k cannot exceed {settings.max_top_k}"
            )
        
        # Use the new payment-focused smart response system
        logger.info("Processing payment domain query", query=search_request.query)
        smart_response = await ai_service.generate_payment_smart_response(search_request.query)
        
        results = []
        
        if smart_response["type"] == "domain_rejection":
            # Non-payment query - return rejection message
            result = SearchResult(
                id="domain-rejection",
                title="Payment Domain Only",
                description="This system specializes in payment-related issues only.",
                resolution=smart_response["content"],
                ai_suggestion="Please ask about UPI transactions, payment gateways, card processing, bank integrations, payment errors, or other payment-related topics.",
                score=1.0,
                tags=["Domain-Restriction", "Payment-Only"],
                created_at=datetime.utcnow(),
                resolved_by="SherlockAI Domain Filter"
            )
            results.append(result)
            
        elif smart_response["type"] == "historical_payment_issues":
            # Found historical payment issues
            for issue in smart_response["content"]:
                try:
                    result = SearchResult(
                        id=issue["id"],
                        title=issue["title"],
                        description=issue["description"],
                        resolution=issue["resolution"],
                        ai_suggestion=issue["ai_suggestion"],
                        score=issue["score"],
                        tags=issue["tags"],
                        created_at=datetime.fromisoformat(issue["created_at"]) if issue["created_at"] else datetime(2024, 1, 1),
                        resolved_by=issue["resolved_by"]
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(
                        "Failed to process historical payment issue",
                        issue_id=issue.get("id", "unknown"),
                        error=str(e)
                    )
                    continue
                    
        elif smart_response["type"] in ["ai_payment_solution", "ai_payment_solution_fallback"]:
            # AI-generated payment solution with learning
            pending_id = smart_response.get("pending_issue_id", "unknown")
            
            result = SearchResult(
                id=f"ai-payment-{pending_id}",
                title="AI-Generated Payment Solution",
                description=f"Payment issue: {search_request.query}",
                resolution=smart_response["content"],
                ai_suggestion=f"⚠️ This is an AI-generated solution (ID: {pending_id}). Please verify with your team and update the system with the actual resolution for future learning.",
                score=1.0,
                tags=["AI-Generated", "Payment-Domain", "Learning-System"],
                created_at=datetime.utcnow(),
                resolved_by="SherlockAI Payment Expert"
            )
            results.append(result)
            
        else:
            # Error case
            result = SearchResult(
                id="payment-error",
                title="Payment System Error",
                description=f"Error processing payment query: {search_request.query}",
                resolution=smart_response.get("content", "Unable to process payment query due to technical issues."),
                ai_suggestion="Please try again later or contact your payment engineering team for assistance.",
                score=1.0,
                tags=["Payment-Error", "System-Error"],
                created_at=datetime.utcnow(),
                resolved_by="SherlockAI Error Handler"
            )
            results.append(result)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Create response
        response_data = {
            "query": search_request.query,
            "results": results,
            "total_results": len(results),
            "execution_time_ms": execution_time_ms,
            "search_type": search_request.search_type,
            "timestamp": datetime.utcnow()
        }
        
        response = SearchResponse(**response_data)
        
        # Log search request in background
        background_tasks.add_task(
            log_search_request,
            db,
            request,
            search_request,
            [result.dict() for result in results],
            execution_time_ms
        )
        
        logger.info(
            "Payment search completed",
            query=search_request.query,
            response_type=smart_response["type"],
            results_count=len(results),
            execution_time_ms=execution_time_ms,
            domain_validation=smart_response.get("domain_validation", {})
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        logger.error(
            "Payment search request failed",
            query=search_request.query,
            error=str(e),
            execution_time_ms=execution_time_ms
        )
        raise HTTPException(
            status_code=500,
            detail=f"Payment search failed: {str(e)}"
        )


@router.get("/search/capabilities")
async def get_capabilities():
    """
    Get information about SherlockAI's capabilities
    """
    try:
        capabilities = {
            "title": "🔧 SherlockAI Capabilities",
            "description": "I can help you solve various technical issues based on historical data and AI-powered solutions.",
            "categories": [
                {
                    "name": "Payment Systems",
                    "issues": [
                        "UPI payment failures and timeouts",
                        "Payment gateway integration issues",
                        "Transaction processing errors",
                        "Refund and settlement problems",
                        "PSP routing and failover issues"
                    ]
                },
                {
                    "name": "API & Integration",
                    "issues": [
                        "API timeout and connection errors",
                        "Webhook delivery failures",
                        "Authentication and authorization issues",
                        "Rate limiting problems",
                        "SSL/TLS certificate issues"
                    ]
                },
                {
                    "name": "Database & Performance",
                    "issues": [
                        "Database connection timeouts",
                        "Query performance optimization",
                        "Connection pool exhaustion",
                        "Deadlock resolution",
                        "Index and schema issues"
                    ]
                },
                {
                    "name": "Infrastructure & Deployment",
                    "issues": [
                        "Service deployment failures",
                        "Configuration management",
                        "Load balancing issues",
                        "Monitoring and alerting",
                        "Resource scaling problems"
                    ]
                }
            ],
            "features": [
                "🔍 Semantic search through historical incidents",
                "🤖 AI-powered solution generation",
                "📊 Similarity scoring and ranking",
                "⚡ Fast response times",
                "🏷️ Intelligent tagging and categorization"
            ],
            "example_queries": [
                "UPI payment failed with error 5003",
                "Database connection timeout",
                "API returning 500 error",
                "Webhook not receiving callbacks",
                "SSL certificate expired"
            ]
        }
        
        return capabilities
        
    except Exception as e:
        logger.error("Failed to get capabilities", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve capabilities"
        )


@router.get("/search/suggestions")
async def get_search_suggestions():
    """
    Get popular search suggestions based on historical queries
    """
    try:
        # For now, return static suggestions
        # In production, this would query the database for popular searches
        suggestions = [
            "UPI payment failed with error 5003",
            "Webhook retries exhausted",
            "3DS timeout",
            "Card tokenization failing",
            "Settlement file parsing error",
            "OTP delivery latency",
            "Mandate creation timeout",
            "Refund webhook not processed",
            "Intent deeplink broken",
            "Authorization 3DS step fails"
        ]
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error("Failed to get search suggestions", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve search suggestions"
        )


@router.get("/search/history")
async def get_search_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_database)
):
    """
    Get recent search history (for analytics/debugging)
    """
    try:
        # This would typically require authentication
        # For demo purposes, returning recent searches
        
        from sqlalchemy import select, desc
        
        stmt = (
            select(SearchLog)
            .order_by(desc(SearchLog.timestamp))
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        search_logs = result.scalars().all()
        
        history = []
        for log in search_logs:
            history.append({
                "query": log.query,
                "timestamp": log.timestamp.isoformat(),
                "results_count": log.results_count,
                "execution_time_ms": log.execution_time_ms,
                "search_type": log.search_type
            })
        
        return {"history": history}
        
    except Exception as e:
        logger.error("Failed to get search history", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve search history"
        )
