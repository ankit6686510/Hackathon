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
    Search for similar issues using AI-powered semantic search
    
    This endpoint performs semantic search across historical issues to find
    the most relevant solutions and generates AI-powered fix suggestions.
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
        
        # Check cache first
        cache_key = generate_search_cache_key(search_request)
        try:
            redis_client = await get_redis()
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                logger.info("Retrieved search results from cache", cache_key=cache_key)
                cached_data = json.loads(cached_result)
                
                # Update execution time for cache hit
                cached_data["execution_time_ms"] = (time.time() - start_time) * 1000
                cached_data["timestamp"] = datetime.utcnow().isoformat()
                
                # Log cache hit
                background_tasks.add_task(
                    log_search_request,
                    db,
                    request,
                    search_request,
                    cached_data["results"],
                    cached_data["execution_time_ms"]
                )
                
                return SearchResponse(**cached_data)
        except Exception as e:
            logger.warning("Cache retrieval failed", error=str(e))
        
        # Generate query embedding
        logger.info("Generating embedding for search query", query=search_request.query)
        query_embedding = await ai_service.embed_text(search_request.query)
        
        # Prepare filters for vector search
        vector_filters = {}
        if search_request.include_resolved_only:
            vector_filters["status"] = {"$eq": "resolved"}
        
        # Add custom filters
        if search_request.filters:
            vector_filters.update(search_request.filters)
        
        # Search similar issues
        logger.info("Searching for similar issues", top_k=search_request.top_k)
        similar_issues = await ai_service.search_similar(
            query_embedding=query_embedding,
            top_k=search_request.top_k,
            similarity_threshold=search_request.similarity_threshold,
            filters=vector_filters if vector_filters else None
        )
        
        # Generate AI suggestions for each result
        results = []
        for issue in similar_issues:
            try:
                # Generate fix suggestion using the issue data directly
                issue_metadata = {
                    "id": issue["id"],
                    "title": issue["title"],
                    "description": issue["description"],
                    "resolution": issue["resolution"],
                    "tags": issue["tags"]
                }
                
                ai_suggestion = await ai_service.generate_fix_suggestion(
                    issue_metadata=issue_metadata,
                    query=search_request.query
                )
                
                # Create search result
                result = SearchResult(
                    id=issue["id"],
                    title=issue["title"],
                    description=issue["description"],
                    resolution=issue["resolution"],
                    ai_suggestion=ai_suggestion,
                    score=issue["score"],
                    tags=issue["tags"],
                    created_at=datetime.fromisoformat(issue["created_at"]) if issue["created_at"] else datetime(2024, 1, 1),
                    resolved_by=issue["resolved_by"]
                )
                results.append(result)
                
            except Exception as e:
                logger.error(
                    "Failed to process search result",
                    issue_id=issue.get("id", "unknown"),
                    error=str(e)
                )
                continue
        
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
        
        # Cache the results
        try:
            redis_client = await get_redis()
            cache_data = response.dict()
            cache_data["timestamp"] = cache_data["timestamp"].isoformat()
            cache_data["results"] = [
                {**result.dict(), "created_at": result.created_at.isoformat()}
                for result in results
            ]
            
            await redis_client.setex(
                cache_key,
                settings.cache_ttl_search,
                json.dumps(cache_data, default=str)
            )
            logger.debug("Cached search results", cache_key=cache_key)
        except Exception as e:
            logger.warning("Failed to cache search results", error=str(e))
        
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
            "Search completed successfully",
            query=search_request.query,
            results_count=len(results),
            execution_time_ms=execution_time_ms
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        logger.error(
            "Search request failed",
            query=search_request.query,
            error=str(e),
            execution_time_ms=execution_time_ms
        )
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
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
