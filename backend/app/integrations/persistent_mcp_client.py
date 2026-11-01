import logging
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from app.integrations.mcp_client import PLAYWRIGHT_SERVER

logger = logging.getLogger(__name__)


class PersistentMCPClient:

    def __init__(self):
        self._exit_stack = None
        self.session = None

    async def start(self) -> None:

        if self.session is not None:
            raise RuntimeError("MCP client is already running.")

        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()

        try:
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(PLAYWRIGHT_SERVER)
            )

            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            await self.session.initialize()
            logger.info("Persistent Playwright MCP session started.")

        except Exception:
            await self.close()
            raise

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict | None = None,
    ) -> dict:

        if self.session is None:
            raise RuntimeError("Start the MCP client before calling tools.")

        result = await self.session.call_tool(
            tool_name,
            arguments or {},
        )

        response_text = "\n".join(
            item.text for item in result.content if hasattr(item, "text")
        )

        if result.is_error:
            return {
                "status": "error",
                "tool": tool_name,
                "message": response_text or "MCP tool execution failed.",
            }

        return {
            "status": "success",
            "tool": tool_name,
            "result": response_text,
        }

    async def navigate(self, url: str) -> dict:

        if not isinstance(url, str) or not url.strip():
            return {
                "status": "error",
                "message": "A non-empty URL is required.",
            }

        return await self.call_tool(
            "browser_navigate",
            {"url": url.strip()},
        )

    async def snapshot(self) -> dict:

        return await self.call_tool("browser_snapshot")

    async def click(self, target: str, element: str = "") -> dict:

        if not isinstance(target, str) or not target.strip():
            return {
                "status": "error",
                "message": "A target element reference is required.",
            }

        arguments = {"target": target.strip()}

        if element:
            arguments["element"] = element

        return await self.call_tool("browser_click", arguments)

    async def type_text(
        self,
        target: str,
        text: str,
        element: str = "",
    ) -> dict:

        if not isinstance(target, str) or not target.strip():
            return {
                "status": "error",
                "message": "A target element reference is required.",
            }

        arguments = {
            "target": target.strip(),
            "text": text,
        }

        if element:
            arguments["element"] = element

        return await self.call_tool("browser_type", arguments)

    async def close(self) -> None:

        stack = self._exit_stack

        if stack is None:
            return

        self._exit_stack = None
        self.session = None

        await stack.aclose()
        logger.info("Persistent Playwright MCP session closed.")
