import functools
import logging
import traceback
import time
from typing import Callable, Any, Dict
from backend.core.exceptions import QLMError, MCPError, MCPInternalError
from backend.core.circuit_breaker import circuit_breaker
from backend.core.forensics import crash_recorder
from backend.core.telemetry import telemetry
from backend.core.audit_logger import audit_logger

logger = logging.getLogger("QLM.MCP.Interceptor")

def mcp_safe(func: Callable) -> Callable:
    """
    Decorator to wrap MCP tool executions.
    Catches exceptions, analyzes tracebacks, and returns structured MCP errors.
    Integrates Circuit Breaker, Crash Forensics, Telemetry, and Audit Logging.
    """
    @functools.wraps(func)
    async def wrapper(self, tool_name: str, args: Dict) -> Any:
        start_time = time.time()
        status = "success"

        # Check Circuit Breaker
        if not circuit_breaker.is_available(tool_name):
            logger.warning(f"Tool {tool_name} blocked by Circuit Breaker.")
            return {
                "error": f"Service Degraded: Tool '{tool_name}' is temporarily unavailable due to repeated failures.",
                "code": -32000,
                "data": {"retry_after": 60}
            }

        try:
            # Audit Log (Before Execution)
            # Note: self refers to AITools instance, but interceptor doesn't have easy access to session_id yet.
            # Ideally we pass session_id in args or context.
            # For now, we use a placeholder or extract from args if present.
            session_id = args.get("session_id", "mcp_global")
            audit_logger.log_action(session_id, tool_name, args)

            result = await func(self, tool_name, args)

            if isinstance(result, dict) and "error" in result:
                status = "logical_error"
            else:
                circuit_breaker.record_success(tool_name)

            return result

        except MCPError as e:
            status = "mcp_error"
            logger.warning(f"MCP Known Error in {tool_name}: {e}")
            return {"error": str(e), "code": e.code, "data": e.details}

        except QLMError as e:
            status = "qlm_error"
            logger.warning(f"QLM Logic Error in {tool_name}: {e}")
            return {"error": str(e), "code": -32603, "data": e.details}

        except Exception as e:
            status = "crash"
            # Critical Crash -> Trip Breaker & Record Dump
            circuit_breaker.record_failure(tool_name)
            dump_path = crash_recorder.record_crash(e, context={"tool": tool_name, "args": args})

            tb = traceback.format_exc()
            logger.error(f"Critical Crash in {tool_name}: {e}\n{tb}")

            suggestion = "Please check your inputs and try again."
            if "MemoryError" in str(e):
                suggestion = "System ran out of memory. Try a smaller dataset or timeframe."
            elif "Timeout" in str(e):
                suggestion = "Operation timed out. The task might be too heavy."

            return {
                "error": f"Internal System Crash: {str(e)}",
                "code": -32603,
                "data": {
                    "traceback": tb,
                    "suggestion": suggestion,
                    "crash_dump": dump_path
                }
            }
        finally:
            duration = (time.time() - start_time) * 1000
            telemetry.record_request(tool_name, duration, status)

    return wrapper
