import asyncio
import os
import json
from backend.api.mcp_tools import MCPTools

async def test_mcp_async_upload():
    print("Testing MCP Async Catbox Upload...")
    tools = MCPTools()
    
    # Setup dummy environment to run a backtest
    # We need a dummy strategy and data to simulate a quick backtest.
    # Actually, we can just call get_definitions to check if it parses.
    defs = tools.get_definitions()
    print(f"Loaded {len(defs)} tool definitions.")
    
    # Write a quick dummy CSV file to test just the async upload mechanism itself
    dummy_csv = "dummy_trades.csv"
    with open(dummy_csv, "w") as f:
        f.write("time,price,size,type,pnl\n2023-01-01,100,1,BUY,10\n")
    
    run_id = "test-run-1234"
    
    # 1. Spawn upload
    print(f"Spawning async upload for Run ID: {run_id}")
    task = asyncio.create_task(tools._upload_ledger_to_catbox(run_id, dummy_csv))
    
    # Wait a split second to simulate immediate polling
    await asyncio.sleep(0.1)
    
    # 2. Assert pending status immediately
    url_res = await tools.execute("get_backtest_ledger_url", {"run_id": run_id})
    print(f"Polling Status: {url_res}")
    
    # 3. Wait for upload to finish
    print("Waiting for upload to finish (max 10s)...")
    await asyncio.wait_for(task, timeout=10.0)
    
    url_res = await tools.execute("get_backtest_ledger_url", {"run_id": run_id})
    print(f"Final Status: {url_res}")
    
    if os.path.exists(dummy_csv):
        os.remove(dummy_csv)

if __name__ == "__main__":
    asyncio.run(test_mcp_async_upload())
