# -*- coding: utf-8 -*-
"""
Tests for the FastAPI application.
"""

from unittest.mock import patch, AsyncMock

import pytest
from fastapi import FastAPI

from src.api.app import lifespan, create_app


@pytest.mark.asyncio
async def test_lifespan_manager():
    """
    Test the application lifespan manager.
    """
    app = FastAPI()
    
    with patch("src.api.app.init_logging") as mock_init_logging, \
         patch("src.api.app.BrowserManager") as mock_browser_manager, \
         patch("src.api.app.RequestHandler") as mock_request_handler, \
         patch("src.api.app.set_dependencies") as mock_set_dependencies:

        mock_browser_manager.return_value.start = AsyncMock()
        mock_browser_manager.return_value.stop = AsyncMock()

        async with lifespan(app):
            mock_init_logging.assert_called_once()
            mock_browser_manager.return_value.start.assert_awaited_once()
            mock_request_handler.assert_called_once()
            mock_set_dependencies.assert_called_once()

        mock_browser_manager.return_value.stop.assert_awaited_once()

@pytest.mark.asyncio
async def test_http_exception_handler(async_client):
    """
    Test the HTTP exception handler.
    """
    response = await async_client.get("/nonexistent-route")
    assert response.status_code == 404
    json_response = response.json()
    assert json_response["error"]["type"] == "server_error"
    assert json_response["error"]["code"] == "404"

@pytest.mark.asyncio
async def test_validation_exception_handler(async_client):
    """
    Test the request validation exception handler.
    """
    response = await async_client.post("/v1/chat/completions", json={"invalid": "payload"})
    assert response.status_code == 422
    json_response = response.json()
    assert json_response["error"]["type"] == "validation_error"
    assert json_response["error"]["code"] == "422"

@pytest.mark.asyncio
async def test_general_exception_handler(async_client):
    """
    Test the general exception handler.
    """
    with patch("src.api.app.setup_middleware", side_effect=Exception("general error")):
        with pytest.raises(Exception, match="general error"):
            create_app()