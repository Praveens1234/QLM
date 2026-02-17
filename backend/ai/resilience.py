from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from backend.core.exceptions import SystemError
import aiohttp
import logging

logger = logging.getLogger("QLM.AI.Resilience")

# Retry strategy for network issues or rate limits
ai_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, SystemError)), # SystemError wraps HTTP errors
    reraise=True
)
