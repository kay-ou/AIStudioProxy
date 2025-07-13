# -*- coding: utf-8 -*-
"""
Tests for the BrowserManager.
"""

from unittest.mock import AsyncMock, MagicMock, patch, create_autospec

import pytest

from aistudioproxy.browser.manager import BrowserManager
from playwright.async_api import Page
from aistudioproxy.utils.config import BrowserConfig

@pytest.fixture
def mock_browser_config():
    """Fixture for browser configuration."""
    return BrowserConfig(headless=True, port=9222)

@pytest.mark.asyncio
@patch("aistudioproxy.browser.manager.async_playwright")
async def test_browser_manager_start_stop(mock_async_playwright, mock_browser_config):
    """
    Test the start and stop methods of the BrowserManager.
    """
    # Mock Playwright and Browser objects
    mock_playwright = AsyncMock()
    mock_browser = AsyncMock()
    mock_browser.is_connected = MagicMock(return_value=True)
    
    # Configure the mock browser to return a properly specced page mock.
    # This prevents RuntimeWarning when PageController calls is_closed() on the page.
    mock_page = create_autospec(Page, instance=True)
    mock_page.is_closed.return_value = False
    mock_browser.new_page.return_value = mock_page
    
    # When async_playwright() is called, it returns a context manager.
    # We mock the start() method to return the playwright object.
    mock_async_playwright.return_value.start = AsyncMock(return_value=mock_playwright)
    
    # Patch the launch_browser method to return our mock browser
    with patch.object(BrowserManager, "launch_browser", new_callable=AsyncMock) as mock_launch:
        mock_launch.return_value = mock_browser
        
        manager = BrowserManager(mock_browser_config)
        
        # Test start
        await manager.start()
        assert manager.playwright is not None
        assert manager.browser is not None
        mock_launch.assert_awaited_once()
        
        # Test stop
        await manager.stop()
        assert manager.browser is None
        assert manager.playwright is None
        mock_browser.close.assert_awaited_once()
        mock_playwright.stop.assert_awaited_once()

@pytest.mark.asyncio
async def test_browser_manager_health_check(mock_browser_config):
    """
    Test the health_check method of the BrowserManager.
    """
    manager = BrowserManager(mock_browser_config)
    
    # Test when browser is not running
    assert not await manager.health_check()
    
    # Mock a healthy browser
    mock_browser = AsyncMock()
    mock_browser.is_connected = MagicMock(return_value=True)
    mock_page = create_autospec(Page, instance=True)
    mock_page.is_closed.return_value = False
    mock_page.close = AsyncMock()
    
    mock_browser.new_page.return_value = mock_page
    manager.browser = mock_browser
    
    assert await manager.health_check()
    mock_browser.new_page.assert_awaited_once()
    mock_page.close.assert_awaited_once()
    
    # Mock an unhealthy browser by making new_page raise an error
    mock_browser.new_page.side_effect = Exception("Browser is dead")
    assert not await manager.health_check()
