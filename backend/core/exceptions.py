class QLMError(Exception):
    """Base class for all QLM-specific exceptions."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {}

class StrategyError(QLMError):
    """Raised when a strategy fails validation or execution."""
    pass

class DataError(QLMError):
    """Raised when data ingestion or processing fails."""
    pass

class SystemError(QLMError):
    """Raised for critical system failures (e.g., DB lock, OOM)."""
    pass

class OptimizationError(QLMError):
    """Raised when optimization fails."""
    pass

# --- MCP Specific Errors ---
class MCPError(QLMError):
    """Base for MCP Protocol Errors."""
    def __init__(self, message: str, code: int, data: dict = None):
        super().__init__(message, data)
        self.code = code

class MCPInvalidRequestError(MCPError):
    def __init__(self, message: str = "Invalid Request", data: dict = None):
        super().__init__(message, -32600, data)

class MCPMethodNotFoundError(MCPError):
    def __init__(self, message: str = "Method not found", data: dict = None):
        super().__init__(message, -32601, data)

class MCPInvalidParamsError(MCPError):
    def __init__(self, message: str = "Invalid params", data: dict = None):
        super().__init__(message, -32602, data)

class MCPInternalError(MCPError):
    def __init__(self, message: str = "Internal error", data: dict = None):
        super().__init__(message, -32603, data)
