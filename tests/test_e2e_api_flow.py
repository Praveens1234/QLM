import pytest
import asyncio
from httpx import AsyncClient
from backend.main import app
import os
import shutil

# E2E Flow Test
# Simulates a full user session: 
# 1. Check System Health
# 2. Upload/Import Data
# 3. Create & Save Strategy
# 4. Run Backtest
# 5. Check AI Interaction
# 6. Check MCP Status

@pytest.mark.asyncio
async def test_e2e_flow():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        
        print("\n[E2E] 1. Checking Health...")
        response = await ac.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "system": "QLM"}
        print("✅ Health OK")

        print("\n[E2E] 2. Checking Data Manager...")
        # Clean up any existing test data
        response = await ac.get("/api/data/")
        for d in response.json():
            if d['symbol'] == "E2E_TEST":
                await ac.delete(f"/api/data/{d['id']}")
        
        # Import data from URL (mocking the download to avoid ext net dependency issues inside test env if blocked)
        # But here we'll try the real endpoint if allowed, or mock it.
        # Let's try to simulate a file upload which is safer.
        
        # Create a dummy CSV
        os.makedirs("data", exist_ok=True)
        with open("data/e2e_test.csv", "w") as f:
            f.write("time,open,high,low,close,volume\n")
            f.write("2023-01-01 00:00:00,100,105,95,102,1000\n")
            f.write("2023-01-01 01:00:00,102,108,101,107,1500\n")
            f.write("2023-01-01 02:00:00,107,110,106,109,1200\n")
            f.write("2023-01-01 03:00:00,109,112,100,105,1800\n")
            f.write("2023-01-01 04:00:00,105,108,102,106,1100\n")

        with open("data/e2e_test.csv", "rb") as f:
            files = {"file": ("e2e_test.csv", f, "text/csv")}
            data = {"symbol": "E2E_TEST", "timeframe": "1h"}
            response = await ac.post("/api/data/upload", files=files, data=data)
            assert response.status_code == 200
            data_id = response.json()["data"]["id"]
            print(f"✅ Data Uploaded (ID: {data_id})")

        # Verify it's in the list
        response = await ac.get("/api/data/")
        datasets = response.json()
        assert any(d['id'] == data_id for d in datasets)
        print("✅ Data Listed")

        print("\n[E2E] 3. Strategy Lab...")
        strategy_name = "E2E_Strategy"
        strategy_code = """
from backend.core.strategy import Strategy
import pandas as pd

class E2E_Strategy(Strategy):
    def define_variables(self, df):
        return {}
    def entry_long(self, df, vars):
        # Buy on first candle
        s = pd.Series([False] * len(df))
        s.iloc[1] = True 
        return s
    def entry_short(self, df, vars):
        return pd.Series([False] * len(df))
    def exit_long_signal(self, df, vars):
        # Sell on last candle
        s = pd.Series([False] * len(df))
        s.iloc[-1] = True
        return s
    def exit_short_signal(self, df, vars):
        return pd.Series([False] * len(df))
    def exit(self, df, vars, trade):
        return False
    def risk_model(self, df, vars):
        return {}
"""
        # Save Strategy
        response = await ac.post("/api/strategies/", json={"name": strategy_name, "code": strategy_code})
        assert response.status_code == 200
        print("✅ Strategy Saved")

        # Validate Strategy
        response = await ac.post("/api/strategies/validate", json={"name": strategy_name, "code": strategy_code})
        validation = response.json()
        assert validation["valid"] is True
        print("✅ Strategy Validated")

        print("\n[E2E] 4. Backtest Runner...")
        # Run Backtest
        payload = {
            "dataset_id": data_id,
            "strategy_name": strategy_name,
            "cash": 10000,
            "commission": 0.001
        }
        response = await ac.post("/api/backtest/run", json=payload)
        assert response.status_code == 200
        result = response.json()
        if result["status"] == "success":
            assert "results" in result
            print("✅ Backtest Finished Immediately (Small Data)")
        else:
            assert result["status"] == "idling" or result.get("job_id")
            print("✅ Backtest Started")

        # Since backtest is async via websocket usually, the run endpoint might return job ID.
        # We can check progress via polling if endpoint is available, or just assume start is success for API test.
        # Let's try to fetch job status if implemented, or just wait a bit.
        
        print("\n[E2E] 5. AI Assistant...")
        # Create Session
        response = await ac.post("/api/ai/sessions", json={"title": "E2E Test"})
        session_id = response.json()["id"]
        
        # Send Message
        # Mocking the AI response would be needed for a pure unit test, but this is integration.
        # If openAI key is missing, this might fail. We'll wrap in try/except.
        try:
            print("   (Skipping actual AI call to avoid key dependency, checking session creation only)")
            # msg_payload = {"session_id": session_id, "message": "Hello"}
            # response = await ac.post("/api/ai/chat/message", json=msg_payload)
            # assert response.status_code == 200
        except Exception:
            pass
        print(f"✅ AI Session Created (ID: {session_id})")

        print("\n[E2E] 6. MCP Service...")
        # Check Status
        response = await ac.get("/api/mcp/status")
        assert response.status_code == 200
        print("✅ MCP Status Checked")
        
        # Toggle
        response = await ac.post("/api/mcp/toggle", json={"active": False})
        assert response.status_code == 200
        assert response.json()["is_active"] is False
        print("✅ MCP Toggled Off")
        
        response = await ac.post("/api/mcp/toggle", json={"active": True})
        assert response.json()["is_active"] is True
        print("✅ MCP Toggled On")

        # Cleanup
        await ac.delete(f"/api/data/{data_id}")
        await ac.delete(f"/api/strategies/{strategy_name}")
        if os.path.exists("data/e2e_test.csv"):
            os.remove("data/e2e_test.csv")
        print("\n[E2E] Cleanup Complete.")

if __name__ == "__main__":
    import sys
    # Manual run support
    try:
        asyncio.run(test_e2e_flow())
        print("\nAll E2E Tests Passed!")
    except Exception as e:
        print(f"\n❌ E2E Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
