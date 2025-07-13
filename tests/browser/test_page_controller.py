# -*- coding: utf-8 -*-
"""
Tests for the PageController.
"""

from unittest.mock import AsyncMock

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.browser.page_controller import PageController

@pytest.fixture
def mock_page():
    """Fixture for a mock Playwright page."""
    page = AsyncMock()
    page.url = "about:blank"
    return page

@pytest.mark.asyncio
async def test_page_controller_navigate(mock_page):
    """
    Test the navigate_to_aistudio method.
    """
    controller = PageController(mock_page)
    await controller.navigate_to_aistudio()
    
    mock_page.goto.assert_awaited_once_with(
        controller.AISTUDIO_URL,
        wait_until="load",
        timeout=controller.default_timeout
    )

@pytest.mark.asyncio
async def test_page_controller_click(mock_page):
    """
    Test the click method.
    """
    controller = PageController(mock_page)
    selector = "#my-button"
    await controller.click(selector)
    
    mock_page.click.assert_awaited_once_with(selector, timeout=controller.default_timeout)

@pytest.mark.asyncio
async def test_page_controller_fill(mock_page):
    """
    Test the fill method.
    """
    controller = PageController(mock_page)
    selector = "input[name='q']"
    text = "hello world"
    await controller.fill(selector, text)
    
    mock_page.fill.assert_awaited_once_with(selector, text, timeout=controller.default_timeout)

@pytest.mark.asyncio
async def test_page_controller_wait_for_selector(mock_page):
    """
    Test the wait_for_selector method.
    """
    controller = PageController(mock_page)
    selector = ".ready"
    await controller.wait_for_selector(selector)
    
    mock_page.wait_for_selector.assert_awaited_once_with(selector, timeout=controller.default_timeout)

@pytest.mark.asyncio
async def test_page_controller_timeout_exception(mock_page):
    """
    Test that timeout exceptions are correctly raised.
    """
    mock_page.click.side_effect = PlaywrightTimeoutError("Timeout")
    
    controller = PageController(mock_page, default_timeout=100)
    
    with pytest.raises(PlaywrightTimeoutError):
        await controller.click("#timeout-button")
