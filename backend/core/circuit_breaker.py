import time
import logging
from typing import Dict

logger = logging.getLogger("QLM.MCP.CircuitBreaker")

class CircuitBreaker:
    """
    Protects the system from cascading failures by temporarily disabling
    problematic tools.
    """
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures: Dict[str, int] = {}
        self.last_failure_time: Dict[str, float] = {}
        self.state: Dict[str, str] = {} # "OPEN", "CLOSED", "HALF_OPEN"

    def record_failure(self, tool_name: str):
        current_time = time.time()

        # Reset if recovery timeout passed
        if tool_name in self.last_failure_time:
            if current_time - self.last_failure_time[tool_name] > self.recovery_timeout:
                self.failures[tool_name] = 0
                self.state[tool_name] = "CLOSED"

        self.failures[tool_name] = self.failures.get(tool_name, 0) + 1
        self.last_failure_time[tool_name] = current_time

        if self.failures[tool_name] >= self.threshold:
            self.state[tool_name] = "OPEN"
            logger.warning(f"Circuit Breaker OPEN for tool: {tool_name}")

    def record_success(self, tool_name: str):
        if self.state.get(tool_name) == "OPEN":
            # If we allowed a call and it succeeded, close it
            self.state[tool_name] = "CLOSED"
            self.failures[tool_name] = 0
            logger.info(f"Circuit Breaker CLOSED for tool: {tool_name}")
        elif self.failures.get(tool_name, 0) > 0:
            self.failures[tool_name] = max(0, self.failures[tool_name] - 1)

    def is_available(self, tool_name: str) -> bool:
        if self.state.get(tool_name) == "OPEN":
            # Check if timeout passed to allow a retry (Half-Open logic)
            if time.time() - self.last_failure_time.get(tool_name, 0) > self.recovery_timeout:
                self.state[tool_name] = "HALF_OPEN"
                logger.info(f"Circuit Breaker HALF_OPEN for tool: {tool_name}")
                return True # Allow one test request
            return False
        return True

# Singleton
circuit_breaker = CircuitBreaker()
