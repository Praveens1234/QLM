import functools
import logging
import traceback
import time
import asyncio
from typing import Callable, Any, Dict
from backend.core.exceptions import QLMError, MCPError, MCPInternalError
from backend.core.circuit_breaker import circuit_breaker
from backend.core.forensics import crash_recorder
from backend.core.telemetry import telemetry
from backend.core.audit_logger import audit_logger
from backend.core.diagnostics import diagnostics, EventLevel, EventCategory

logger = logging.getLogger("QLM.MCP.Interceptor")

def mcp_safe(func: Callable) -> Callable:
    """
    Decorator to wrap MCP tool executions.
    Catches exceptions, analyzes tracebacks, and returns structured MCP errors.
    Integrates Circuit Breaker, Crash Forensics, Telemetry, Audit Logging, and Diagnostics.
    """
    @functools.wraps(func)
    async def wrapper(self, tool_name: str, args: Dict) -> Any:
        start_time = time.time()
        status = "success"

        # Check Circuit Breaker
        if not circuit_breaker.is_available(tool_name):
            diagnostics.record(EventLevel.WARNING, EventCategory.MCP_TOOL_CALL,
                f"Tool '{tool_name}' blocked by Circuit Breaker",
                details={"tool": tool_name})
            return {
                "error": f"Service Degraded: Tool '{tool_name}' is temporarily unavailable due to repeated failures.",
                "code": -32000,
                "data": {"retry_after": 60}
            }

        try:
            # Audit Log (non-blocking to prevent DB lock from freezing event loop)
            try:
                session_id = args.get("session_id", "mcp_global")
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, audit_logger.log_action, session_id, tool_name, args)
            except Exception:
                pass  # Never let audit logging crash a tool execution

            diagnostics.record(EventLevel.DEBUG, EventCategory.MCP_TOOL_CALL,
                f"mcp_safe: executing '{tool_name}'",
                details={"tool": tool_name, "args_keys": list(args.keys())})

            result = await func(self, tool_name, args)

            elapsed = round((time.time() - start_time) * 1000, 1)

            if isinstance(result, dict) and "error" in result:
                status = "logical_error"
                diagnostics.record(EventLevel.WARNING, EventCategory.MCP_TOOL_RESULT,
                    f"mcp_safe: '{tool_name}' returned logical error in {elapsed}ms",
                    details={"tool": tool_name, "error": result.get("error", ""), "elapsed_ms": elapsed})
            else:
                circuit_breaker.record_success(tool_name)
                diagnostics.record(EventLevel.DEBUG, EventCategory.MCP_TOOL_RESULT,
                    f"mcp_safe: '{tool_name}' succeeded in {elapsed}ms",
                    details={"tool": tool_name, "elapsed_ms": elapsed})

            return result

        except MCPError as e:
            status = "mcp_error"
            diagnostics.record(EventLevel.WARNING, EventCategory.MCP_TOOL_RESULT,
                f"mcp_safe: MCP error in '{tool_name}': {e}",
                details={"tool": tool_name, "code": e.code}, error=e)
            return {"error": str(e), "code": e.code, "data": e.details}

        except QLMError as e:
            status = "qlm_error"
            diagnostics.record(EventLevel.WARNING, EventCategory.MCP_TOOL_RESULT,
                f"mcp_safe: QLM error in '{tool_name}': {e}",
                details={"tool": tool_name}, error=e)
            return {"error": str(e), "code": -32603, "data": e.details}
            
        except asyncio.TimeoutError:
            status = "timeout"
            elapsed = round((time.time() - start_time) * 1000, 1)
            diagnostics.record(EventLevel.CRITICAL, EventCategory.MCP_TIMEOUT,
                f"mcp_safe: TIMEOUT in '{tool_name}' after {elapsed}ms",
                details={"tool": tool_name, "elapsed_ms": elapsed})
            return {
                "error": f"Operation Timed Out. The task '{tool_name}' took too long to complete.",
                "code": -32004,
                "data": {"suggestion": "Please ensure the dataset is not too large or network dependencies are reachable."}
            }

        except Exception as e:
            status = "crash"
            elapsed = round((time.time() - start_time) * 1000, 1)
            
            # Critical Crash -> Trip Breaker & Record Dump
            circuit_breaker.record_failure(tool_name)
            
            try:
                dump_path = crash_recorder.record_crash(e, context={"tool": tool_name, "args": args})
            except Exception:
                dump_path = ""
            
            tb = traceback.format_exc()
            
            diagnostics.record(EventLevel.CRITICAL, EventCategory.CRASH,
                f"mcp_safe: CRASH in '{tool_name}' after {elapsed}ms: {type(e).__name__}: {e}",
                details={"tool": tool_name, "elapsed_ms": elapsed, "dump_path": dump_path},
                error=e)

            suggestion = "Please check your inputs and try again."
            if "MemoryError" in str(type(e).__name__):
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
            try:
                telemetry.record_request(tool_name, duration, status)
            except Exception:
                pass  # Never let telemetry crash the wrapper

    return wrapper
