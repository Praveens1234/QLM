"""
QLM System Diagnostics & Bug Recorder

Centralized logging system that captures every MCP event, system health,
and crash with full context. Writes to both in-memory ring buffer (for API access)
and persistent file log.
"""
import os
import json
import time
import asyncio
import traceback
import platform
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import deque
from enum import Enum

logger = logging.getLogger("QLM.Diagnostics")


class EventLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventCategory(str, Enum):
    MCP_TRANSPORT = "MCP_TRANSPORT"       # SSE connect/disconnect/error
    MCP_TOOL_CALL = "MCP_TOOL_CALL"       # Tool invocations
    MCP_TOOL_RESULT = "MCP_TOOL_RESULT"   # Tool results
    MCP_TIMEOUT = "MCP_TIMEOUT"           # Timeout events
    SYSTEM_HEALTH = "SYSTEM_HEALTH"       # CPU/Memory snapshots
    CRASH = "CRASH"                       # Unhandled exceptions
    SERVER = "SERVER"                     # Server lifecycle events
    EVENT_LOOP = "EVENT_LOOP"             # Event loop health checks


class DiagnosticsRecorder:
    """
    Thread-safe event recorder with in-memory ring buffer and file persistence.
    """

    def __init__(self, log_dir: str = "logs", max_events: int = 500):
        self.log_dir = log_dir
        self.max_events = max_events
        self._events: deque = deque(maxlen=max_events)
        self._crash_count = 0
        self._tool_call_count = 0
        self._timeout_count = 0
        self._start_time = time.time()

        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)

        # Persistent log file
        self._log_file = os.path.join(log_dir, "diagnostics.jsonl")

    def record(
        self,
        level: EventLevel,
        category: EventCategory,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ):
        """Record a diagnostic event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "epoch": time.time(),
            "level": level.value,
            "category": category.value,
            "message": message,
            "details": details or {},
        }

        if error:
            event["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc()
            }
            self._crash_count += 1

        if category == EventCategory.MCP_TOOL_CALL:
            self._tool_call_count += 1
        if category == EventCategory.MCP_TIMEOUT:
            self._timeout_count += 1

        # Add to ring buffer
        self._events.append(event)

        # Log to Python logger
        log_func = getattr(logger, level.value.lower(), logger.info)
        log_func(f"[{category.value}] {message}")

        # Persist to file (non-blocking best-effort)
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, default=str) + "\n")
        except Exception:
            pass  # Never let file I/O crash the recorder

    def get_events(
        self,
        limit: int = 50,
        level: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict]:
        """Get recent events with optional filtering."""
        events = list(self._events)
        events.reverse()  # Most recent first

        if level:
            events = [e for e in events if e["level"] == level]
        if category:
            events = [e for e in events if e["category"] == category]

        return events[:limit]

    def get_summary(self) -> Dict[str, Any]:
        """Get a system health summary."""
        uptime = time.time() - self._start_time

        # Count events by level
        level_counts = {}
        for event in self._events:
            lv = event["level"]
            level_counts[lv] = level_counts.get(lv, 0) + 1

        # Count events by category
        category_counts = {}
        for event in self._events:
            cat = event["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Get last 5 errors
        recent_errors = [
            e for e in reversed(list(self._events))
            if e["level"] in ("ERROR", "CRITICAL")
        ][:5]

        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
        except Exception:
            cpu = -1
            mem = -1

        return {
            "uptime_seconds": round(uptime, 1),
            "total_events": len(self._events),
            "total_crashes": self._crash_count,
            "total_tool_calls": self._tool_call_count,
            "total_timeouts": self._timeout_count,
            "events_by_level": level_counts,
            "events_by_category": category_counts,
            "recent_errors": recent_errors,
            "system": {
                "os": platform.system(),
                "python": platform.python_version(),
                "cpu_percent": cpu,
                "memory_percent": mem,
            },
            "log_file": self._log_file,
        }

    def clear(self):
        """Clear in-memory events."""
        self._events.clear()
        self._crash_count = 0
        self._tool_call_count = 0
        self._timeout_count = 0

    async def start_health_monitor(self, interval: int = 60):
        """Background task that records system health periodically."""
        while True:
            try:
                await asyncio.sleep(interval)
                import psutil
                self.record(
                    EventLevel.DEBUG,
                    EventCategory.SYSTEM_HEALTH,
                    f"Health: CPU={psutil.cpu_percent()}%, MEM={psutil.virtual_memory().percent}%",
                    details={
                        "cpu_percent": psutil.cpu_percent(),
                        "memory_percent": psutil.virtual_memory().percent,
                    }
                )

                # Check event loop responsiveness
                loop = asyncio.get_running_loop()
                start = loop.time()
                await asyncio.sleep(0)
                lag = (loop.time() - start) * 1000
                if lag > 100:  # More than 100ms lag = event loop is stressed
                    self.record(
                        EventLevel.WARNING,
                        EventCategory.EVENT_LOOP,
                        f"Event loop lag detected: {lag:.1f}ms",
                        details={"lag_ms": round(lag, 1)}
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.record(
                    EventLevel.ERROR,
                    EventCategory.SYSTEM_HEALTH,
                    f"Health monitor error: {e}",
                    error=e
                )


# Singleton
diagnostics = DiagnosticsRecorder()
