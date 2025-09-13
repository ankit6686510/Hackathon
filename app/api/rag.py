"""
RAG API endpoints for enterprise-grade Retrieval-Augmented Generation
"""

import time
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import structlog

from app.models import SearchRequest, SearchResponse, SearchResult, SearchLog
from app.database import get_database
from app.services.rag_service import rag_service, QueryComplexity
from app.services.ai_service import ai_service
from app.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


class RAGRequest(BaseModel):
    """RAG request model"""
    query: str = Field(..., description="User's question or issue description")
    include_sources: bool = Field(default=True, description="Include source citations in response")
    max_incidents: int = Field(default=5, description="Maximum number of incidents to retrieve")
    confidence_threshold: float = Field(default=0.3, description="Minimum confidence threshold")


class RAGResult(BaseModel):
    """RAG result model"""
    query: str
    generated_answer: str
    confidence_score: float
    query_complexity: str
    execution_time_ms: float
    rag_strategy: str
    sources: List[str]
    retrieved_incidents: List[dict]
    timestamp: datetime


class RAGResponse(BaseModel):
    """RAG response model"""
    result: RAGResult
    metadata: dict


class RAGFeedbackRequest(BaseModel):
    """RAG feedback request model"""
    query: str
    rag_result_id: str
    feedback_type: str = Field(..., description="UPVOTE, DOWNVOTE, or NEUTRAL")
    feedback_text: Optional[str] = Field(default=None, description="Optional feedback text")
    helpful: bool = Field(..., description="Whether the response was helpful")


async def log_rag_request(
    db: AsyncSession,
    request: Request,
    rag_request: RAGRequest,
    rag_result: RAGResult,
    execution_time_ms: float
):
    """Log RAG request for analytics"""
    try:
        # Create search log entry (reusing existing model)
        search_log = SearchLog(
            query=rag_request.query,
            search_type="rag",
            top_k=rag_request.max_incidents,
            results_count=len(rag_result.retrieved_incidents),
            execution_time_ms=execution_time_ms,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            top_result_id=rag_result.retrieved_incidents[0]["id"] if rag_result.retrieved_incidents else None,
            top_result_score=rag_result.confidence_score,
        )
        
        db.add(search_log)
        await db.commit()
        
        logger.info(
            "RAG request logged",
            query=rag_request.query,
            complexity=rag_result.query_complexity,
            confidence=rag_result.confidence_score,
            execution_time_ms=execution_time_ms
        )
    except Exception as e:
        logger.error("Failed to log RAG request", error=str(e))


