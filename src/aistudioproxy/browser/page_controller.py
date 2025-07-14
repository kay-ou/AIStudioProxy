# -*- coding: utf-8 -*-
"""
Page Controller for AIStudioProxy.

This module provides the PageController class, which is responsible for
managing interactions with the AI Studio page, including navigation,
initialization, and basic operations.
"""

import asyncio
from typing import AsyncGenerator, Optional

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..utils.logger import LoggerMixin
from ..utils.retry import async_retry


class PageController(LoggerMixin):
    """
    Manages interactions with the AI Studio page.
    """

    AISTUDIO_URL = "https://aistudio.google.com/"
    error_selectors = [
        ".error-message",
        '[role="alert"]',
        ".MuiAlert-message",  # A common selector for Material-UI alerts
    ]

    def __init__(self, page: Page, default_timeout: int = 30000):
        """
        Initialize the PageController.

        Args:
            page: The Playwright page object to control.
            default_timeout: Default timeout for operations in milliseconds.
        """
        self.page = page
        self.default_timeout = default_timeout

    @async_retry()
    async def navigate_to_aistudio(self) -> None:
        """
        Navigate to the AI Studio page and wait for it to load.
        """
        self.log_method_call("navigate_to_aistudio")

        if self.page.url == self.AISTUDIO_URL:
            self.logger.info("Already at AI Studio page.")
            return

        await self.page.goto(
            self.AISTUDIO_URL, wait_until="load", timeout=self.default_timeout
        )
        self.logger.info("Navigated to AI Studio page.")

    @async_retry()
    async def click(self, selector: str, timeout: Optional[int] = None) -> None:
        """
        Click an element on the page.

        Args:
            selector: The CSS selector of the element to click.
            timeout: Optional timeout in milliseconds.
        """
        self.log_method_call("click", selector=selector)
        try:
            await self.page.click(selector, timeout=timeout or self.default_timeout)
        except PlaywrightTimeoutError:
            self.logger.error("Timeout while clicking element", selector=selector)
            raise

    @async_retry()
    async def fill(
        self, selector: str, text: str, timeout: Optional[int] = None
    ) -> None:
        """
        Fill an input element with text.

        Args:
            selector: The CSS selector of the input element.
            text: The text to fill.
            timeout: Optional timeout in milliseconds.
        """
        self.log_method_call("fill", selector=selector)
        try:
            await self.page.fill(
                selector, text, timeout=timeout or self.default_timeout
            )
        except PlaywrightTimeoutError:
            self.logger.error("Timeout while filling element", selector=selector)
            raise

    @async_retry()
    async def wait_for_selector(
        self, selector: str, timeout: Optional[int] = None, **kwargs
    ) -> None:
        """
        Wait for an element to appear on the page.

        Args:
            selector: The CSS selector of the element to wait for.
            timeout: Optional timeout in milliseconds.
            **kwargs: Additional arguments to pass to Playwright's wait_for_selector.
        """
        self.log_method_call("wait_for_selector", selector=selector, **kwargs)
        try:
            await self.page.wait_for_selector(
                selector, timeout=timeout or self.default_timeout, **kwargs
            )
        except PlaywrightTimeoutError:
            self.logger.error(
                "Timeout while waiting for selector", selector=selector, **kwargs
            )
            raise

    async def close(self) -> None:
        """
        Close the page.
        """
        self.log_method_call("close")
        if not self.page.is_closed():
            await self.page.close()
            self.logger.info("Page closed.")

    async def is_logged_in(self, timeout: Optional[int] = 5000) -> bool:
        """
        Check if the user is logged in by looking for a specific element.

        Args:
            timeout: Optional timeout in milliseconds.

        Returns:
            True if the user is logged in, False otherwise.
        """
        self.log_method_call("is_logged_in")
        # This selector should target an element that is only visible when logged in,
        # for example, a user profile button or avatar.
        # TODO: Replace with a more reliable selector for AI Studio.
        login_indicator_selector = 'button[aria-label="Google Account"]'

        try:
            await self.page.wait_for_selector(
                login_indicator_selector, state="visible", timeout=timeout
            )
            self.logger.info("Login indicator found, user is logged in.")
            return True
        except PlaywrightTimeoutError:
            self.logger.warning("Login indicator not found, user is not logged in.")
            return False

    @async_retry(attempts=3)
    async def switch_model(self, model_name: str) -> None:
        """
        Switch to a specified model in the AI Studio UI.

        Args:
            model_name: The name of the model to switch to (e.g., "Gemini 1.5 Pro").

        Raises:
            ValueError: If the specified model is not found or cannot be selected.
            PlaywrightTimeoutError: If a timeout occurs during the operation.
        """
        self.log_method_call("switch_model", model_name=model_name)

        model_menu_selector = 'button[aria-label="Model"]'
        try:
            await self.click(model_menu_selector)
            self.logger.info("Model selection menu opened.")
        except PlaywrightTimeoutError:
            self.logger.error("Failed to open model selection menu.")
            raise ValueError("Could not open model selection menu.")

        model_element_selector = f'text="{model_name}"'
        try:
            await self.click(model_element_selector)
            self.logger.info(f"Selected model: {model_name}")
        except PlaywrightTimeoutError:
            self.logger.error(f"Model '{model_name}' not found in the menu.")
            raise ValueError(f"Model '{model_name}' not found.")

        try:
            await self.page.wait_for_selector(
                f'button[aria-label="Model"]:has-text("{model_name}")', state="visible"
            )
            self.logger.info(f"Successfully switched to model: {model_name}")
        except PlaywrightTimeoutError:
            self.logger.error(f"Failed to verify model switch to '{model_name}'.")
            raise ValueError(f"Failed to switch to model '{model_name}'.")

    async def send_message(self, message: str) -> None:
        """
        Sends a message to the AI Studio chat input.

        Args:
            message: The message to send.

        Raises:
            ValueError: If the chat input or send button is not found.
        """
        self.log_method_call("send_message")

        chat_input_selector = 'div[aria-label="Chat input"]'
        send_button_selector = 'button[aria-label="Send message"]'

        try:
            await self.fill(chat_input_selector, message)
            self.logger.info("Filled chat input with message.")
        except PlaywrightTimeoutError:
            self.logger.error("Failed to find chat input.")
            raise ValueError("Chat input not found.")

        try:
            await self.click(send_button_selector)
            self.logger.info("Clicked send button.")
        except PlaywrightTimeoutError:
            self.logger.error("Failed to find send button.")
            raise ValueError("Send button not found.")

    async def wait_for_response(self) -> str:
        """
        Waits for the AI response to be generated and returns the full response text.

        This method first waits for the "Stop generating" button to appear,
        indicating that the response generation has started. Then, it waits
        for that same button to disappear, indicating the response is complete.
        Finally, it extracts the text from the last response block.

        Returns:
            The full text of the AI's response.

        Raises:
            PlaywrightTimeoutError: If the response start or end indicators
                                    do not appear/disappear within the timeout.
            ValueError: If the response content cannot be found after generation.
        """
        self.log_method_call("wait_for_response")

        stop_generating_selector = 'button[aria-label="Stop generating"]'

        self.logger.info("Waiting for response generation to start...")
        await self.wait_for_selector(stop_generating_selector, state="visible")
        self.logger.info("Response generation started.")

        self.logger.info("Waiting for response generation to complete...")
        await self.wait_for_selector(stop_generating_selector, state="hidden")
        self.logger.info("Response generation completed.")

        # After the response is complete, we need to get the content.
        # The responses are in a div with class "response-block". We want the last one.
        response_selector = ".response-block:last-child"

        try:
            response_element = await self.page.query_selector(response_selector)
            if not response_element:
                self.logger.error("Could not find response block element.")
                raise ValueError("Response block not found.")

            response_text = await response_element.inner_text()
            self.logger.info(
                "Extracted response text.", response_length=len(response_text)
            )
            return response_text
        except Exception as e:
            self.logger.error("Failed to extract response text.", error=e)
            raise ValueError("Failed to extract response text.")

    async def start_streaming_response(self) -> AsyncGenerator[str, None]:
        """
        Starts listening for a streaming response and yields text chunks.

        This method sets up a MutationObserver to detect changes in the response
        area and yields new text chunks as they appear. It also monitors for
        the end of the response.

        Yields:
            str: A chunk of the response text.

        Raises:
            asyncio.TimeoutError: If the response generation does not start or
                                  end within the expected timeout.
        """
        self.log_method_call("start_streaming_response")
        queue = asyncio.Queue()

        async def on_response_chunk(chunk: str):
            await queue.put(chunk)

        async def on_response_done():
            await queue.put(None)  # Signal for end of stream

        await self.page.expose_function("onResponseChunk", on_response_chunk)
        await self.page.expose_function("onResponseDone", on_response_done)

        response_container_selector = ".chat-history"
        stop_generating_selector = 'button[aria-label="Stop generating"]'

        js_code = (
            """
        () => {
            const targetNode = document.querySelector('"""
            + response_container_selector
            + """');
            if (!targetNode) {
                console.error('Response container not found');
                window.onResponseDone();
                return;
            }

            let lastResponseBlock = null;
            let lastText = '';

            const responseObserver = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                        mutation.addedNodes.forEach(node => {
                            if (node.nodeType === 1 && node.classList.contains('response-block')) {
                                lastResponseBlock = node;
                                observeResponseBlock(lastResponseBlock);
                            }
                        });
                    }
                }
            });

            const observeResponseBlock = (responseBlock) => {
                const blockObserver = new MutationObserver(() => {
                    const newText = responseBlock.innerText;
                    if (newText !== lastText) {
                        const chunk = newText.substring(lastText.length);
                        lastText = newText;
                        window.onResponseChunk(chunk);
                    }
                });
                blockObserver.observe(responseBlock, { childList: true, characterData: true, subtree: true });
            };

            responseObserver.observe(targetNode, { childList: true });

            // Handle completion
            const stopButton = document.querySelector('"""
            + stop_generating_selector
            + """');
            if (stopButton) {
                const doneObserver = new MutationObserver(() => {
                    if (!document.querySelector('"""
            + stop_generating_selector
            + """')) {
                        doneObserver.disconnect();
                        // Final check for any remaining text
                        if (lastResponseBlock) {
                           const finalText = lastResponseBlock.innerText;
                           if (finalText.length > lastText.length) {
                               window.onResponseChunk(finalText.substring(lastText.length));
                           }
                        }
                        window.onResponseDone();
                    }
                });
                doneObserver.observe(document.body, { childList: true, subtree: true });
            } else {
                // If stop button never appears, we might be in an error state or done already
                window.onResponseDone();
            }
        }
        """
        )

        # Wait for generation to start
        self.logger.info("Waiting for response generation to start...")
        await self.wait_for_selector(stop_generating_selector, state="visible")
        self.logger.info("Response generation started.")

        await self.page.evaluate(js_code)
        self.logger.info("MutationObserver for streaming response started.")

        while True:
            try:
                # Wait for a new chunk with a timeout
                chunk = await asyncio.wait_for(
                    queue.get(), timeout=self.default_timeout / 1000
                )
                if chunk is None:
                    self.logger.info("End of stream signal received.")
                    break
                yield chunk
            except asyncio.TimeoutError:
                self.logger.error("Timeout waiting for next stream chunk.")
                # Check if the stop button is gone, which means we are done
                if not await self.page.query_selector(stop_generating_selector):
                    self.logger.info(
                        "Stop button disappeared, assuming stream is complete."
                    )
                    break
                else:
                    raise  # Re-raise if we timed out but generation is supposedly still active

    async def is_error_response(self) -> Optional[str]:
        """
        Checks if the latest response is an error message.

        Returns:
            The error message text if an error is found, otherwise None.
        """
        self.log_method_call("is_error_response")

        for selector in self.error_selectors:
            try:
                error_element = await self.page.query_selector(
                    f".response-block:last-child {selector}"
                )
                if error_element:
                    error_text = await error_element.inner_text()
                    self.logger.warning(
                        "Error response detected.",
                        selector=selector,
                        error_text=error_text,
                    )
                    return error_text
            except Exception as e:
                self.logger.debug(
                    "Could not check for error selector, it might not exist.",
                    selector=selector,
                    error=str(e),
                )

        return None
