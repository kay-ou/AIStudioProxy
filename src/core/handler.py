"""
Request handler for AIStudioProxy.

This module provides the main request handling logic for processing
chat completion requests and interfacing with the browser automation layer.
"""

import asyncio
import json
import time
import uuid
from typing import AsyncGenerator

from ..api.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    Message,
    Usage,
    MessageRole,
)
from ..utils.logger import LoggerMixin
from ..utils.config import get_config


class RequestHandler(LoggerMixin):
    """Main request handler for chat completion requests."""
    
    def __init__(self, browser_manager=None):
        """
        Initialize the request handler.
        
        Args:
            browser_manager: Browser manager instance for automation
        """
        self.browser_manager = browser_manager
        self.config = get_config()
        
        # Request tracking
        self.active_requests = {}
        
        self.logger.info("Request handler initialized")
    
    async def handle_request(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """
        Handle a non-streaming chat completion request.
        
        Args:
            request: The chat completion request
            
        Returns:
            Chat completion response
            
        Raises:
            HTTPException: If the request cannot be processed
        """
        request_id = str(uuid.uuid4())
        
        self.log_method_call(
            "handle_request",
            request_id=request_id,
            model=request.model,
            message_count=len(request.messages),
        )
        
        try:
            # Track the request
            self.active_requests[request_id] = {
                "start_time": time.time(),
                "model": request.model,
                "status": "processing"
            }
            
            # For now, return a placeholder response until browser automation is implemented
            # TODO: Replace with actual browser automation logic
            response = await self._create_placeholder_response(request, request_id)
            
            # Update request tracking
            self.active_requests[request_id]["status"] = "completed"
            
            self.log_method_result(
                "handle_request",
                request_id=request_id,
                response_id=response.id,
            )
            
            return response
            
        except Exception as e:
            # Update request tracking
            if request_id in self.active_requests:
                self.active_requests[request_id]["status"] = "failed"
            
            self.log_error(e, context={"request_id": request_id})
            raise
        finally:
            # Clean up request tracking after some time
            asyncio.create_task(self._cleanup_request(request_id, delay=300))
    
    async def handle_stream_request(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        """
        Handle a streaming chat completion request.
        
        Args:
            request: The chat completion request
            
        Yields:
            Server-sent events formatted response chunks
        """
        request_id = str(uuid.uuid4())
        
        self.log_method_call(
            "handle_stream_request",
            request_id=request_id,
            model=request.model,
            message_count=len(request.messages),
        )
        
        try:
            # Track the request
            self.active_requests[request_id] = {
                "start_time": time.time(),
                "model": request.model,
                "status": "streaming"
            }
            
            # For now, yield a placeholder stream until browser automation is implemented
            # TODO: Replace with actual browser automation logic
            async for chunk in self._create_placeholder_stream(request, request_id):
                yield chunk
            
            # Update request tracking
            self.active_requests[request_id]["status"] = "completed"
            
            self.log_method_result(
                "handle_stream_request",
                request_id=request_id,
            )
            
        except Exception as e:
            # Update request tracking
            if request_id in self.active_requests:
                self.active_requests[request_id]["status"] = "failed"
            
            self.log_error(e, context={"request_id": request_id})
            raise
        finally:
            # Clean up request tracking after some time
            asyncio.create_task(self._cleanup_request(request_id, delay=300))
    
    async def health_check(self) -> bool:
        """
        Check if the request handler is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Check if browser manager is available and healthy
            if self.browser_manager:
                return await self.browser_manager.health_check()
            
            # If no browser manager, we're in development mode
            return True
            
        except Exception as e:
            self.log_error(e, context={"method": "health_check"})
            return False
    
    async def _create_placeholder_response(
        self, 
        request: ChatCompletionRequest, 
        request_id: str
    ) -> ChatCompletionResponse:
        """
        Create a placeholder response for development/testing.
        
        This method will be replaced with actual browser automation logic.
        """
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        # Create a simple response
        content = (
            "I'm a placeholder response from AIStudioProxy. "
            "The actual browser automation is not yet implemented. "
            f"You asked: {request.messages[-1].content}"
        )
        
        # Calculate token usage (rough estimation)
        prompt_tokens = sum(len(msg.content.split()) for msg in request.messages)
        completion_tokens = len(content.split())
        
        return ChatCompletionResponse(
            id=request_id,
            created=int(time.time()),
            model=request.model,
            choices=[
                Choice(
                    index=0,
                    message=Message(
                        role=MessageRole.ASSISTANT,
                        content=content
                    ),
                    finish_reason="stop"
                )
            ],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
        )
    
    async def _create_placeholder_stream(
        self, 
        request: ChatCompletionRequest, 
        request_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Create a placeholder streaming response for development/testing.
        
        This method will be replaced with actual browser automation logic.
        """
        # Simulate streaming response
        content_parts = [
            "I'm ", "a ", "placeholder ", "streaming ", "response ", 
            "from ", "AIStudioProxy. ", "The ", "actual ", "browser ", 
            "automation ", "is ", "not ", "yet ", "implemented."
        ]
        
        # First chunk with role
        first_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant"},
                "finish_reason": None,
            }]
        }
        yield f"data: {json.dumps(first_chunk)}\n\n"
        await asyncio.sleep(0.05)

        # Content chunks
        for part in content_parts:
            chunk_data = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": part},
                    "finish_reason": None,
                }]
            }

            yield f"data: {json.dumps(chunk_data)}\n\n"
            await asyncio.sleep(0.05)  # Simulate typing delay
        
        # Final chunk
        final_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }]
        }
        
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    async def _cleanup_request(self, request_id: str, delay: int = 300):
        """Clean up request tracking after a delay."""
        await asyncio.sleep(delay)
        self.active_requests.pop(request_id, None)
    
    def get_active_requests_count(self) -> int:
        """Get the number of currently active requests."""
        return len(self.active_requests)
    
    def get_request_stats(self) -> dict:
        """Get statistics about request processing."""
        now = time.time()
        active_count = 0
        avg_duration = 0
        
        if self.active_requests:
            durations = []
            for req_data in self.active_requests.values():
                if req_data["status"] == "processing":
                    active_count += 1
                durations.append(now - req_data["start_time"])
            
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        return {
            "active_requests": active_count,
            "total_tracked": len(self.active_requests),
            "average_duration": avg_duration,
        }
