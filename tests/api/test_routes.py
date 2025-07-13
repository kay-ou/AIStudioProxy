"""
Tests for API routes.

This module contains unit and integration tests for the FastAPI routes.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from fastapi import status
from src.api.models import ChatCompletionResponse, ChatCompletionChoice, Message, Usage

@pytest.mark.unit
class TestChatCompletions:
    """Test chat completions endpoint."""
    
    def test_chat_completions_success(self, client, sample_chat_request, test_utils):
        """Test successful chat completion request."""
        
        # Mock the response from the request handler
        mock_response = ChatCompletionResponse(
            id="chatcmpl-123",
            object="chat.completion",
            created=1677652288,
            model=sample_chat_request["model"],
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content="Hello there!"),
                    finish_reason="stop",
                )
            ],
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        )
        
        with patch("src.api.routes.request_handler.handle_request", new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = mock_response
            response = client.post("/v1/chat/completions", json=sample_chat_request)
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        test_utils.assert_valid_response_format(response_data)
        assert response_data["model"] == sample_chat_request["model"]
    
    def test_chat_completions_invalid_model(self, client, sample_chat_request):
        """Test chat completion with invalid model."""
        sample_chat_request["model"] = "invalid-model"
        response = client.post("/v1/chat/completions", json=sample_chat_request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert "error" in response_data
        assert "not supported" in response_data["error"]["message"]
    
    def test_chat_completions_empty_messages(self, client, sample_chat_request):
        """Test chat completion with empty messages."""
        sample_chat_request["messages"] = []
        response = client.post("/v1/chat/completions", json=sample_chat_request)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_chat_completions_invalid_temperature(self, client, sample_chat_request):
        """Test chat completion with invalid temperature."""
        sample_chat_request["temperature"] = 3.0  # Should be <= 2.0
        response = client.post("/v1/chat/completions", json=sample_chat_request)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_chat_completions_streaming(self, client, sample_stream_request):
        """Test streaming chat completion."""
        
        async def mock_streamer():
            yield 'data: {"id": "1", "object": "chat.completion.chunk", "model": "gemini-2.5-pro", "choices": [{"delta": {"content": "Hello"}}]}\n\n'
            yield 'data: [DONE]\n\n'

        with patch("src.api.routes.request_handler.handle_stream_request", return_value=mock_streamer()) as mock_handle:
            response = client.post("/v1/chat/completions", json=sample_stream_request)
            
            assert response.status_code == status.HTTP_200_OK
            assert "text/event-stream" in response.headers["content-type"]
            
            content = response.text
            assert "data: " in content
            assert "[DONE]" in content

    def test_chat_completions_with_system_message(self, client, test_utils):
        """Test chat completion with system message."""
        request_data = {
            "model": "gemini-2.5-pro",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ]
        }
        
        mock_response = ChatCompletionResponse(
            id="chatcmpl-124",
            object="chat.completion",
            created=1677652289,
            model=request_data["model"],
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content="Hi! How can I help?"),
                    finish_reason="stop",
                )
            ],
            usage=Usage(prompt_tokens=15, completion_tokens=8, total_tokens=23)
        )

        with patch("src.api.routes.request_handler.handle_request", new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = mock_response
            response = client.post("/v1/chat/completions", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        test_utils.assert_valid_response_format(response_data)


@pytest.mark.unit
class TestModels:
    """Test models endpoint."""
    
    def test_list_models_success(self, client, test_config):
        """Test successful models list request."""
        response = client.get("/v1/models")
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        
        assert response_data["object"] == "list"
        assert "data" in response_data
        assert isinstance(response_data["data"], list)
        assert len(response_data["data"]) == len(test_config.supported_models)
        
        # Check model format
        for model in response_data["data"]:
            assert "id" in model
            assert "object" in model
            assert model["object"] == "model"
            assert "created" in model
            assert "owned_by" in model
            assert model["owned_by"] == "google"


@pytest.mark.unit
class TestHealth:
    """Test health check endpoint."""
    
    def test_health_check_success(self, client):
        """Test successful health check."""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        
        required_fields = ["status", "timestamp", "version", "uptime", "browser_status", "auth_status"]
        for field in required_fields:
            assert field in response_data
        
        assert response_data["status"] in ["healthy", "unhealthy", "unknown"]
        assert isinstance(response_data["uptime"], (int, float))
        assert response_data["uptime"] >= 0
    
    @patch('src.api.routes.browser_manager')
    def test_health_check_with_unhealthy_browser(self, mock_browser_manager, client):
        """Test health check with unhealthy browser."""
        mock_browser_manager.health_check = AsyncMock(return_value=False)
        
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["status"] == "unhealthy"
        assert response_data["browser_status"] == "unhealthy"


@pytest.mark.unit
class TestMetrics:
    """Test metrics endpoint."""
    
    def test_metrics_success(self, client):
        """Test successful metrics request."""
        response = client.get("/metrics")
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        
        required_fields = [
            "requests_total", "requests_success", "requests_error",
            "average_response_time", "active_connections", "browser_sessions", "uptime"
        ]
        for field in required_fields:
            assert field in response_data
            assert isinstance(response_data[field], (int, float))
            assert response_data[field] >= 0


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints."""
    
    def test_full_chat_flow(self, client, sample_chat_request, test_utils):
        """Test complete chat completion flow."""
        # This is an integration test, so it will depend on a running browser instance.
        # For unit tests, we mock the handler. Here we let it run.
        pass

    def test_error_handling_flow(self, client, test_utils):
        """Test error handling across endpoints."""
        # Test invalid model
        invalid_request = {
            "model": "non-existent-model",
            "messages": [{"role": "user", "content": "test"}]
        }
        
        response = client.post("/v1/chat/completions", json=invalid_request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        response_data = response.json()
        test_utils.assert_valid_error_format(response_data)
    
    def test_concurrent_requests(self, client, sample_chat_request):
        """Test handling of concurrent requests."""
        # This is a performance/integration test.
        pass


@pytest.mark.slow
class TestPerformance:
    """Performance tests for API endpoints."""
    
    def test_response_time(self, client, sample_chat_request):
        """Test API response time."""
        # This is a performance test.
        pass
    
    def test_memory_usage(self, client, sample_chat_request):
        """Test memory usage during requests."""
        # This is a performance test.
        pass
