"""
Analytics and feedback API endpoints
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from pydantic import BaseModel, Field
import structlog

from app.database import get_database
from app.models import SearchLog, FeedbackLog
from app.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class FeedbackRequest(BaseModel):
    """Feedback request model"""
    query: str = Field(..., description="Original search query")
    result_id: str = Field(..., description="ID of the result being rated")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback_text: Optional[str] = Field(None, description="Optional feedback text")
    helpful: bool = Field(..., description="Whether the result was helpful")


class AnalyticsResponse(BaseModel):
    """Analytics response model"""
    total_searches: int
    avg_execution_time: float
    top_queries: List[Dict[str, Any]]
    search_trends: List[Dict[str, Any]]
    feedback_summary: Dict[str, Any]


@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database)
):
    """
    Submit feedback for search results
    """
    try:
        # Create feedback log entry
        feedback_log = FeedbackLog(
            query=feedback.query,
            result_id=feedback.result_id,
            rating=feedback.rating,
            feedback_text=feedback.feedback_text,
            helpful=feedback.helpful,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        db.add(feedback_log)
        await db.commit()
        
        logger.info(
            "Feedback submitted",
            query=feedback.query,
            result_id=feedback.result_id,
            rating=feedback.rating,
            helpful=feedback.helpful
        )
        
        return {
            "message": "Feedback submitted successfully",
            "feedback_id": feedback_log.id
        }
        
    except Exception as e:
        logger.error("Failed to submit feedback", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to submit feedback"
        )


@router.get("/dashboard", response_model=AnalyticsResponse)
async def get_analytics_dashboard(
    days: int = 7,
    db: AsyncSession = Depends(get_database)
):
    """
    Get analytics dashboard data
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Total searches
        total_searches_stmt = select(func.count(SearchLog.id)).where(
            SearchLog.timestamp >= start_date
        )
        total_searches_result = await db.execute(total_searches_stmt)
        total_searches = total_searches_result.scalar() or 0
        
        # Average execution time
        avg_time_stmt = select(func.avg(SearchLog.execution_time_ms)).where(
            SearchLog.timestamp >= start_date
        )
        avg_time_result = await db.execute(avg_time_stmt)
        avg_execution_time = float(avg_time_result.scalar() or 0)
        
        # Top queries
        top_queries_stmt = (
            select(
                SearchLog.query,
                func.count(SearchLog.id).label("count"),
                func.avg(SearchLog.execution_time_ms).label("avg_time"),
                func.avg(SearchLog.results_count).label("avg_results")
            )
            .where(SearchLog.timestamp >= start_date)
            .group_by(SearchLog.query)
            .order_by(desc("count"))
            .limit(10)
        )
        top_queries_result = await db.execute(top_queries_stmt)
        top_queries = [
            {
                "query": row.query,
                "count": row.count,
                "avg_execution_time": float(row.avg_time or 0),
                "avg_results": float(row.avg_results or 0)
            }
            for row in top_queries_result
        ]
        
        # Search trends (daily)
        search_trends = []
        for i in range(days):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_count_stmt = select(func.count(SearchLog.id)).where(
                and_(
                    SearchLog.timestamp >= day_start,
                    SearchLog.timestamp < day_end
                )
            )
            day_count_result = await db.execute(day_count_stmt)
            day_count = day_count_result.scalar() or 0
            
            search_trends.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "searches": day_count
            })
        
        # Feedback summary
        feedback_summary_stmt = (
            select(
                func.count(FeedbackLog.id).label("total_feedback"),
                func.avg(FeedbackLog.rating).label("avg_rating"),
                func.sum(func.cast(FeedbackLog.helpful, func.INTEGER)).label("helpful_count")
            )
            .where(FeedbackLog.timestamp >= start_date)
        )
        feedback_summary_result = await db.execute(feedback_summary_stmt)
        feedback_row = feedback_summary_result.first()
        
        feedback_summary = {
            "total_feedback": feedback_row.total_feedback or 0,
            "average_rating": float(feedback_row.avg_rating or 0),
            "helpful_percentage": (
                (feedback_row.helpful_count / feedback_row.total_feedback * 100)
                if feedback_row.total_feedback and feedback_row.helpful_count
                else 0
            )
        }
        
        return AnalyticsResponse(
            total_searches=total_searches,
            avg_execution_time=avg_execution_time,
            top_queries=top_queries,
            search_trends=search_trends,
            feedback_summary=feedback_summary
        )
        
    except Exception as e:
        logger.error("Failed to get analytics dashboard", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve analytics data"
        )


