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
