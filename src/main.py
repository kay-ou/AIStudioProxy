"""
Main entry point for AIStudioProxy.

This module provides the main function to start the AIStudioProxy server
with proper configuration and error handling.
"""

import sys
import signal
import asyncio
from typing import Optional

import uvicorn

from .api.app import app
from .utils.config import get_config, load_config_from_file
from .utils.logger import init_logging, get_logger

logger = get_logger(__name__)


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """
    Main entry point for the AIStudioProxy server.
    
    This function handles configuration loading, logging setup, and server startup.
    """
    try:
        # Parse command line arguments
        import argparse
        parser = argparse.ArgumentParser(description="AIStudioProxy Server")
        parser.add_argument(
            "--config",
            type=str,
            help="Path to configuration file (YAML)"
        )
        parser.add_argument(
            "--host",
            type=str,
            help="Host to bind to"
        )
        parser.add_argument(
            "--port",
            type=int,
            help="Port to bind to"
        )
        parser.add_argument(
            "--workers",
            type=int,
            help="Number of worker processes"
        )
        parser.add_argument(
            "--reload",
            action="store_true",
            help="Enable auto-reload for development"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug mode"
        )
        
        args = parser.parse_args()
        
        # Load configuration
        if args.config:
            config = load_config_from_file(args.config)
            logger.info(f"Loaded configuration from {args.config}")
        else:
            config = get_config()
        
        # Override config with command line arguments
        if args.host:
            config.server.host = args.host
        if args.port:
            config.server.port = args.port
        if args.workers:
            config.server.workers = args.workers
        if args.reload:
            config.development.reload = args.reload
        if args.debug:
            config.server.debug = args.debug
        
        # Initialize logging
        init_logging()
        
        # Setup signal handlers
        setup_signal_handlers()
        
        # Log startup information
        logger.info(
            "Starting AIStudioProxy",
            host=config.server.host,
            port=config.server.port,
            workers=config.server.workers,
            debug=config.server.debug,
            reload=config.development.reload,
        )
        
        # Start the server
        uvicorn.run(
            "src.api.app:app",
            host=config.server.host,
            port=config.server.port,
            workers=config.server.workers if not config.development.reload else 1,
            reload=config.development.reload,
            log_config=None,  # We handle logging ourselves
            access_log=False,  # We handle access logging in middleware
        )
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(
            "Failed to start AIStudioProxy",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
