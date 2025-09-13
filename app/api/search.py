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
from app.services.hybrid_search import hybrid_search_service
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


@router.post("/search/hybrid", response_model=SearchResponse)
async def hybrid_search_issues(
    search_request: SearchRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database)
):
    """
    Search for payment-related issues using Hybrid Search (Semantic + BM25 + TF-IDF)
    
    This endpoint performs hybrid search combining semantic similarity, BM25 keyword matching,
    and TF-IDF scoring to find the most relevant solutions with better coverage.
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
        
        # Validate payment domain
        domain_validation = ai_service.validate_payment_domain(search_request.query)
        
        if not domain_validation["is_payment_related"]:
            # Non-payment query - return rejection message
            result = SearchResult(
                id="domain-rejection",
                title="Payment Domain Only",
                description="This system specializes in payment-related issues only.",
                resolution="I specialize in payment-related issues only. Please ask about UPI transactions, payment gateways, card processing, bank integrations, payment errors, or other payment-related topics.",
                ai_suggestion="Please ask about UPI transactions, payment gateways, card processing, bank integrations, payment errors, or other payment-related topics.",
                score=1.0,
                tags=["Domain-Restriction", "Payment-Only"],
                created_at=datetime.utcnow(),
                resolved_by="SherlockAI Domain Filter"
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            response = SearchResponse(
                query=search_request.query,
                results=[result],
                total_results=1,
                execution_time_ms=execution_time_ms,
                search_type="domain_validation",
                timestamp=datetime.utcnow()
            )
            return response
        
        # Perform hybrid search
        logger.info("Processing payment domain query with hybrid search", query=search_request.query)
        hybrid_results = await hybrid_search_service.hybrid_search(
            query=search_request.query,
            top_k=search_request.top_k,
            min_score=0.1  # Lower threshold for better coverage
        )
        
        results = []
        
        if hybrid_results:
            # Process hybrid search results
            for hybrid_result in hybrid_results:
                try:
                    # Generate AI suggestion for each result
                    ai_suggestion = await ai_service.generate_fix_suggestion(hybrid_result, search_request.query)
                    
                    # Handle date parsing
                    try:
                        created_at = hybrid_result.get('created_at', '')
                        if created_at and isinstance(created_at, str):
                            parsed_date = datetime.fromisoformat(created_at)
                        else:
                            parsed_date = datetime(2024, 1, 1)
                    except (ValueError, TypeError):
                        parsed_date = datetime(2024, 1, 1)
                    
                    result = SearchResult(
                        id=hybrid_result.get('id', ''),
                        title=hybrid_result.get('title', ''),
                        description=hybrid_result.get('description', ''),
                        resolution=hybrid_result.get('resolution', ''),
                        ai_suggestion=ai_suggestion,
                        score=hybrid_result.get('fused_score', 0.0),
                        tags=hybrid_result.get('tags', []),
                        created_at=parsed_date,
                        resolved_by=str(hybrid_result.get('resolved_by', ''))
                    )
                    results.append(result)
                    
                    logger.info(
                        "Successfully processed hybrid search result",
                        issue_id=hybrid_result.get('id', ''),
                        title=hybrid_result.get('title', '')[:50] + "..." if len(hybrid_result.get('title', '')) > 50 else hybrid_result.get('title', ''),
                        fused_score=hybrid_result.get('fused_score', 0.0),
                        search_methods=hybrid_result.get('search_methods', [])
                    )
                    
                except Exception as e:
                    logger.error(
                        "Failed to process hybrid search result",
                        issue_id=hybrid_result.get('id', 'unknown'),
                        error=str(e)
                    )
        
        # If no results found, provide helpful fallback
        if not results:
            # Try to get suggestions based on query keywords
            suggestions = await hybrid_search_service.get_search_suggestions(search_request.query)
            
            suggestion_text = ""
            if suggestions:
                suggestion_text = f"\n\n💡 **You might want to search for:**\n" + "\n".join([f"• {s}" for s in suggestions])
            
            result = SearchResult(
                id="no-results-found",
                title="No Matching Issues Found",
                description=f"No exact matches found for '{search_request.query}' in our knowledge base.",
                resolution=f"This might be a new type of issue that hasn't been encountered before.{suggestion_text}\n\n**Next Steps:**\n• Check recent documentation\n• Contact the team that owns the affected service\n• Document this issue for future reference once resolved",
                ai_suggestion="Consider searching with different keywords or check if this is a new issue that needs to be documented.",
                score=1.0,
                tags=["No-Results", "New-Issue"],
                created_at=datetime.utcnow(),
                resolved_by="SherlockAI Hybrid Search"
            )
            results.append(result)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Create response
        response = SearchResponse(
            query=search_request.query,
            results=results,
            total_results=len(results),
            execution_time_ms=execution_time_ms,
            search_type="hybrid",
            timestamp=datetime.utcnow()
        )
        
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
            "Hybrid search completed",
            query=search_request.query,
            results_count=len(results),
            execution_time_ms=execution_time_ms,
            domain_validation=domain_validation
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        logger.error(
            "Hybrid search request failed",
            query=search_request.query,
            error=str(e),
            execution_time_ms=execution_time_ms
        )
        raise HTTPException(
            status_code=500,
            detail=f"Hybrid search failed: {str(e)}"
        )


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
                    # Extract metadata if it exists, otherwise use issue data directly
                    metadata = issue.get("metadata", {})
                    
                    # Get values from metadata first, then fallback to issue level
                    issue_id = issue.get("id", "unknown")
                    title = metadata.get("title", issue.get("title", ""))
                    description = metadata.get("description", issue.get("description", ""))
                    resolution = metadata.get("resolution", issue.get("resolution", ""))
                    tags = metadata.get("tags", issue.get("tags", []))
                    created_at = metadata.get("created_at", issue.get("created_at", ""))
                    resolved_by = metadata.get("resolved_by", issue.get("resolved_by", ""))
                    score = issue.get("score", 0.0)
                    ai_suggestion = issue.get("ai_suggestion", "")
                    
                    # If ai_suggestion is empty, provide a fallback
                    if not ai_suggestion:
                        ai_suggestion = "Fix suggestion temporarily unavailable due to API quota limits. Please refer to the resolution details above."
                    
                    # Handle date parsing more robustly
                    try:
                        if created_at and isinstance(created_at, str):
                            parsed_date = datetime.fromisoformat(created_at)
                        else:
                            parsed_date = datetime(2024, 1, 1)
                    except (ValueError, TypeError):
                        parsed_date = datetime(2024, 1, 1)
                    
                    result = SearchResult(
                        id=issue_id,
                        title=title,
                        description=description,
                        resolution=resolution,
                        ai_suggestion=ai_suggestion,
                        score=score,
                        tags=tags if isinstance(tags, list) else [],
                        created_at=parsed_date,
                        resolved_by=resolved_by if isinstance(resolved_by, str) else str(resolved_by)
                    )
                    results.append(result)
                    
                    logger.info(
                        "Successfully processed historical payment issue",
                        issue_id=issue_id,
                        title=title[:50] + "..." if len(title) > 50 else title,
                        score=score
                    )
                    
                except Exception as e:
                    logger.error(
                        "Failed to process historical payment issue",
                        issue_id=issue.get("id", "unknown"),
                        error=str(e),
                        issue_data=str(issue)[:200] + "..." if len(str(issue)) > 200 else str(issue)
                    )
                    # Don't continue - try to create a minimal result
                    try:
                        minimal_result = SearchResult(
                            id=issue.get("id", "unknown"),
                            title=issue.get("title", "Issue processing error"),
                            description="Error processing this issue",
                            resolution="Please contact support",
                            ai_suggestion="Unable to process this issue due to technical error",
                            score=issue.get("score", 0.0),
                            tags=["Error"],
                            created_at=datetime(2024, 1, 1),
                            resolved_by="System"
                        )
                        results.append(minimal_result)
                    except Exception as e2:
                        logger.error("Failed to create minimal result", error=str(e2))
                    
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
