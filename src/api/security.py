# -*- coding: utf-8 -*-
"""
API Security and Authentication.

This module provides functions for API key validation and other security-related
utilities.
"""

from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from ..utils.config import get_config

API_KEY_NAME = "Authorization"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validate the API key provided in the request header.

    Args:
        api_key: The API key from the "Authorization" header.

    Returns:
        The validated API key.

    Raises:
        HTTPException: If the API key is missing or invalid.
    """
    if not api_key:
        raise HTTPException(status_code=403, detail="API key is missing")

    config = get_config()
    # The key is expected to be "Bearer <key>"
    parts = api_key.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=403, detail="Invalid authorization header format")
    
    token = parts[1]

    if token not in config.api.keys:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return token