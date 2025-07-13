# -*- coding: utf-8 -*-
"""
Tests for the retry utility.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.utils.retry import async_retry

@pytest.mark.asyncio
async def test_async_retry_success_on_first_attempt():
    """
    Test that the decorator returns the result on the first attempt if no exception is raised.
    """
    mock_func = AsyncMock(return_value="success")

    decorated_func = async_retry(attempts=3)(mock_func)
    result = await decorated_func()

    assert result == "success"
    mock_func.assert_awaited_once()

@pytest.mark.asyncio
async def test_async_retry_success_after_failures():
    """
    Test that the decorator succeeds after a few failed attempts.
    """
    mock_func = AsyncMock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])

    decorated_func = async_retry(attempts=3, initial_delay=0.01)(mock_func)
    result = await decorated_func()

    assert result == "success"
    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_async_retry_fails_after_max_attempts():
    """
    Test that the decorator raises the last exception after all attempts fail.
    """
    mock_func = AsyncMock(side_effect=ValueError("persistent failure"))

    decorated_func = async_retry(attempts=3, initial_delay=0.01)(mock_func)

    with pytest.raises(ValueError, match="persistent failure"):
        await decorated_func()

    assert mock_func.call_count == 3

@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_async_retry_uses_exponential_backoff(mock_sleep):
    """
    Test that the decorator uses exponential backoff for delays.
    """
    mock_func = AsyncMock(side_effect=[ValueError, ValueError, "success"])
    
    decorated_func = async_retry(attempts=3, initial_delay=0.1, factor=2)(mock_func)
    await decorated_func()

    assert mock_sleep.call_count == 2
    # Check if the delay increases. Jitter makes exact checks difficult, so we check ranges.
    assert 0.09 <= mock_sleep.call_args_list[0][0][0] <= 0.11  # initial_delay
    assert 0.18 <= mock_sleep.call_args_list[1][0][0] <= 0.22  # initial_delay * factor
