"""
FastAPI application for AIStudioProxy.

This module creates and aiconfigures the FastAPI application with all necessary
middleware, routes, and lifecycle management.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import __version__
from ..auth.manager import AuthManager
from ..browser.manager import BrowserManager
from ..core.handler import RequestHandler
from ..services.keep_alive import KeepAliveService
from ..utils.config import get_config
from ..utils.logger import get_logger, init_logging
from .middleware import setup_middleware
from .models import ErrorDetail, ErrorResponse
from .routes import router, set_dependencies

logger = get_logger(__name__)

# It's better to use app.state for sharing objects across the application
# instead of global variables.


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application,
    including initializing and cleaning up the browser, authentication,
    and keep-alive services.
    """
    # Startup
    logger.info("Starting AIStudioProxy", version=__version__)

    try:
        # Initialize logging
        init_logging()

        # Initialize managers and services
        config = get_config()
        browser_manager = BrowserManager(config.browser)
        auth_manager = AuthManager(config.auth)

        # Store managers in app.state for access in other parts of the app
        app.state.browser_manager = browser_manager
        app.state.auth_manager = auth_manager

        # Start browser
        await browser_manager.start()

        # Perform initial login
        if config.auth.auto_login:
            logger.info("Performing initial login...")
            login_success = await auth_manager.login(browser_manager)
            if not login_success:
                logger.error(
                    "Initial login failed. "
                    "The proxy may not function correctly."
                )
                # Depending on requirements, you might want to exit here.
                # For now, we'll log an error and continue.

        # Start keep-alive service
        keep_alive_service = KeepAliveService(auth_manager, browser_manager)
        app.state.keep_alive_service = keep_alive_service
        await keep_alive_service.start()

        # Initialize request handler
        request_handler = RequestHandler(browser_manager=browser_manager)

        # Set dependencies for routes
        set_dependencies(
            handler=request_handler,
            browser=browser_manager,
            auth=auth_manager,
        )

        logger.info("AIStudioProxy startup completed")

        yield

    except Exception as e:
        logger.error(
            "Failed to start AIStudioProxy", error=str(e), exc_info=True
        )
        # Ensure cleanup is attempted even if startup fails
        if hasattr(app.state, "browser_manager") and app.state.browser_manager:
            await app.state.browser_manager.stop()
        raise

    finally:
        # Shutdown
        logger.info("Shutting down AIStudioProxy")

        try:
            # Stop keep-alive service
            if (
                hasattr(app.state, "keep_alive_service")
                and app.state.keep_alive_service
            ):
                await app.state.keep_alive_service.stop()

            # Cleanup browser manager
            if (
                hasattr(app.state, "browser_manager")
                and app.state.browser_manager
            ):
                await app.state.browser_manager.stop()

            logger.info("AIStudioProxy shutdown completed")

        except Exception as e:
            logger.error(
                "Error during shutdown", error=str(e), exc_info=True
            )


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
        description="A lightweight Google AI Studio proxy",
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

    logger.info(
        "FastAPI application created",
        debug=config.development.debug_browser
    )

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
                    param=None,
                    code=str(exc.status_code),
                )
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request, exc: RequestValidationError
    ):
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
                    param=None,
                    code="422",
                )
            ).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(
        request, exc: StarletteHTTPException
    ):
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
                    param=None,
                    code=str(exc.status_code),
                )
            ).model_dump(),
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
                    param=None,
                    code="500",
                )
            ).model_dump(),
        )


# Create the application instance
app = create_app()
