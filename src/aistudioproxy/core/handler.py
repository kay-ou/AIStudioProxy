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

from fastapi import HTTPException

from ..api.models import ChatCompletionRequest, ChatCompletionResponse
from ..browser.page_controller import PageController
from ..utils.config import get_config
from ..utils.logger import LoggerMixin
from ..utils.response_formatter import (
    _count_tokens,
    format_final_stream_chunk,
    format_initial_stream_chunk,
    format_non_streaming_response,
    format_streaming_chunk,
)


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

        # Concurrency control
        max_concurrency = self.config.performance.max_concurrent_requests
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.logger.info(
            f"Request handler initialized with max concurrency: {max_concurrency}"
        )

        # Request tracking
        self.active_requests = {}
        self._background_tasks = set()

    async def handle_request(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
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

        async with self.semaphore:
            page = None
            try:
                # Track the request
                self.active_requests[request_id] = {
                    "start_time": time.time(),
                    "model": request.model,
                    "status": "processing",
                }

                if not self.browser_manager or not self.browser_manager.is_running():
                    raise HTTPException(
                        status_code=503, detail="Browser is not running"
                    )

                page = await self.browser_manager.get_page()
                if not page:
                    raise HTTPException(
                        status_code=503, detail="No available page in browser"
                    )

                controller = PageController(page)

                # Switch model
                await controller.switch_model(request.model)

                # Send message
                prompt = request.messages[-1].content
                await controller.send_message(prompt)

                # Wait for response
                raw_response = await controller.wait_for_response()

                # Check for errors in response
                error_message = await controller.is_error_response()
                if error_message:
                    raise HTTPException(
                        status_code=500, detail=f"AI Studio Error: {error_message}"
                    )

                # Format response
                response = format_non_streaming_response(
                    raw_response, request.model, prompt
                )
                response.id = request_id  # Ensure consistent request ID

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
                if page and self.browser_manager:
                    await self.browser_manager.release_page(page)
                # Clean up request tracking after some time
                task = asyncio.create_task(self._cleanup_request(request_id))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

    async def handle_stream_request(
        self, request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
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

        async with self.semaphore:
            page = None
            try:
                self.active_requests[request_id] = {
                    "start_time": time.time(),
                    "model": request.model,
                    "status": "streaming",
                }

                if not self.browser_manager or not self.browser_manager.is_running():
                    raise HTTPException(
                        status_code=503, detail="Browser is not running"
                    )

                page = await self.browser_manager.get_page()
                if not page:
                    raise HTTPException(
                        status_code=503, detail="No available page in browser"
                    )

                controller = PageController(page)

                # Switch model and send message
                await controller.switch_model(request.model)
                prompt = request.messages[-1].content
                await controller.send_message(prompt)

                # Yield the initial role chunk
                yield format_initial_stream_chunk(request.model, request_id)

                # Process stream from the page controller
                completion_tokens = 0
                async for chunk in controller.start_streaming_response():
                    completion_tokens += _count_tokens(chunk)
                    yield format_streaming_chunk(chunk, request.model, request_id)

                # Check for errors after streaming
                error_message = await controller.is_error_response()
                if error_message:
                    raise HTTPException(
                        status_code=500, detail=f"AI Studio Error: {error_message}"
                    )

                yield format_final_stream_chunk(request.model, request_id)
                yield "data: [DONE]\n\n"

                # Update request tracking with usage
                prompt_tokens = _count_tokens(prompt)
                self.active_requests[request_id].update(
                    {
                        "status": "completed",
                        "usage": {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": prompt_tokens + completion_tokens,
                        },
                    }
                )
                self.log_method_result("handle_stream_request", request_id=request_id)

            except Exception as e:
                if request_id in self.active_requests:
                    self.active_requests[request_id]["status"] = "failed"
                self.log_error(e, context={"request_id": request_id})
                # Yield a user-friendly error message in SSE format if possible
                if isinstance(e, HTTPException):
                    error_content = {
                        "error": {"message": e.detail, "type": "api_error"}
                    }
                    yield f"data: {json.dumps(error_content)}\n\n"
                yield "data: [DONE]\n\n"
                # Do not re-raise, as the stream is the response
            finally:
                if page and self.browser_manager:
                    await self.browser_manager.release_page(page)
                task = asyncio.create_task(self._cleanup_request(request_id))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

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

    async def _cleanup_request(self, request_id: str):
        """Clean up request tracking after a configured delay."""
        delay = self.config.performance.cleanup_delay
        if delay > 0:
            await asyncio.sleep(delay)
        self.active_requests.pop(request_id, None)
        self.logger.debug(f"Cleaned up request {request_id}")

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
