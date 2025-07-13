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
