# -*- coding: utf-8 -*-
"""
Page Controller for AIStudioProxy.

This module provides the PageController class, which is responsible for
managing interactions with the AI Studio page, including navigation,
initialization, and basic operations.
"""

from typing import Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from ..utils.logger import LoggerMixin
from ..utils.retry import async_retry


class PageController(LoggerMixin):
    """
    Manages interactions with the AI Studio page.
    """

    AISTUDIO_URL = "https://aistudio.google.com/"

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

        await self.page.goto(self.AISTUDIO_URL, wait_until="load", timeout=self.default_timeout)
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
    async def fill(self, selector: str, text: str, timeout: Optional[int] = None) -> None:
        """
        Fill an input element with text.

        Args:
            selector: The CSS selector of the input element.
            text: The text to fill.
            timeout: Optional timeout in milliseconds.
        """
        self.log_method_call("fill", selector=selector)
        try:
            await self.page.fill(selector, text, timeout=timeout or self.default_timeout)
        except PlaywrightTimeoutError:
            self.logger.error("Timeout while filling element", selector=selector)
            raise

    @async_retry()
    async def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> None:
        """
        Wait for an element to appear on the page.

        Args:
            selector: The CSS selector of the element to wait for.
            timeout: Optional timeout in milliseconds.
        """
        self.log_method_call("wait_for_selector", selector=selector)
        try:
            await self.page.wait_for_selector(selector, timeout=timeout or self.default_timeout)
        except PlaywrightTimeoutError:
            self.logger.error("Timeout while waiting for selector", selector=selector)
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
                login_indicator_selector, 
                state="visible",
                timeout=timeout
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
            await self.page.wait_for_selector(f'button[aria-label="Model"]:has-text("{model_name}")', state="visible")
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
