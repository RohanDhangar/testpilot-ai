import asyncio
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(level=logging.INFO)

PLAYWRIGHT_SERVER = StdioServerParameters(
    command="npx",
    args=["-y", "@playwright/mcp@latest"],
)

async def explore_application(url: str) -> dict:
    if not isinstance(url, str) or not url.strip():
        return {
            "status":"error",
            "message":"Invalid URL provided. Please provide a non-empty string."
        }

    try:
        async with stdio_client(PLAYWRIGHT_SERVER) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
        
                    navigation = await session.call_tool("browser_navigate", {"url": url.strip()})
        
                    if navigation.is_error:
                        return {
                            "status": "error",
                            "message": "Navigation is failed",
                            "details": [getattr(item, "test", str(item)) for item in navigation.content]
                        }
        
                    snapshot = await session.call_tool("browser_snapshot", {})
        
                    if snapshot.is_error:
                        return {
                            "status": "error",
                            "message": "Browser snapshot failed",
                            "details": [getattr(item, "text", str(item)) for item in snapshot.content]
                        }
        
                    snapshot_text = "\n".join([getattr(item, "text", str(item)) for item in snapshot.content])
        
                    logging.info("Application navigation and snapshot completed.") 
        
                    return {
                        "status": "success", 
                        "url": url.strip(), 
                        "snapshot": snapshot_text
                    }
    except Exception:
        logging.exception("Application exploration failed.")
        return {"status": "error", "message": "Application exploration failed. Check the logs."}
    
async def main():
    target_url = input("Enter your URL").strip()
    result = await explore_application(target_url)
    print(result)


# async def discover_tools():
#     async with stdio_client(PLAYWRIGHT_SERVER) as (read, write):
#         async with ClientSession(read, write) as session:
#             await session.initialize()

#             response = await session.list_tools()

#             print("\n Available Playwright tools are : \n")

#             for tool in response.tools:
#                 print(f" Name : {tool.name}")
#                 print(f" description: {tool.description}")
#                 print(f" schema: {tool.input_schema}")
#                 print("-"*50)

if __name__ == "__main__":
    asyncio.run(main())