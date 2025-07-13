# -*- coding: utf-8 -*-
"""
Tests for the KeepAliveService.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.keep_alive import KeepAliveService


@pytest.fixture
def mock_auth_manager():
    """Fixture for a mock AuthManager."""
    return AsyncMock()


@pytest.fixture
def mock_browser_manager():
    """Fixture for a mock BrowserManager."""
    return MagicMock()


@pytest.mark.asyncio
async def test_keep_alive_service_start_stop(mock_auth_manager, mock_browser_manager):
    """Test that the keep-alive service can be started and stopped."""
    service = KeepAliveService(mock_auth_manager, mock_browser_manager, check_interval=0.1)
    
    await service.start()
    assert service._task is not None
    assert not service._task.done()
    
    await service.stop()
    assert service._task is None


@pytest.mark.asyncio
async def test_keep_alive_service_run_loop_session_active(mock_auth_manager, mock_browser_manager):
    """Test the run loop when the session is active."""
    mock_auth_manager.check_session_status.return_value = True
    
    service = KeepAliveService(mock_auth_manager, mock_browser_manager, check_interval=0.1)
    
    task = asyncio.create_task(service._run())
    
    await asyncio.sleep(0.2)  # Allow the loop to run at least once
    
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    mock_auth_manager.check_session_status.assert_called_once_with(mock_browser_manager)
    mock_auth_manager.login.assert_not_called()


@pytest.mark.asyncio
async def test_keep_alive_service_run_loop_session_inactive(mock_auth_manager, mock_browser_manager):
    """Test the run loop when the session is inactive and re-login is successful."""
    mock_auth_manager.check_session_status.return_value = False
    mock_auth_manager.login.return_value = True
    
    service = KeepAliveService(mock_auth_manager, mock_browser_manager, check_interval=0.1)
    
    task = asyncio.create_task(service._run())
    
    await asyncio.sleep(0.2)
    
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    mock_auth_manager.check_session_status.assert_called_once_with(mock_browser_manager)
    mock_auth_manager.login.assert_awaited_once_with(mock_browser_manager)


@pytest.mark.asyncio
async def test_keep_alive_service_relogin_fails(mock_auth_manager, mock_browser_manager):
    """Test the run loop when re-login fails."""
    mock_auth_manager.check_session_status.return_value = False
    mock_auth_manager.login.side_effect = Exception("Login failed")
    
    service = KeepAliveService(mock_auth_manager, mock_browser_manager, check_interval=0.1)
    
    task = asyncio.create_task(service._run())
    
    await asyncio.sleep(0.2)
    
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    mock_auth_manager.check_session_status.assert_called_once_with(mock_browser_manager)
    mock_auth_manager.login.assert_awaited_once_with(mock_browser_manager)