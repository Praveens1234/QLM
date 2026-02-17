import time
import logging
from collections import deque
from typing import Dict, Any, List

logger = logging.getLogger("QLM.MCP.Telemetry")

class TelemetryRecorder:
    """
    Records latency and status codes for MCP requests.
    """
    def __init__(self):
        self.latency_log: deque = deque(maxlen=1000) # Keep last 1000 requests
        self.tool_stats: Dict[str, Dict] = {}

    def record_request(self, tool_name: str, duration_ms: float, status: str):
        self.latency_log.append({
            "timestamp": time.time(),
            "tool": tool_name,
            "duration": duration_ms,
            "status": status
        })

        if tool_name not in self.tool_stats:
            self.tool_stats[tool_name] = {"count": 0, "total_ms": 0, "errors": 0}

        stats = self.tool_stats[tool_name]
        stats["count"] += 1
        stats["total_ms"] += duration_ms
        if status != "success":
            stats["errors"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        avg_latency = {}
        for tool, stats in self.tool_stats.items():
            avg = stats["total_ms"] / stats["count"] if stats["count"] > 0 else 0
            error_rate = (stats["errors"] / stats["count"] * 100) if stats["count"] > 0 else 0
            avg_latency[tool] = {
                "avg_ms": round(avg, 2),
                "count": stats["count"],
                "error_rate_pct": round(error_rate, 2)
            }

        return {
            "tool_metrics": avg_latency,
            "total_requests": len(self.latency_log)
        }

telemetry = TelemetryRecorder()
