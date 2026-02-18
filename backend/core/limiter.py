import asyncio
import logging
from typing import Dict

logger = logging.getLogger("QLM.MCP.Limiter")

class RequestLimiter:
    """
    Manages concurrency limits for MCP tools.
    """
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_requests = 0

    async def acquire(self):
        await self.semaphore.acquire()
        self.active_requests += 1
        logger.debug(f"Request acquired. Active: {self.active_requests}")

    def release(self):
        self.semaphore.release()
        self.active_requests -= 1
        logger.debug(f"Request released. Active: {self.active_requests}")

# Singleton Limiter
request_limiter = RequestLimiter(max_concurrent=3) # Strict limit for heavy backtests
