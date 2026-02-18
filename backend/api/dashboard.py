from fastapi import APIRouter
from backend.api.mcp_session import session_manager
from backend.core.telemetry import telemetry
from backend.api.transport import mcp_transport

router = APIRouter()

@router.get("/dashboard/mcp")
async def get_dashboard_metrics():
    """
    Aggregate metrics for the Frontend Dashboard.
    """
    metrics = telemetry.get_metrics()

    active_sessions = len(session_manager.sessions)

    return {
        "status": "online" if mcp_transport.active else "offline",
        "active_sessions": active_sessions,
        "total_requests": metrics["total_requests"],
        "tool_performance": metrics["tool_metrics"],
        "recent_activity": session_manager.global_log[:20] # Last 20 actions
    }
