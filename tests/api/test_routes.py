"""
Tests for API routes.

This module contains unit and integration tests for the FastAPI routes.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from fastapi import status


@pytest.mark.unit
class TestChatCompletions:
    """Test chat completions endpoint."""
    
    def test_chat_completions_success(self, client, sample_chat_request, test_utils):
        """Test successful chat completion request."""
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
        response = client.post("/v1/chat/completions", json=sample_stream_request)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        
        # Check that response contains streaming data
        content = response.content.decode()
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
        
        assert response_data["status"] in ["healthy", "unhealthy"]
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
        # First, check available models
        models_response = client.get("/v1/models")
        assert models_response.status_code == status.HTTP_200_OK
        models_data = models_response.json()
        available_models = [model["id"] for model in models_data["data"]]
        
        # Use an available model
        sample_chat_request["model"] = available_models[0]
        
        # Make chat completion request
        chat_response = client.post("/v1/chat/completions", json=sample_chat_request)
        assert chat_response.status_code == status.HTTP_200_OK
        
        response_data = chat_response.json()
        test_utils.assert_valid_response_format(response_data)
        
        # Check that the response model matches request
        assert response_data["model"] == sample_chat_request["model"]
    
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
        import concurrent.futures
        import threading
        
        def make_request():
            return client.post("/v1/chat/completions", json=sample_chat_request)
        
        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [future.result() for future in futures]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK


@pytest.mark.slow
class TestPerformance:
    """Performance tests for API endpoints."""
    
    def test_response_time(self, client, sample_chat_request):
        """Test API response time."""
        import time
        
        start_time = time.time()
        response = client.post("/v1/chat/completions", json=sample_chat_request)
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        
        response_time = end_time - start_time
        assert response_time < 5.0  # Should respond within 5 seconds
    
    def test_memory_usage(self, client, sample_chat_request):
        """Test memory usage during requests."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make multiple requests
        for _ in range(10):
            response = client.post("/v1/chat/completions", json=sample_chat_request)
            assert response.status_code == status.HTTP_200_OK
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024
