"""
Slack Extraction API Endpoints
Provides endpoints to extract incidents from Slack #issues channel
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio

from app.services.slack_extractor import extract_and_learn_from_slack, start_continuous_monitoring

router = APIRouter(prefix="/api/v1/slack", tags=["slack-extraction"])


class SlackExtractionRequest(BaseModel):
    """Request model for Slack extraction"""
    hours_back: int = 24
    auto_add_to_knowledge_base: bool = True


class SlackExtractionResponse(BaseModel):
    """Response model for Slack extraction"""
    success: bool
    incidents_found: int
    incidents_added: int
    message: str
    incidents: Optional[list] = None
    error: Optional[str] = None


# Global monitoring task
monitoring_task = None


@router.post("/extract", response_model=SlackExtractionResponse)
async def extract_incidents_from_slack(request: SlackExtractionRequest):
    """
    Extract incidents from Slack #issues channel
    
    This endpoint analyzes recent messages in your #issues channel and automatically
    extracts incident information using AI, then adds it to your knowledge base.
    """
    try:
        result = await extract_and_learn_from_slack(hours_back=request.hours_back)
        
        if result["success"]:
            return SlackExtractionResponse(
                success=True,
                incidents_found=result["incidents_found"],
                incidents_added=result["incidents_added"],
                message=result.get("message", f"Successfully extracted {result['incidents_found']} incidents"),
                incidents=result.get("incidents", [])
            )
        else:
            return SlackExtractionResponse(
                success=False,
                incidents_found=0,
                incidents_added=0,
                message="Failed to extract incidents",
                error=result.get("error", "Unknown error")
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/start-monitoring")
async def start_slack_monitoring(background_tasks: BackgroundTasks):
    """
    Start continuous monitoring of Slack #issues channel
    
    This will monitor your #issues channel every 5 minutes and automatically
    extract and add new incidents to your knowledge base.
    """
    global monitoring_task
    
    if monitoring_task and not monitoring_task.done():
        return {
            "success": False,
            "message": "Monitoring is already running",
            "status": "already_running"
        }
    
    try:
        # Start monitoring in background
        monitoring_task = asyncio.create_task(start_continuous_monitoring())
        
        return {
            "success": True,
            "message": "Started continuous monitoring of #issues channel",
            "status": "monitoring_started",
            "check_interval": "5 minutes"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@router.post("/stop-monitoring")
async def stop_slack_monitoring():
    """
    Stop continuous monitoring of Slack #issues channel
    """
    global monitoring_task
    
    if not monitoring_task or monitoring_task.done():
        return {
            "success": False,
            "message": "No monitoring task is currently running",
            "status": "not_running"
        }
    
    try:
        monitoring_task.cancel()
        
        return {
            "success": True,
            "message": "Stopped continuous monitoring of #issues channel",
            "status": "monitoring_stopped"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")


@router.get("/monitoring-status")
async def get_monitoring_status():
    """
    Get current status of Slack monitoring
    """
    global monitoring_task
    
    if not monitoring_task:
        status = "not_started"
        message = "Monitoring has not been started"
    elif monitoring_task.done():
        if monitoring_task.cancelled():
            status = "stopped"
            message = "Monitoring was stopped"
        else:
            status = "completed"
            message = "Monitoring task completed (possibly due to error)"
    else:
        status = "running"
        message = "Monitoring is actively running"
    
    return {
        "status": status,
        "message": message,
        "task_exists": monitoring_task is not None,
        "task_done": monitoring_task.done() if monitoring_task else None
    }


@router.get("/channel-info")
async def get_slack_channel_info():
    """
    Get information about the Slack #issues channel connection
    """
    try:
        from app.services.slack_extractor import slack_extractor
        
        # Try to initialize and get channel info
        initialized = await slack_extractor.initialize()
        
        return {
            "success": initialized,
            "channel_name": slack_extractor.issues_channel,
            "channel_id": slack_extractor.issues_channel_id,
            "connected": initialized,
            "message": "Connected to #issues channel" if initialized else "Failed to connect to #issues channel"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get channel information"
        }


@router.post("/test-extraction")
async def test_slack_extraction():
    """
    Test Slack extraction with a small sample (last 2 hours)
    
    This is useful for testing the extraction without processing too much data.
    """
    try:
        result = await extract_and_learn_from_slack(hours_back=2)
        
        return {
            "success": result["success"],
            "test_results": result,
            "message": "Test extraction completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test extraction failed: {str(e)}")
