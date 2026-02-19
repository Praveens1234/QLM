from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging
import traceback
from backend.core.exceptions import QLMSystemError, OptimizationError, StrategyError, DataError, QLMError
from ccxt import ExchangeError, NetworkError, RateLimitExceeded, DDoSProtection

logger = logging.getLogger("QLM.API")

async def global_exception_handler(request: Request, exc: Exception):
    """
    Global Exception Handler for FastAPI.
    Returns structured JSON responses for all errors.
    """

    error_content = {
        "error": "Internal Server Error",
        "detail": str(exc),
        "code": 500,
        "path": request.url.path
    }

    # 1. System & Critical Errors
    if isinstance(exc, QLMSystemError):
        error_content["error"] = "System Critical Error"
        error_content["code"] = 503 # Service Unavailable
        logger.critical(f"System Error at {request.url.path}: {exc}")

    # 2. Domain Errors
    elif isinstance(exc, StrategyError):
        error_content["error"] = "Strategy Execution Failed"
        error_content["code"] = 422 # Unprocessable Entity
        logger.error(f"Strategy Error at {request.url.path}: {exc}")

    elif isinstance(exc, OptimizationError):
        error_content["error"] = "Optimization Failed"
        error_content["code"] = 400 # Bad Request
        logger.warning(f"Optimization Error at {request.url.path}: {exc}")

    elif isinstance(exc, DataError):
        error_content["error"] = "Data Error"
        error_content["code"] = 404 # Not Found / Data Missing
        logger.warning(f"Data Error at {request.url.path}: {exc}")

    # 3. Exchange / Network Errors (CCXT)
    elif isinstance(exc, (RateLimitExceeded, DDoSProtection)):
        error_content["error"] = "Exchange Rate Limit Exceeded"
        error_content["code"] = 429 # Too Many Requests
        logger.warning(f"Rate Limit at {request.url.path}: {exc}")

    elif isinstance(exc, NetworkError):
        error_content["error"] = "Exchange Network Error"
        error_content["code"] = 503 # Service Unavailable
        logger.error(f"Network Error at {request.url.path}: {exc}")

    elif isinstance(exc, ExchangeError):
        error_content["error"] = "Exchange API Error"
        error_content["code"] = 502 # Bad Gateway
        logger.error(f"Exchange Error at {request.url.path}: {exc}")

    # 4. Validation Errors
    elif isinstance(exc, ValueError):
        error_content["error"] = "Validation Error"
        error_content["code"] = 422 # Unprocessable Entity
        logger.warning(f"Validation Error at {request.url.path}: {exc}")

    # 5. Generic QLM Errors
    elif isinstance(exc, QLMError):
        error_content["error"] = "Application Error"
        error_content["code"] = 400
        logger.error(f"QLM Error at {request.url.path}: {exc}")

    # 6. Unhandled
    else:
        logger.error(f"Unhandled Exception at {request.url.path}: {exc}\n{traceback.format_exc()}")
        # In production, we might want to hide detail for security.
        # But for this internal tool, full details are helpful.

    return JSONResponse(
        status_code=error_content["code"],
        content=error_content
    )
