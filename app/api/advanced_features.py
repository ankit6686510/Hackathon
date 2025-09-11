"""
Advanced API features for SherlockAI
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
import json
import time
from datetime import datetime, timedelta
import structlog

from app.services.ai_service import ai_service
from app.services.performance_optimizer import performance_optimizer, cached_search
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/advanced", tags=["Advanced Features"])

class StreamingSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    stream: bool = Field(True, description="Enable streaming response")
    include_reasoning: bool = Field(False, description="Include AI reasoning process")

class BulkSearchRequest(BaseModel):
    queries: List[str] = Field(..., description="List of queries to search")
    max_concurrent: int = Field(5, description="Maximum concurrent searches")

class SimilarityAnalysisRequest(BaseModel):
    issue_id: str = Field(..., description="Issue ID to analyze")
    threshold: float = Field(0.7, description="Similarity threshold")

class TrendAnalysisResponse(BaseModel):
    period: str
    issue_categories: Dict[str, int]
    resolution_times: Dict[str, float]
    common_patterns: List[str]
    recommendations: List[str]

@router.post("/search/streaming")
async def streaming_search(
    request: StreamingSearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Streaming search with real-time AI reasoning
    """
    async def generate_stream():
        try:
            # Start with search status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting semantic search...'})}\n\n"
            
            # Perform search
            search_start = time.time()
            search_results = await ai_service.semantic_search(
                query=request.query,
                top_k=3
            )
            search_time = time.time() - search_start
            
            yield f"data: {json.dumps({'type': 'search_complete', 'time': search_time, 'results_count': len(search_results)})}\n\n"
            
            # Stream each result
            for i, result in enumerate(search_results):
                yield f"data: {json.dumps({'type': 'result', 'index': i, 'data': result})}\n\n"
                await asyncio.sleep(0.1)  # Small delay for streaming effect
            
            # Generate AI suggestions with reasoning
            if request.include_reasoning:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Generating AI insights...'})}\n\n"
                
                ai_start = time.time()
                ai_response = await ai_service.generate_comprehensive_solution(
                    query=request.query,
                    search_results=search_results,
                    include_reasoning=True
                )
                ai_time = time.time() - ai_start
                
                yield f"data: {json.dumps({'type': 'ai_complete', 'time': ai_time, 'response': ai_response})}\n\n"
            
            # Final summary
            yield f"data: {json.dumps({'type': 'complete', 'total_time': time.time() - search_start})}\n\n"
            
        except Exception as e:
            logger.error("Streaming search failed", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@router.post("/search/bulk")
async def bulk_search(
    request: BulkSearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk search multiple queries concurrently
    """
    async def search_single_query(query: str) -> Dict[str, Any]:
        try:
            start_time = time.time()
            results = await ai_service.semantic_search(query=query, top_k=3)
            execution_time = time.time() - start_time
            
            return {
                "query": query,
                "results": results,
                "execution_time": execution_time,
                "status": "success"
            }
        except Exception as e:
            return {
                "query": query,
                "error": str(e),
                "status": "error"
            }
    
    # Create semaphore to limit concurrent searches
    semaphore = asyncio.Semaphore(request.max_concurrent)
    
    async def limited_search(query: str):
        async with semaphore:
            return await search_single_query(query)
    
    # Execute all searches concurrently
    start_time = time.time()
    tasks = [limited_search(query) for query in request.queries]
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Calculate statistics
    successful_searches = [r for r in results if r["status"] == "success"]
    failed_searches = [r for r in results if r["status"] == "error"]
    
    avg_execution_time = 0
    if successful_searches:
        avg_execution_time = sum(r["execution_time"] for r in successful_searches) / len(successful_searches)
    
    return {
        "results": results,
        "statistics": {
            "total_queries": len(request.queries),
            "successful": len(successful_searches),
            "failed": len(failed_searches),
            "total_time": total_time,
            "average_execution_time": avg_execution_time,
            "queries_per_second": len(request.queries) / total_time
        }
    }

@router.post("/analysis/similarity")
async def similarity_analysis(
    request: SimilarityAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze similarity patterns for a specific issue
    """
    try:
        # Get the target issue
        target_issue = await ai_service.get_issue_by_id(request.issue_id)
        if not target_issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        
        # Find similar issues
        similar_issues = await ai_service.find_similar_issues(
            issue_id=request.issue_id,
            threshold=request.threshold
        )
        
        # Analyze patterns
        patterns = await ai_service.analyze_similarity_patterns(
            target_issue=target_issue,
            similar_issues=similar_issues
        )
        
        return {
            "target_issue": target_issue,
            "similar_issues": similar_issues,
            "patterns": patterns,
            "analysis": {
                "total_similar": len(similar_issues),
                "avg_similarity": sum(issue["similarity"] for issue in similar_issues) / len(similar_issues) if similar_issues else 0,
                "common_tags": patterns.get("common_tags", []),
                "resolution_patterns": patterns.get("resolution_patterns", [])
            }
        }
        
    except Exception as e:
        logger.error("Similarity analysis failed", error=str(e), issue_id=request.issue_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/trends")
@cached_search(ttl=1800)  # Cache for 30 minutes
async def trend_analysis(
    period: str = "7d",
    db: AsyncSession = Depends(get_db)
) -> TrendAnalysisResponse:
    """
    Analyze trends in issues and resolutions
    """
    try:
        # Parse period
        if period == "7d":
            start_date = datetime.now() - timedelta(days=7)
        elif period == "30d":
            start_date = datetime.now() - timedelta(days=30)
        elif period == "90d":
            start_date = datetime.now() - timedelta(days=90)
        else:
            raise HTTPException(status_code=400, detail="Invalid period. Use 7d, 30d, or 90d")
        
        # Analyze trends (this would typically query your database)
        trends = await ai_service.analyze_trends(start_date=start_date)
        
        # Generate recommendations based on trends
        recommendations = await ai_service.generate_trend_recommendations(trends)
        
        return TrendAnalysisResponse(
            period=period,
            issue_categories=trends.get("categories", {}),
            resolution_times=trends.get("resolution_times", {}),
            common_patterns=trends.get("patterns", []),
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error("Trend analysis failed", error=str(e), period=period)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search/explain")
async def explain_search_results(
    query: str,
    result_ids: List[str],
    db: AsyncSession = Depends(get_db)
):
    """
    Explain why specific results were returned for a query
    """
    try:
        explanation = await ai_service.explain_search_results(
            query=query,
            result_ids=result_ids
        )
        
        return {
            "query": query,
            "explanation": explanation,
            "factors": {
                "semantic_similarity": explanation.get("semantic_factors", []),
                "keyword_matches": explanation.get("keyword_factors", []),
                "contextual_relevance": explanation.get("context_factors", [])
            }
        }
        
    except Exception as e:
        logger.error("Search explanation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/cache-stats")
async def get_cache_performance():
    """
    Get detailed cache performance statistics
    """
    try:
        stats = await performance_optimizer.get_cache_stats()
        
        # Add additional performance metrics
        extended_stats = {
            **stats,
            "performance_impact": {
                "estimated_time_saved": stats["hits"] * 0.5,  # Assume 500ms saved per cache hit
                "bandwidth_saved": stats["hits"] * 2048,  # Assume 2KB saved per hit
                "cost_efficiency": stats["hit_rate_percent"]
            }
        }
        
        return extended_stats
        
    except Exception as e:
        logger.error("Cache stats retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/warm-cache")
async def warm_cache(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Warm up the cache with popular queries
    """
    try:
        background_tasks.add_task(performance_optimizer.warm_cache, db)
        
        return {
            "message": "Cache warming started in background",
            "estimated_completion": "2-3 minutes"
        }
        
    except Exception as e:
        logger.error("Cache warming failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check with performance metrics
    """
    try:
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "performance": {},
            "resources": {}
        }
        
        # Check AI service
        ai_start = time.time()
        ai_healthy = await ai_service.health_check()
        ai_time = time.time() - ai_start
        
        health_data["services"]["ai_service"] = {
            "status": "healthy" if ai_healthy else "unhealthy",
            "response_time": ai_time
        }
        
        # Check cache
        cache_stats = await performance_optimizer.get_cache_stats()
        health_data["services"]["cache"] = {
            "status": "healthy" if cache_stats["redis_connected"] else "unhealthy",
            "hit_rate": cache_stats["hit_rate_percent"]
        }
        
        # Check database
        db_start = time.time()
        try:
            await db.execute("SELECT 1")
            db_time = time.time() - db_start
            health_data["services"]["database"] = {
                "status": "healthy",
                "response_time": db_time
            }
        except Exception:
            health_data["services"]["database"] = {
                "status": "unhealthy",
                "response_time": None
            }
        
        # Overall health
        all_healthy = all(
            service["status"] == "healthy" 
            for service in health_data["services"].values()
        )
        
        health_data["overall_status"] = "healthy" if all_healthy else "degraded"
        
        return health_data
        
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
