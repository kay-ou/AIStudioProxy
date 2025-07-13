# -*- coding: utf-8 -*-
"""
Tests for API routes.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status

from aistudioproxy.api.models import HealthResponse, ModelListResponse

@pytest.mark.asyncio
async def test_health_check(async_client):
    """Test the health check endpoint."""
    with patch("aistudioproxy.api.routes.browser_manager", new_callable=AsyncMock) as mock_browser_manager:
        mock_browser_manager.health_check.return_value = True
        
        response = await async_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        
        health_data = HealthResponse(**response.json())
        assert health_data.status == "healthy"
        assert health_data.browser_status == "healthy"

@pytest.mark.asyncio
async def test_list_models(async_client, test_config):
    """Test the list models endpoint."""
    response = await async_client.get("/v1/models")
    assert response.status_code == status.HTTP_200_OK
    
    model_list = ModelListResponse(**response.json())
    assert model_list.object == "list"
    assert len(model_list.data) == len(test_config.supported_models)
    assert model_list.data[0].id == test_config.supported_models[0]


@pytest.mark.asyncio
async def test_chat_completions_unsupported_model(async_client):
    """
    Test that an error is returned for an unsupported model.
    """
    response = await async_client.post(
        "/v1/chat/completions",
        json={"model": "unsupported-model", "messages": [{"role": "user", "content": "hello"}]},
        headers={"Authorization": "Bearer test-key"}
    )
    assert response.status_code == 400
    assert "is not supported" in response.text

@pytest.mark.asyncio
async def test_chat_completions_no_handler(async_client):
    """
    Test that a 503 error is returned when the request handler is not available.
    """
    with patch("aistudioproxy.api.routes.request_handler", None):
        response = await async_client.post(
            "/v1/chat/completions",
            json={"model": "gemini-2.5-pro", "messages": [{"role": "user", "content": "hello"}]},
            headers={"Authorization": "Bearer test-key"}
        )
        assert response.status_code == 503

@pytest.mark.asyncio
async def test_chat_completions_streaming(async_client):
    """
    Test the streaming chat completion endpoint.
    """
    async def mock_stream_response(request):
        yield "data: hello\n\n"
        yield "data: world\n\n"

    with patch("aistudioproxy.api.routes.request_handler.handle_stream_request", new=mock_stream_response):
        response = await async_client.post(
            "/v1/chat/completions",
            json={"model": "gemini-2.5-pro", "messages": [{"role": "user", "content": "hello"}], "stream": True},
            headers={"Authorization": "Bearer test-key"}
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        
        content = await response.aread()
        assert b"data: hello" in content
        assert b"data: world" in content


@pytest.mark.asyncio
async def test_health_check_no_browser_manager(async_client):
    """
    Test the health check endpoint when the browser manager is not available.
    """
    with patch("aistudioproxy.api.routes.browser_manager", None):
        response = await async_client.get("/health")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["browser_status"] == "unknown"

@pytest.mark.asyncio
async def test_health_check_browser_error(async_client):
    """
    Test the health check endpoint when the browser health check fails.
    """
    with patch("aistudioproxy.api.routes.browser_manager.health_check", side_effect=Exception("health check failed")):
        response = await async_client.get("/health")
        assert response.status_code == 200
        json_response = response.json()
        assert "error: health check failed" in json_response["browser_status"]

@pytest.mark.asyncio
async def test_get_metrics(async_client):
    """
    Test the metrics endpoint.
    """
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    json_response = response.json()
    assert "requests_total" in json_response
    assert "uptime" in json_response
