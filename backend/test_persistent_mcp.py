
import asyncio

from app.integrations.persistent_mcp_client import PersistentMCPClient


async def main():
    client = PersistentMCPClient()

    try:
        await client.start()
        print("1. MCP session started")

        first_navigation = await client.navigate("https://qk.peoplestrong.com/altLogin.jsf")
        print("2. First navigation:", first_navigation["status"])

        if first_navigation["status"] != "success":
            print(first_navigation)
            return

        first_snapshot = await client.snapshot()
        print("3. First snapshot:", first_snapshot["status"])
        print(first_snapshot.get("result", "")[:1000])

        second_navigation = await client.navigate("https://playwright.dev")
        print("4. Second navigation:", second_navigation["status"])

        if second_navigation["status"] != "success":
            print(second_navigation)
            return

        second_snapshot = await client.snapshot()
        print("5. Second snapshot:", second_snapshot["status"])
        print(second_snapshot.get("result", "")[:1000])

    except Exception as error:
        print("MCP test failed:", error)
        raise

    finally:
        await client.close()
        print("6. MCP session closed")


if __name__ == "__main__":
    asyncio.run(main())
