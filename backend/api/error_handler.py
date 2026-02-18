from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging
import traceback
from backend.core.exceptions import SystemError, OptimizationError

logger = logging.getLogger("QLM.API")

async def global_exception_handler(request: Request, exc: Exception):
    """
    Global Exception Handler for FastAPI.
    Returns structured JSON responses for all errors.
    """

    # Standardize Error Response
    error_content = {
        "error": "Internal Server Error",
        "detail": str(exc),
        "code": 500,
        "path": request.url.path
    }

    if isinstance(exc, SystemError):
        error_content["error"] = "System Error"
        error_content["code"] = 503 # Service Unavailable
        logger.error(f"System Error at {request.url.path}: {exc}")

    elif isinstance(exc, OptimizationError):
        error_content["error"] = "Optimization Failed"
        error_content["code"] = 400 # Bad Request
        logger.warning(f"Optimization Error at {request.url.path}: {exc}")

    elif isinstance(exc, ValueError):
        error_content["error"] = "Validation Error"
        error_content["code"] = 422 # Unprocessable Entity
        logger.warning(f"Validation Error at {request.url.path}: {exc}")

    else:
        # Unexpected Error
        logger.error(f"Unhandled Exception at {request.url.path}: {exc}\n{traceback.format_exc()}")
        # In production, we might want to hide detail for security, but for this dev tool it's useful.

    return JSONResponse(
        status_code=error_content["code"],
        content=error_content
    )
