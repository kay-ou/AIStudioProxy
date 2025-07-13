"""
API routes for AIStudioProxy.

This module defines the FastAPI routes for OpenAI-compatible endpoints.
"""

import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse

from .models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelListResponse,
    Model,
    HealthResponse,
    MetricsResponse,
)
from ..utils.logger import get_logger
from ..utils.config import get_config
from .. import __version__
from ..core.handler import RequestHandler
from ..browser.manager import BrowserManager
from ..auth.manager import AuthManager
from .security import get_api_key

logger = get_logger(__name__)
router = APIRouter()

# Global variables will be replaced by dependencies injected via app state
request_handler: Optional[RequestHandler] = None
browser_manager: Optional[BrowserManager] = None
auth_manager: Optional[AuthManager] = None
start_time = time.time()

# Metrics tracking
metrics = {
    "requests_total": 0,
    "requests_success": 0,
    "requests_error": 0,
    "response_times": [],
}


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    http_request: Request,
    api_key: str = Depends(get_api_key)
):
    """
    Create a chat completion.
    
    This endpoint is compatible with OpenAI's chat completions API.
    """
    request_id = getattr(http_request.state, 'request_id', 'unknown')
    start_time_req = time.time()
    
    try:
        # Update metrics
        metrics["requests_total"] += 1
        
        # Validate model
        config = get_config()
        if request.model not in config.supported_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{request.model}' is not supported. "
                       f"Supported models: {', '.join(config.supported_models)}"
            )
        
        logger.info(
            "Processing chat completion request",
            request_id=request_id,
            model=request.model,
            message_count=len(request.messages),
            stream=request.stream,
        )
        
        # Check if request handler is available
        if request_handler is None:
            raise HTTPException(
                status_code=503,
                detail="Service not ready - request handler not initialized"
            )

        # Process the request through the handler
        if request.stream:
            return StreamingResponse(
                request_handler.handle_stream_request(request),
                media_type="text/event-stream"
            )
        else:
            response = await request_handler.handle_request(request)

            # Update metrics
            process_time = time.time() - start_time_req
            metrics["requests_success"] += 1
            metrics["response_times"].append(process_time)

            return response
    
    except HTTPException:
        metrics["requests_error"] += 1
        raise
    except Exception as e:
        metrics["requests_error"] += 1
        logger.error(
            "Error processing chat completion",
            request_id=request_id,
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    """List available models."""
    config = get_config()
    
    models = [
        Model(
            id=model_id,
            created=int(time.time()),
            owned_by="google"
        )
        for model_id in config.supported_models
    ]
    
    logger.debug("Listed available models", model_count=len(models))
    
    return ModelListResponse(data=models)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    uptime = time.time() - start_time
    
    # Check browser status
    browser_status = "unknown"
    if browser_manager:
        try:
            browser_healthy = await browser_manager.health_check()
            browser_status = "healthy" if browser_healthy else "unhealthy"
        except Exception as e:
            browser_status = f"error: {str(e)}"
            logger.warning("Browser health check failed", error=str(e))
    
    # Check auth status
    auth_status = "unknown"
    if auth_manager:
        try:
            auth_healthy = await auth_manager.health_check()
            auth_status = auth_manager.status.value if auth_manager.status else "unknown"
            if not auth_healthy:
                auth_status = f"unhealthy ({auth_status})"
        except Exception as e:
            auth_status = f"error: {str(e)}"
            logger.warning("Auth health check failed", error=str(e))

    # Determine overall status
    is_healthy = browser_status == "healthy" and "unhealthy" not in auth_status
    overall_status = "healthy" if is_healthy else "unhealthy"
    
    response = HealthResponse(
        status=overall_status,
        timestamp=int(time.time()),
        version=__version__,
        uptime=uptime,
        browser_status=browser_status,
        auth_status=auth_status,
    )
    
    logger.debug("Health check completed", status=overall_status)
    
    return response


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get service metrics."""
    uptime = time.time() - start_time
    
    # Calculate average response time
    avg_response_time = 0.0
    if metrics["response_times"]:
        avg_response_time = sum(metrics["response_times"]) / len(metrics["response_times"])
        # Keep only recent response times (last 1000)
        if len(metrics["response_times"]) > 1000:
            metrics["response_times"] = metrics["response_times"][-1000:]
    
    # Get browser sessions count
    browser_sessions = 1 if browser_manager and browser_manager.is_running() else 0
    
    response = MetricsResponse(
        requests_total=metrics["requests_total"],
        requests_success=metrics["requests_success"],
        requests_error=metrics["requests_error"],
        average_response_time=avg_response_time,
        active_connections=0,  # TODO: Implement actual connection tracking
        browser_sessions=browser_sessions,
        uptime=uptime,
    )
    
    logger.debug("Metrics retrieved", **response.model_dump())
    
    return response


def set_dependencies(
    handler: RequestHandler,
    browser: BrowserManager,
    auth: AuthManager,
):
    """Set global dependencies for routes."""
    global request_handler, browser_manager, auth_manager
    request_handler = handler
    browser_manager = browser
    auth_manager = auth
