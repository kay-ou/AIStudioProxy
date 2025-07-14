"""
Tests for API security features.
"""

from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from aistudioproxy.api.security import API_KEY_NAME, get_api_key
from aistudioproxy.utils.config import APIConfig, Config

# Create a test FastAPI app
app = FastAPI()


@app.get("/secure")
async def secure_endpoint(api_key: str = Depends(get_api_key)):
    return {"message": "Access granted", "api_key": api_key}


client = TestClient(app)

# Test data
VALID_KEY = "test-key-123"
INVALID_KEY = "invalid-key-456"


@pytest.fixture
def mock_config():
    """Fixture to mock the application configuration."""
    mock_api_config = APIConfig(keys=[VALID_KEY])
    mock_app_config = Config(api=mock_api_config)
    with patch("aistudioproxy.api.security.get_config", return_value=mock_app_config):
        yield


def test_get_api_key_valid(mock_config):
    """Test successful API key validation."""
    headers = {API_KEY_NAME: f"Bearer {VALID_KEY}"}
    response = client.get("/secure", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Access granted", "api_key": VALID_KEY}


def test_get_api_key_invalid(mock_config):
    """Test validation with an invalid API key."""
    headers = {API_KEY_NAME: f"Bearer {INVALID_KEY}"}
    response = client.get("/secure", headers=headers)
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid API key"}


def test_get_api_key_missing_header(mock_config):
    """Test request with a missing Authorization header."""
    response = client.get("/secure")
    # fastapi.security.api_key.APIKeyHeader handles this and returns 403
    # but the detail message is not what we expect from our custom code.
    # This is fine, as the protection is still active.
    assert response.status_code == 403
    assert response.json() == {"detail": "API key is missing"}


def test_get_api_key_malformed_header_no_bearer(mock_config):
    """Test request with a malformed header (missing 'Bearer')."""
    headers = {API_KEY_NAME: VALID_KEY}
    response = client.get("/secure", headers=headers)
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid authorization header format"}


def test_get_api_key_malformed_header_too_many_parts(mock_config):
    """Test request with a malformed header (too many parts)."""
    headers = {API_KEY_NAME: f"Bearer {VALID_KEY} extra"}
    response = client.get("/secure", headers=headers)
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid authorization header format"}


def test_get_api_key_empty_key_list(mock_config):
    """Test validation when the configured key list is empty."""
    # Override the mock for this specific test
    mock_api_config = APIConfig(keys=[])
    mock_app_config = Config(api=mock_api_config)
    with patch("aistudioproxy.api.security.get_config", return_value=mock_app_config):
        headers = {API_KEY_NAME: f"Bearer {VALID_KEY}"}
        response = client.get("/secure", headers=headers)
        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid API key"}
