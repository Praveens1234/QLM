import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.exceptions import QLMSystemError, OptimizationError
from fastapi import APIRouter

# Create a router for testing
test_router = APIRouter()

@test_router.get("/api/test_error/{error_type}")
async def trigger_error(error_type: str):
    if error_type == "system":
        raise QLMSystemError("Simulated System Crash")
    elif error_type == "optimization":
        raise OptimizationError("Simulated Optimization Failure")
    elif error_type == "validation":
        raise ValueError("Invalid Input")
    else:
        raise RuntimeError("Unexpected Crash")

# Include router at the beginning of routes list?
# app.include_router appends.
# We need to manually insert.
app.include_router(test_router)

# Hack: Move the last added routes (from test_router) to the front
# test_router adds 1 route.
# app.routes[-1] is the new route.
# We want it before the Mount at app.routes[-2] (assuming mount is last).
# Actually, let's just inspect and move.
# The mount is likely one of the last.

# Let's just create a new client that uses the app.
# But verify routing order.
# If I just use a fresh app with the same exception handler?
# No, I want to test integration.

# Try moving the new route to index 0
latest_route = app.routes.pop()
app.routes.insert(0, latest_route)

client = TestClient(app, raise_server_exceptions=False)

def test_system_error_handling():
    response = client.get("/api/test_error/system")
    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "System Error"
    assert "Simulated System Crash" in data["detail"]

def test_optimization_error_handling():
    response = client.get("/api/test_error/optimization")
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "Optimization Failed"

def test_validation_error_handling():
    response = client.get("/api/test_error/validation")
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "Validation Error"

def test_unhandled_error_handling():
    response = client.get("/api/test_error/unknown")
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "Internal Server Error"
