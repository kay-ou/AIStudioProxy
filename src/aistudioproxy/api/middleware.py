"""
Middleware for AIStudioProxy.

This module provides various middleware components for request processing,
logging, error handling, and security.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.config import get_config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request start
        start_time = time.time()
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log request completion
            logger.info(
                "Request completed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=process_time,
            )

            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # Calculate processing time
            process_time = time.time() - start_time

            # Log request error
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                error_type=type(e).__name__,
                error_message=str(e),
                process_time=process_time,
            )

            # Re-raise the exception
            raise


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for security headers and basic protection."""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Process request
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers[
            "Referrer-Policy"
        ] = "strict-origin-when-cross-origin"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Get current time
        now = time.time()

        # Clean old entries
        self.clients = {
            ip: timestamps
            for ip, timestamps in self.clients.items()
            if any(ts > now - self.period for ts in timestamps)
        }

        # Check rate limit
        if client_ip in self.clients:
            # Filter recent timestamps
            recent_calls = [
                ts
                for ts in self.clients[client_ip]
                if ts > now - self.period
            ]

            if len(recent_calls) >= self.calls:
                logger.warning(
                    "Rate limit exceeded",
                    client_ip=client_ip,
                    calls=len(recent_calls),
                    limit=self.calls,
                    period=self.period,
                )
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(self.period)},
                )

            # Update timestamps
            self.clients[client_ip] = recent_calls + [now]
        else:
            # First call from this IP
            self.clients[client_ip] = [now]

        # Process request
        return await call_next(request)


def setup_cors_middleware(app, config):
    """Set up CORS middleware."""
    origins = []
    if config.security.cors_origins != "*":
        origins = [
            origin.strip()
            for origin in config.security.cors_origins.split(",")
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


def setup_middleware(app):
    """Set up all middleware for the FastAPI application."""
    config = get_config()

    # Add custom middleware (order matters - last added is executed first)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Add rate limiting if configured
    if config.security.rate_limit > 0:
        app.add_middleware(
            RateLimitMiddleware,
            calls=config.security.rate_limit,
            period=60
        )

    # Set up CORS
    setup_cors_middleware(app, config)

    logger.info("Middleware setup completed")
