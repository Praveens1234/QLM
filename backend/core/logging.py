import sys
import logging
import structlog
from typing import Optional

def configure_logging(log_level: str = "INFO", json_format: bool = False):
    """
    Configures structured logging for the application.
    """
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_format:
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        processors = shared_processors + [structlog.dev.ConsoleRenderer()]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use structlog
    handler = logging.StreamHandler(sys.stdout)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Remove existing handlers to avoid duplication
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    root_logger.addHandler(handler)

    # Redirect standard logging to structlog
    # This ensures third-party libraries using logging also get formatted
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level.upper())

def get_logger(name: str):
    """
    Returns a structured logger with the given name.
    """
    return structlog.get_logger(name)
