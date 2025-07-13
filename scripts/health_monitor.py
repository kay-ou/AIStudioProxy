#!/usr/bin/env python3
"""
Health monitoring script for AIStudioProxy.

This script continuously monitors the health of the AIStudioProxy service
and can perform automatic recovery actions if needed.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any
import aiohttp
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthMonitor:
    """Health monitoring service for AIStudioProxy."""
    
    def __init__(self, 
                 api_url: str = "http://localhost:2048",
                 check_interval: int = 30,
                 failure_threshold: int = 3,
                 recovery_timeout: int = 300):
        self.api_url = api_url
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.consecutive_failures = 0
        self.last_success_time = time.time()
        self.is_running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down health monitor...")
        self.is_running = False
    
    async def check_health(self) -> Dict[str, Any]:
        """Check the health of the AIStudioProxy service."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"{self.api_url}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        return {
                            "status": "healthy",
                            "response_time": response.headers.get("X-Process-Time", "unknown"),
                            "data": health_data
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "error": f"HTTP {response.status}",
                            "response_time": response.headers.get("X-Process-Time", "unknown")
                        }
        except asyncio.TimeoutError:
            return {
                "status": "unhealthy",
                "error": "Request timeout"
            }
        except aiohttp.ClientError as e:
            return {
                "status": "unhealthy",
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def check_metrics(self) -> Dict[str, Any]:
        """Check the metrics endpoint."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.api_url}/metrics") as response:
                    if response.status == 200:
                        metrics_data = await response.json()
                        return {
                            "status": "available",
                            "data": metrics_data
                        }
                    else:
                        return {
                            "status": "unavailable",
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            return {
                "status": "unavailable",
                "error": str(e)
            }
    
    async def perform_recovery_action(self):
        """Perform recovery actions when service is unhealthy."""
        logger.warning("Attempting recovery actions...")
        
        # Recovery action 1: Wait and retry
        logger.info("Recovery action 1: Waiting for service recovery...")
        await asyncio.sleep(30)
        
        # Recovery action 2: Check if it's a temporary issue
        health_result = await self.check_health()
        if health_result["status"] == "healthy":
            logger.info("Service recovered automatically")
            return True
        
        # Recovery action 3: Log detailed error information
        logger.error("Service still unhealthy after recovery attempts")
        logger.error(f"Last health check result: {json.dumps(health_result, indent=2)}")
        
        # In a production environment, you might want to:
        # - Restart the service
        # - Send alerts to administrators
        # - Scale up additional instances
        # - Perform database cleanup
        
        return False
    
    async def log_health_status(self, health_result: Dict[str, Any], metrics_result: Dict[str, Any]):
        """Log the current health status."""
        status = health_result["status"]
        
        if status == "healthy":
            self.consecutive_failures = 0
            self.last_success_time = time.time()
            
            # Log success with metrics
            if metrics_result["status"] == "available":
                metrics = metrics_result["data"]
                logger.info(
                    f"Service healthy - "
                    f"Uptime: {metrics.get('uptime', 'unknown')}s, "
                    f"Requests: {metrics.get('requests_total', 'unknown')}, "
                    f"Success rate: {self._calculate_success_rate(metrics)}%"
                )
            else:
                logger.info("Service healthy (metrics unavailable)")
        else:
            self.consecutive_failures += 1
            logger.warning(
                f"Service unhealthy ({self.consecutive_failures}/{self.failure_threshold}) - "
                f"Error: {health_result.get('error', 'unknown')}"
            )
    
    def _calculate_success_rate(self, metrics: Dict[str, Any]) -> float:
        """Calculate success rate from metrics."""
        total = metrics.get('requests_total', 0)
        success = metrics.get('requests_success', 0)
        
        if total == 0:
            return 100.0
        
        return round((success / total) * 100, 2)
    
    async def run(self):
        """Main monitoring loop."""
        logger.info(f"Starting health monitor for {self.api_url}")
        logger.info(f"Check interval: {self.check_interval}s")
        logger.info(f"Failure threshold: {self.failure_threshold}")
        
        while self.is_running:
            try:
                # Perform health check
                health_result = await self.check_health()
                metrics_result = await self.check_metrics()
                
                # Log status
                await self.log_health_status(health_result, metrics_result)
                
                # Check if recovery is needed
                if (health_result["status"] == "unhealthy" and 
                    self.consecutive_failures >= self.failure_threshold):
                    
                    logger.error(
                        f"Service has been unhealthy for {self.consecutive_failures} consecutive checks"
                    )
                    
                    # Perform recovery
                    recovery_success = await self.perform_recovery_action()
                    
                    if not recovery_success:
                        logger.critical("Recovery actions failed - manual intervention may be required")
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(self.check_interval)
        
        logger.info("Health monitor stopped")

async def main():
    """Main function."""
    import os
    
    # Configuration from environment variables
    api_url = os.getenv("MONITOR_API_URL", "http://localhost:2048")
    check_interval = int(os.getenv("MONITOR_CHECK_INTERVAL", "30"))
    failure_threshold = int(os.getenv("MONITOR_FAILURE_THRESHOLD", "3"))
    recovery_timeout = int(os.getenv("MONITOR_RECOVERY_TIMEOUT", "300"))
    
    # Create and run monitor
    monitor = HealthMonitor(
        api_url=api_url,
        check_interval=check_interval,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout
    )
    
    try:
        await monitor.run()
    except KeyboardInterrupt:
        logger.info("Health monitor interrupted by user")
    except Exception as e:
        logger.error(f"Health monitor failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
