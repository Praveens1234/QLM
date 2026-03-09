import asyncio
from backend.api.mcp_tools import MCPTools

async def test_guidelines():
    tools = MCPTools()
    res = await tools.execute("get_strategy_coding_guidelines", {})
    if "content" in res:
        print("SUCCESS! Loaded guidelines document.")
        print(f"Length: {len(res['content'])} characters")
        print("First 100 chars:", res['content'][:100])
    else:
        print("FAILED to get content:", res)

if __name__ == "__main__":
    asyncio.run(test_guidelines())
