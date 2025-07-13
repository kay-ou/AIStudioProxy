"""
Pytest configuration and fixtures for AIStudioProxy tests.

This module provides common fixtures and configuration for all tests.
"""

import asyncio
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.api.app import create_app
from src.utils.config import Config
from src.utils.logger import setup_logger


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration."""
    config = Config()
    
    # Override settings for testing
    config.server.host = "127.0.0.1"
    config.server.port = 8888
    config.server.debug = True
    config.browser.headless = True
    config.browser.timeout = 5000
    config.log.level = "DEBUG"
    config.development.mock_responses = True
    config.api.keys = ["test-key"]
    
    return config


@pytest.fixture
def mock_browser_manager():
    """Create a mock browser manager."""
    mock = AsyncMock()
    mock.is_running.return_value = True
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    
    # Mock the page pool methods
    mock_page = AsyncMock()
    mock.get_page = AsyncMock(return_value=mock_page)
    mock.release_page = AsyncMock()
    
    mock.page = mock_page # for backward compatibility if any test uses it directly
    return mock


@pytest.fixture
def mock_request_handler():
    """Create a mock request handler."""
    mock = AsyncMock()
    mock.handle_request = AsyncMock()
    mock.handle_stream_request = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_auth_manager():
    """Create a mock auth manager."""
    mock = AsyncMock()
    mock.login = AsyncMock(return_value=True)
    mock.health_check = AsyncMock(return_value=True)
    mock.status = Mock()
    mock.status.value = "authenticated"
    return mock

@pytest.fixture
def app_with_mocks(test_config, mock_browser_manager, mock_request_handler, mock_auth_manager):
    """Create FastAPI app with mocked dependencies."""
    # Patch get_config where it's imported to ensure all parts of the app
    # use the test configuration. This is crucial for dependencies like API key
    # security that resolve on module import.
    with patch('src.api.app.get_config', return_value=test_config), \
         patch('src.api.routes.get_config', return_value=test_config), \
         patch('src.api.security.get_config', return_value=test_config):
        
        app = create_app()
        
        # Set mock dependencies for handlers
        from src.api.routes import set_dependencies
        set_dependencies(
            handler=mock_request_handler,
            browser=mock_browser_manager,
            auth=mock_auth_manager,
        )
        
        yield app


@pytest.fixture
def client(app_with_mocks) -> TestClient:
    """Create a test client."""
    return TestClient(app_with_mocks)


@pytest.fixture
async def async_client(app_with_mocks) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(app=app_with_mocks, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_chat_request():
    """Create a sample chat completion request."""
    return {
        "model": "gemini-2.5-pro",
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "temperature": 0.7,
        "max_tokens": 100,
        "stream": False
    }


@pytest.fixture
def sample_stream_request():
    """Create a sample streaming chat completion request."""
    return {
        "model": "gemini-2.5-pro",
        "messages": [
            {"role": "user", "content": "Tell me a story"}
        ],
        "temperature": 0.8,
        "stream": True
    }


@pytest.fixture
def sample_messages():
    """Create sample message list."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "What about Germany?"}
    ]


# Pytest markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "browser: mark test as requiring browser automation"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as requiring authentication"
    )


# Test utilities
class TestUtils:
    """Utility class for common test operations."""
    
    @staticmethod
    def assert_valid_response_format(response_data: dict):
        """Assert that response follows OpenAI format."""
        assert "id" in response_data
        assert "object" in response_data
        assert "created" in response_data
        assert "model" in response_data
        assert "choices" in response_data
        assert isinstance(response_data["choices"], list)
        assert len(response_data["choices"]) > 0
    
    @staticmethod
    def assert_valid_error_format(response_data: dict):
        """Assert that error response follows OpenAI format."""
        assert "error" in response_data
        error = response_data["error"]
        assert "message" in error
        assert "type" in error
    
    @staticmethod
    def assert_valid_stream_chunk(chunk_data: dict):
        """Assert that stream chunk follows OpenAI format."""
        assert "id" in chunk_data
        assert "object" in chunk_data
        assert chunk_data["object"] == "chat.completion.chunk"
        assert "created" in chunk_data
        assert "model" in chunk_data
        assert "choices" in chunk_data


@pytest.fixture
def test_utils():
    """Provide test utilities."""
    return TestUtils


# Async test helpers
@pytest.fixture
async def setup_logger_for_tests():
    """Set up logger for tests."""
    logger = setup_logger()
    yield logger


# Mock data fixtures
@pytest.fixture
def mock_completion_response():
    """Mock completion response data."""
    return {
        "id": "test-completion-123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gemini-2.5-pro",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! I'm doing well, thank you for asking."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 12,
            "total_tokens": 22
        }
    }


@pytest.fixture
def mock_models_response():
    """Mock models list response data."""
    return {
        "object": "list",
        "data": [
            {
                "id": "gemini-2.5-pro",
                "object": "model",
                "created": 1234567890,
                "owned_by": "google"
            },
            {
                "id": "gemini-2.5-flash",
                "object": "model",
                "created": 1234567890,
                "owned_by": "google"
            }
        ]
    }