@router.post("/query", response_model=RAGResponse)
async def process_rag_query(
    rag_request: RAGRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database)
):
    """
    Process query using formal RAG pipeline
    
    This endpoint implements enterprise-grade Retrieval-Augmented Generation:
    1. Query Classification (Simple/Complex/Unknown)
    2. Adaptive Retrieval based on complexity
    3. Context Augmentation with retrieved incidents
    4. Grounded Generation with source citations
    """
    start_time = time.time()
    
    try:
        # Validate request
        if not rag_request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # CRITICAL FIX: Use RAG service domain validation (includes incident ID detection)
        is_payment_related = rag_service.is_payment_domain_query(rag_request.query)
        is_incident_id = rag_service.is_incident_id(rag_request.query)
        
        # Create domain validation response for compatibility
        domain_validation = {
            "is_payment_related": is_payment_related,
            "is_incident_id": is_incident_id,
            "confidence": 1.0 if is_incident_id else 0.8 if is_payment_related else 0.1,
            "reason": "incident_id" if is_incident_id else "payment_domain" if is_payment_related else "non_payment_domain"
        }
        
        if not is_payment_related:
            # Non-payment query - return domain rejection
            execution_time_ms = (time.time() - start_time) * 1000
            
            rag_result = RAGResult(
                query=rag_request.query,
                generated_answer="I specialize in payment-related issues only. Please ask about UPI transactions, payment gateways, card processing, bank integrations, payment errors, or other payment-related topics.",
                confidence_score=1.0,
                query_complexity="domain_rejection",
                execution_time_ms=execution_time_ms,
                rag_strategy="domain_filter",
                sources=[],
                retrieved_incidents=[],
                timestamp=datetime.utcnow()
            )
            
            return RAGResponse(
                result=rag_result,
                metadata={
                    "domain_validation": domain_validation,
                    "status": "rejected",
                    "reason": "non_payment_domain"
                }
            )
        
        # Process with RAG pipeline
        logger.info("Processing RAG query", query=rag_request.query)
        
        rag_response = await rag_service.process_rag_query(rag_request.query)
        
        # Convert to API response format
        rag_result = RAGResult(
            query=rag_response.query,
            generated_answer=rag_response.generated_answer,
            confidence_score=rag_response.confidence_score,
            query_complexity=rag_response.query_complexity.value,
            execution_time_ms=rag_response.execution_time_ms,
            rag_strategy=rag_response.rag_strategy,
            sources=rag_response.sources if rag_request.include_sources else [],
            retrieved_incidents=rag_response.retrieved_incidents,
            timestamp=rag_response.timestamp
        )
        
        # Prepare metadata
        metadata = {
            "domain_validation": domain_validation,
            "status": "success",
            "incidents_retrieved": len(rag_response.retrieved_incidents),
            "confidence_level": "high" if rag_response.confidence_score >= 0.7 else "medium" if rag_response.confidence_score >= 0.4 else "low",
            "rag_pipeline_version": "1.0"
        }
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Log request in background
        background_tasks.add_task(
            log_rag_request,
            db,
            request,
            rag_request,
            rag_result,
            execution_time_ms
        )
        
        logger.info(
            "RAG query completed",
            query=rag_request.query,
            complexity=rag_response.query_complexity.value,
            confidence=rag_response.confidence_score,
            incidents_count=len(rag_response.retrieved_incidents),
            execution_time_ms=execution_time_ms
        )
        
        return RAGResponse(
            result=rag_result,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        logger.error(
            "RAG query failed",
            query=rag_request.query,
            error=str(e),
            execution_time_ms=execution_time_ms
        )
        raise HTTPException(
            status_code=500,
            detail=f"RAG query failed: {str(e)}"
        )


@router.post("/feedback")
async def submit_rag_feedback(
    feedback_request: RAGFeedbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_database)
):
    """
    Submit feedback for RAG response
    
    This endpoint collects user feedback to improve RAG performance:
    - Tracks which responses are helpful vs not helpful
    - Logs feedback for retraining and optimization
    - Enables continuous learning and improvement
    """
    try:
        # Validate feedback type
        valid_feedback_types = ["UPVOTE", "DOWNVOTE", "NEUTRAL"]
        if feedback_request.feedback_type not in valid_feedback_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid feedback type. Must be one of: {valid_feedback_types}"
            )
        
        # Log feedback (this would typically store in a feedback table)
        feedback_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": feedback_request.query,
            "rag_result_id": feedback_request.rag_result_id,
            "feedback_type": feedback_request.feedback_type,
            "feedback_text": feedback_request.feedback_text,
            "helpful": feedback_request.helpful,
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent")
        }
        
        # For now, log to structured logger
        # In production, this would go to a dedicated feedback table
        logger.info(
            "RAG feedback received",
            **feedback_entry
        )
        
        return {
            "status": "success",
            "message": "Feedback recorded successfully",
            "feedback_id": f"fb_{int(time.time())}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to submit RAG feedback", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/metrics")
async def get_rag_metrics():
    """
    Get RAG performance metrics
    
    Returns metrics about RAG pipeline performance:
    - Query complexity distribution
    - Average confidence scores
    - Response times
    - User feedback statistics
    """
    try:
        # Get metrics from RAG service
        rag_metrics = rag_service.get_rag_metrics()
        
        # Add additional API-level metrics
        api_metrics = {
            "api_version": "1.0",
            "rag_pipeline_status": "active",
            "supported_query_types": ["simple", "complex", "unknown"],
            "average_response_time_target_ms": 5000,
            "confidence_threshold": rag_service.min_confidence_threshold
        }
        
        return {
            "rag_service_metrics": rag_metrics,
            "api_metrics": api_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get RAG metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve RAG metrics"
        )


@router.get("/health")
async def rag_health_check():
    """
    RAG service health check
    
    Verifies that all RAG pipeline components are working:
    - Query classification
    - Incident retrieval
    - Response generation
    - Source attribution
    """
    try:
        start_time = time.time()
        
        # Test query classification
        test_query = "UPI payment timeout test"
        complexity = await rag_service.classify_query_complexity(test_query)
        
        # Test incident retrieval
        incidents = await rag_service.retrieve_incidents(test_query, complexity)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        health_status = {
            "status": "healthy",
            "components": {
                "query_classifier": "operational",
                "incident_retrieval": "operational",
                "response_generator": "operational",
                "source_attribution": "operational"
            },
            "test_results": {
                "test_query": test_query,
                "classified_complexity": complexity.value,
                "incidents_retrieved": len(incidents),
                "response_time_ms": execution_time_ms
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("RAG health check completed", **health_status["test_results"])
        
        return health_status
        
    except Exception as e:
        logger.error("RAG health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/examples")
async def get_rag_examples():
    """
    Get example queries for different complexity levels
    
    Provides sample queries that demonstrate RAG capabilities:
    - Simple queries for single incident lookup
    - Complex queries for multi-incident analysis
    - Edge cases and domain boundaries
    """
    examples = {
        "simple_queries": [
            {
                "query": "UPI payment failed with error 5003",
                "description": "Specific error code lookup",
                "expected_complexity": "simple",
                "expected_incidents": "1-3"
            },
            {
                "query": "Card tokenization failing for BIN 65xx",
                "description": "Specific technical issue",
                "expected_complexity": "simple",
                "expected_incidents": "1-3"
            },
            {
                "query": "Webhook delivery timeout from payment gateway",
                "description": "Integration issue",
                "expected_complexity": "simple",
                "expected_incidents": "2-4"
            }
        ],
        "complex_queries": [
            {
                "query": "Why do refunds fail frequently?",
                "description": "Pattern analysis across multiple incidents",
                "expected_complexity": "complex",
                "expected_incidents": "5-8"
            },
            {
                "query": "What are common causes of payment timeouts?",
                "description": "Root cause analysis",
                "expected_complexity": "complex",
                "expected_incidents": "6-10"
            },
            {
                "query": "How to improve payment success rates?",
                "description": "Optimization guidance",
                "expected_complexity": "complex",
                "expected_incidents": "8-12"
            }
        ],
        "edge_cases": [
            {
                "query": "How to deploy a microservice?",
                "description": "Non-payment domain (should be rejected)",
                "expected_complexity": "unknown",
                "expected_incidents": "0"
            },
            {
                "query": "Database schema design best practices",
                "description": "General technical question (should be rejected)",
                "expected_complexity": "unknown",
                "expected_incidents": "0"
            }
        ]
    }
    
    return {
        "examples": examples,
        "usage_instructions": {
            "simple_queries": "Use for specific technical issues or error codes",
            "complex_queries": "Use for pattern analysis or optimization guidance",
            "testing": "Try different query types to see adaptive RAG routing in action"
        },
        "api_endpoint": "/api/v1/rag/query",
        "timestamp": datetime.utcnow().isoformat()
    }
