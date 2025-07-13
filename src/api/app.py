"""
FastAPI application for AIStudioProxy.

This module creates and configures the FastAPI application with all necessary
middleware, routes, and lifecycle management.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .routes import router, set_dependencies
from .middleware import setup_middleware
from .models import ErrorResponse, ErrorDetail
from ..utils.logger import get_logger, init_logging
from ..utils.config import get_config
from .. import __version__

logger = get_logger(__name__)

# Global variables for dependency injection
browser_manager = None
request_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting AIStudioProxy", version=__version__)
    
    try:
        # Initialize logging
        init_logging()
        
        # TODO: Initialize browser manager
        # global browser_manager
        # browser_manager = BrowserManager(get_config().browser)
        # await browser_manager.start()

        # Initialize request handler (without browser for now)
        global request_handler
        request_handler = RequestHandler(browser_manager=None)
        
        # Set dependencies for routes
        set_dependencies(request_handler, None)
        
        logger.info("AIStudioProxy startup completed")
        
        yield
        
    except Exception as e:
        logger.error("Failed to start AIStudioProxy", error=str(e))
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down AIStudioProxy")
        
        try:
            # TODO: Cleanup browser manager
            # if browser_manager:
            #     await browser_manager.stop()
            
            logger.info("AIStudioProxy shutdown completed")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance.
    """
    config = get_config()
    
    # Create FastAPI app
    app = FastAPI(
        title="AIStudioProxy",
        description="Lightweight Google AI Studio proxy with OpenAI API compatibility",
        version=__version__,
        docs_url="/docs" if config.development.debug_browser else None,
        redoc_url="/redoc" if config.development.debug_browser else None,
        lifespan=lifespan,
    )
    
    # Setup middleware
    setup_middleware(app)
    
    # Include routes
    app.include_router(router)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    logger.info("FastAPI application created", debug=config.development.debug_browser)
    
    return app


def setup_exception_handlers(app: FastAPI):
    """Set up custom exception handlers."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.warning(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            url=str(request.url),
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetail(
                    message=exc.detail,
                    type="http_error",
                    code=str(exc.status_code),
                )
            ).dict()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(
            "Validation error",
            errors=exc.errors(),
            url=str(request.url),
        )
        
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorDetail(
                    message="Request validation failed",
                    type="validation_error",
                    code="422",
                )
            ).dict()
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request, exc: StarletteHTTPException):
        """Handle Starlette HTTP exceptions."""
        logger.error(
            "Starlette HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            url=str(request.url),
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetail(
                    message=exc.detail or "Internal server error",
                    type="server_error",
                    code=str(exc.status_code),
                )
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc: Exception):
        """Handle general exceptions."""
        logger.error(
            "Unhandled exception",
            error_type=type(exc).__name__,
            error_message=str(exc),
            url=str(request.url),
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(
                    message="Internal server error",
                    type="internal_error",
                    code="500",
                )
            ).dict()
        )


# Create the application instance
app = create_app()
