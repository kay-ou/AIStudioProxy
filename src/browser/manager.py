# -*- coding: utf-8 -*-
"""
Browser Manager for AIStudioProxy.

This module provides the BrowserManager class, which is responsible for
managing the lifecycle of the browser instance, including startup, shutdown,
and health checks.
"""

import asyncio
from typing import Optional

from playwright.async_api import Browser, Playwright, async_playwright
from camoufox import Camoufox

from ..utils.logger import LoggerMixin
from ..utils.config import BrowserConfig


class BrowserManager(LoggerMixin):
    """
    Manages the Playwright browser instance.
    """

    def __init__(self, config: BrowserConfig):
        """
        Initialize the BrowserManager.

        Args:
            config: Browser configuration settings.
        """
        self.config = config
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None

    async def start(self) -> None:
        """
        Start the browser instance.
        """
        self.log_method_call("start")
        if self.browser and self.browser.is_connected():
            self.logger.warning("Browser is already running.")
            return

        self.playwright = await async_playwright().start()
        self.browser = await self.launch_browser()
        self.logger.info("Browser started successfully.")

    async def stop(self) -> None:
        """
        Stop the browser instance.
        """
        self.log_method_call("stop")
        if self.browser and self.browser.is_connected():
            await self.browser.close()
            self.logger.info("Browser closed.")
        if self.playwright:
            await self.playwright.stop()
            self.logger.info("Playwright stopped.")
        self.browser = None
        self.playwright = None

    async def restart(self) -> None:
        """
        Restart the browser instance.
        """
        self.log_method_call("restart")
        await self.stop()
        await self.start()

    async def health_check(self) -> bool:
        """
        Check the health of the browser instance.

        Returns:
            True if the browser is healthy, False otherwise.
        """

        if not self.browser or not self.browser.is_connected():
            return False
        try:
            # Perform a quick operation to check browser responsiveness
            page = await self.browser.new_page()
            await page.close()
            return True
        except Exception as e:
            self.logger.error("Browser health check failed", error=str(e))
            return False

    async def launch_browser(self) -> Browser:
        """
        Launch the browser with the specified configuration.

        Returns:
            The launched browser instance.
        """
        self.logger.info("Launching browser with Camoufox...", headless=self.config.headless)
        
        fox = Camoufox(
            browser_type="chromium",
            playwright_handle=self.playwright
        )
        
        browser = await fox.launch(
            headless=self.config.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                f"--remote-debugging-port={self.config.port}",
            ],
        )
        return browser