@router.get("/search-patterns")
async def get_search_patterns(
    days: int = 30,
    db: AsyncSession = Depends(get_database)
):
    """
    Analyze search patterns and trends
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Most common search terms
        common_terms_stmt = (
            select(
                SearchLog.query,
                func.count(SearchLog.id).label("frequency"),
                func.avg(SearchLog.results_count).label("avg_results"),
                func.max(SearchLog.timestamp).label("last_searched")
            )
            .where(SearchLog.timestamp >= start_date)
            .group_by(SearchLog.query)
            .order_by(desc("frequency"))
            .limit(20)
        )
        common_terms_result = await db.execute(common_terms_stmt)
        common_terms = [
            {
                "query": row.query,
                "frequency": row.frequency,
                "avg_results": float(row.avg_results or 0),
                "last_searched": row.last_searched.isoformat()
            }
            for row in common_terms_result
        ]
        
        # Search performance by hour
        hourly_performance_stmt = (
            select(
                func.extract('hour', SearchLog.timestamp).label("hour"),
                func.count(SearchLog.id).label("search_count"),
                func.avg(SearchLog.execution_time_ms).label("avg_time")
            )
            .where(SearchLog.timestamp >= start_date)
            .group_by("hour")
            .order_by("hour")
        )
        hourly_performance_result = await db.execute(hourly_performance_stmt)
        hourly_performance = [
            {
                "hour": int(row.hour),
                "search_count": row.search_count,
                "avg_execution_time": float(row.avg_time or 0)
            }
            for row in hourly_performance_result
        ]
        
        # Zero result queries
        zero_results_stmt = (
            select(SearchLog.query, func.count(SearchLog.id).label("count"))
            .where(
                and_(
                    SearchLog.timestamp >= start_date,
                    SearchLog.results_count == 0
                )
            )
            .group_by(SearchLog.query)
            .order_by(desc("count"))
            .limit(10)
        )
        zero_results_result = await db.execute(zero_results_stmt)
        zero_results = [
            {
                "query": row.query,
                "count": row.count
            }
            for row in zero_results_result
        ]
        
        return {
            "common_search_terms": common_terms,
            "hourly_performance": hourly_performance,
            "zero_result_queries": zero_results,
            "analysis_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            }
        }
        
    except Exception as e:
        logger.error("Failed to get search patterns", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve search patterns"
        )


@router.get("/performance-metrics")
async def get_performance_metrics(
    days: int = 7,
    db: AsyncSession = Depends(get_database)
):
    """
    Get detailed performance metrics
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Performance percentiles
        performance_stmt = (
            select(SearchLog.execution_time_ms)
            .where(SearchLog.timestamp >= start_date)
            .order_by(SearchLog.execution_time_ms)
        )
        performance_result = await db.execute(performance_stmt)
        execution_times = [row.execution_time_ms for row in performance_result]
        
        if execution_times:
            def percentile(data, p):
                n = len(data)
                index = p * (n - 1) / 100
                if index.is_integer():
                    return data[int(index)]
                else:
                    lower = data[int(index)]
                    upper = data[int(index) + 1]
                    return lower + (upper - lower) * (index - int(index))
            
            performance_metrics = {
                "min_time": min(execution_times),
                "max_time": max(execution_times),
                "avg_time": sum(execution_times) / len(execution_times),
                "p50": percentile(execution_times, 50),
                "p90": percentile(execution_times, 90),
                "p95": percentile(execution_times, 95),
                "p99": percentile(execution_times, 99),
                "total_requests": len(execution_times)
            }
        else:
            performance_metrics = {
                "min_time": 0,
                "max_time": 0,
                "avg_time": 0,
                "p50": 0,
                "p90": 0,
                "p95": 0,
                "p99": 0,
                "total_requests": 0
            }
        
        # Error rate analysis
        error_rate_stmt = (
            select(
                func.count(SearchLog.id).label("total"),
                func.sum(
                    func.case(
                        (SearchLog.results_count == 0, 1),
                        else_=0
                    )
                ).label("zero_results")
            )
            .where(SearchLog.timestamp >= start_date)
        )
        error_rate_result = await db.execute(error_rate_stmt)
        error_row = error_rate_result.first()
        
        total_requests = error_row.total or 0
        zero_results = error_row.zero_results or 0
        
        error_metrics = {
            "total_requests": total_requests,
            "zero_result_requests": zero_results,
            "zero_result_rate": (zero_results / total_requests * 100) if total_requests > 0 else 0,
            "success_rate": ((total_requests - zero_results) / total_requests * 100) if total_requests > 0 else 0
        }
        
        return {
            "performance_metrics": performance_metrics,
            "error_metrics": error_metrics,
            "analysis_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            }
        }
        
    except Exception as e:
        logger.error("Failed to get performance metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve performance metrics"
        )
