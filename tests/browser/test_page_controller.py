# -*- coding: utf-8 -*-
"""
Tests for the PageController.
"""

import asyncio
from unittest.mock import AsyncMock, create_autospec

import pytest
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from src.browser.page_controller import PageController

@pytest.fixture
def mock_page():
    """
    Provides a precisely configured mock for a Playwright Page using create_autospec.
    This ensures that the mock's API matches the real Page, preventing
    errors from incorrect mock setups (e.g., awaiting a sync method like is_closed).
    """
    page = create_autospec(Page, instance=True)
    page.url = "about:blank"
    
    # is_closed is a synchronous method.
    page.is_closed.return_value = False
    
    # Async methods need to be awaitable.
    page.goto = AsyncMock()
    page.close = AsyncMock()
    page.content = AsyncMock(return_value="<html></html>")
    page.title = AsyncMock(return_value="Test Page")
    
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


@pytest.mark.asyncio
async def test_wait_for_response_success(mock_page):
    """Test successful response waiting and text extraction."""
    controller = PageController(mock_page)
    expected_response = "This is the AI response."

    # Mock the element and its inner_text method
    mock_response_element = AsyncMock()
    mock_response_element.inner_text.return_value = expected_response
    
    # When query_selector is called for the response block, return our mock element
    mock_page.query_selector.return_value = mock_response_element

    response = await controller.wait_for_response()

    stop_generating_selector = 'button[aria-label="Stop generating"]'
    response_selector = ".response-block:last-child"

    # Check that we waited for the stop button to appear and then disappear
    mock_page.wait_for_selector.assert_any_call(stop_generating_selector, state="visible", timeout=controller.default_timeout)
    mock_page.wait_for_selector.assert_any_call(stop_generating_selector, state="hidden", timeout=controller.default_timeout)
    
    # Check that we queried for the response block
    mock_page.query_selector.assert_awaited_once_with(response_selector)
    
    # Check that we got the text from the element
    mock_response_element.inner_text.assert_awaited_once()
    
    assert response == expected_response

@pytest.mark.asyncio
async def test_wait_for_response_timeout_on_start(mock_page):
    """Test timeout waiting for response generation to start."""
    controller = PageController(mock_page)
    
    # Make the first wait_for_selector call (waiting for 'visible') time out
    mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError("Timeout waiting for start")

    with pytest.raises(PlaywrightTimeoutError):
        await controller.wait_for_response()

@pytest.mark.asyncio
async def test_wait_for_response_timeout_on_end(mock_page):
    """Test timeout waiting for response generation to complete."""
    controller = PageController(mock_page)

    # First call for 'visible' succeeds, subsequent calls for 'hidden' fail.
    mock_page.wait_for_selector.side_effect = [
        None,
        PlaywrightTimeoutError("Timeout waiting for end"),
        PlaywrightTimeoutError("Timeout waiting for end"),
        PlaywrightTimeoutError("Timeout waiting for end"),
    ]

    with pytest.raises(PlaywrightTimeoutError):
        await controller.wait_for_response()

@pytest.mark.asyncio
async def test_wait_for_response_no_element_found(mock_page):
    """Test that a ValueError is raised if the response element is not found."""
    controller = PageController(mock_page)
    
    # Make query_selector return None
    mock_page.query_selector.return_value = None

    with pytest.raises(ValueError, match="Failed to extract response text."):
        await controller.wait_for_response()


@pytest.mark.asyncio
async def test_start_streaming_response(mock_page):
    """Test the start_streaming_response async generator."""
    controller = PageController(mock_page)
    
    # Store the exposed functions so we can call them
    exposed_functions = {}
    async def mock_expose(name, func):
        exposed_functions[name] = func
    
    mock_page.expose_function.side_effect = mock_expose
    
    # Mock the page interactions
    mock_page.wait_for_selector.return_value = AsyncMock()
    mock_page.evaluate.return_value = AsyncMock()
    
    # --- Test Execution ---
    chunks = []
    async def consume_stream():
        nonlocal chunks
        async for chunk in controller.start_streaming_response():
            chunks.append(chunk)

    # Run the consumer and the driver concurrently
    consumer_task = asyncio.create_task(consume_stream())

    # Give the consumer a moment to start and set up the observer
    await asyncio.sleep(0.01)

    # Simulate the JS code calling the exposed functions
    await exposed_functions["onResponseChunk"]("data1")
    await exposed_functions["onResponseChunk"]("data2")
    await exposed_functions["onResponseDone"]() # Signal end of stream

    # Wait for the consumer to finish
    await consumer_task

    # --- Assertions ---
    # Verify that the correct functions were exposed
    assert "onResponseChunk" in exposed_functions
    assert "onResponseDone" in exposed_functions
    
    # Verify the page interactions
    mock_page.wait_for_selector.assert_awaited_once_with(
        'button[aria-label="Stop generating"]', state="visible", timeout=controller.default_timeout
    )
    mock_page.evaluate.assert_awaited_once()
    
    # Verify the received chunks
    assert chunks == ["data1", "data2"]


@pytest.mark.asyncio
async def test_is_error_response_found(mock_page):
    """Test that an error response is correctly identified."""
    controller = PageController(mock_page)
    error_message = "An error occurred."

    # Mock the error element and its text
    mock_error_element = AsyncMock()
    mock_error_element.inner_text.return_value = error_message
    
    # Make query_selector return the mock element for the first error selector
    mock_page.query_selector.return_value = mock_error_element

    response = await controller.is_error_response()

    assert response == error_message
    mock_page.query_selector.assert_awaited_once_with('.response-block:last-child .error-message')

@pytest.mark.asyncio
async def test_is_error_response_not_found(mock_page):
    """Test that no error is reported when no error element is found."""
    controller = PageController(mock_page)
    
    # Make query_selector return None for all error selectors
    mock_page.query_selector.return_value = None

    response = await controller.is_error_response()

    assert response is None
    assert mock_page.query_selector.await_count == len(controller.error_selectors)
