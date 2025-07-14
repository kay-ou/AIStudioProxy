# -*- coding: utf-8 -*-
"""
Keep-Alive Service for AIStudioProxy.

This module provides a service that runs in the background to ensure the
browser session remains active and authenticated.
"""

import asyncio

from ..auth.manager import AuthManager
from ..browser.manager import BrowserManager
from ..utils.logger import LoggerMixin


class KeepAliveService(LoggerMixin):
    """
    A service to keep the browser session alive.
    """

    def __init__(
        self,
        auth_manager: AuthManager,
        browser_manager: BrowserManager,
        check_interval: float = 300.0,  # 5 minutes
    ):
        """
        Initialize the KeepAliveService.

        Args:
            auth_manager: The authentication manager.
            browser_manager: The browser manager.
            check_interval: The interval in seconds to check the session status.
        """
        self.auth_manager = auth_manager
        self.browser_manager = browser_manager
        self.check_interval = check_interval
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """
        Start the keep-alive service as a background task.
        """
        self.log_method_call("start")
        if self._task and not self._task.done():
            self.logger.warning("Keep-alive service is already running.")
            return

        self._task = asyncio.create_task(self._run())
        self.logger.info("Keep-alive service started.")

    async def stop(self) -> None:
        """
        Stop the keep-alive service.
        """
        self.log_method_call("stop")
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass  # Task cancellation is expected
            self.logger.info("Keep-alive service stopped.")
        self._task = None

    async def _run(self) -> None:
        """
        The main loop for the keep-alive service.
        """
        self.logger.info(
            f"Starting keep-alive loop with {self.check_interval}s interval."
        )
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                self.logger.info("Running scheduled session check...")

                is_alive = await self.auth_manager.check_session_status(
                    self.browser_manager
                )

                if not is_alive:
                    self.logger.warning(
                        "Session is not active. Attempting to re-login."
                    )
                    try:
                        await self.auth_manager.login(self.browser_manager)
                    except Exception as e:
                        self.logger.error(
                            "Failed to re-login during keep-alive check.", error=e
                        )
                else:
                    self.logger.info("Session is active.")

            except asyncio.CancelledError:
                self.logger.info("Keep-alive loop cancelled.")
                break
            except Exception as e:
                self.logger.error(
                    "An unexpected error occurred in the keep-alive loop.", error=e
                )
                # Wait before retrying to avoid rapid-fire errors
                await asyncio.sleep(self.check_interval)
