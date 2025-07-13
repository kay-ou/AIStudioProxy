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


@pytest.mark.asyncio
async def test_switch_model_success(mock_page):
    """Test successful model switching."""
    controller = PageController(mock_page)
    model_name = "Gemini 1.5 Pro"
    
    await controller.switch_model(model_name)
    
    mock_page.click.assert_any_call('button[aria-label="Model"]', timeout=controller.default_timeout)
    mock_page.click.assert_any_call(f'text="{model_name}"', timeout=controller.default_timeout)
    mock_page.wait_for_selector.assert_awaited_once_with(
        f'button[aria-label="Model"]:has-text("{model_name}")',
        state="visible"
    )

@pytest.mark.asyncio
async def test_switch_model_not_found(mock_page, mocker):
    """Test model not found during switching by patching the click method."""
    controller = PageController(mock_page)
    model_name = "Non-existent Model"

    # Patch the click method on the controller instance to bypass its own retry decorator.
    # This allows us to test the retry logic of `switch_model` in isolation.
    click_mock = mocker.patch.object(
        controller, 
        'click', 
        new_callable=AsyncMock
    )
    
    # The switch_model method will retry 3 times. Each time it calls click twice.
    # We want the second click (selecting the model) to fail every time.
    click_mock.side_effect = [
        # 1st attempt
        None,  # Menu click succeeds
        PlaywrightTimeoutError("Timeout on model select"),  # Model click fails
        # 2nd attempt
        None,  # Menu click succeeds
        PlaywrightTimeoutError("Timeout on model select"),  # Model click fails
        # 3rd attempt
        None,  # Menu click succeeds
        PlaywrightTimeoutError("Timeout on model select"),  # Model click fails
    ]

    with pytest.raises(ValueError, match=f"Model '{model_name}' not found."):
        await controller.switch_model(model_name)

    # Verify that click was called 6 times in total (2 calls per attempt * 3 attempts)
    assert click_mock.call_count == 6


@pytest.mark.asyncio
async def test_send_message_success(mock_page):
    """Test successful message sending."""
    controller = PageController(mock_page)
    message = "Hello, AI!"
    
    await controller.send_message(message)
    
    chat_input_selector = 'div[aria-label="Chat input"]'
    send_button_selector = 'button[aria-label="Send message"]'
    
    mock_page.fill.assert_awaited_once_with(chat_input_selector, message, timeout=controller.default_timeout)
    mock_page.click.assert_awaited_once_with(send_button_selector, timeout=controller.default_timeout)

@pytest.mark.asyncio
async def test_send_message_input_not_found(mock_page):
    """Test that a ValueError is raised if the chat input is not found."""
    controller = PageController(mock_page)
    message = "This will fail"
    
    mock_page.fill.side_effect = PlaywrightTimeoutError("Chat input not found")
    
    with pytest.raises(ValueError, match="Chat input not found."):
        await controller.send_message(message)
    
    mock_page.click.assert_not_called()

@pytest.mark.asyncio
async def test_send_message_button_not_found(mock_page):
    """Test that a ValueError is raised if the send button is not found."""
    controller = PageController(mock_page)
    message = "This will also fail"
    
    mock_page.click.side_effect = PlaywrightTimeoutError("Send button not found")
    
    with pytest.raises(ValueError, match="Send button not found."):
        await controller.send_message(message)
        
    chat_input_selector = 'div[aria-label="Chat input"]'
    mock_page.fill.assert_awaited_once_with(chat_input_selector, message, timeout=controller.default_timeout)
