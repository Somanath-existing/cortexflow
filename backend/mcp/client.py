import httpx
from backend.core.config import settings


class MCPClientManager:
    """
    Manages communication with all MCP servers.
    Each server is a separate process/container.
    """

    def __init__(self):
        self.servers = {
            "database": settings.mcp_database_url,
            "knowledge": settings.mcp_knowledge_url,
            "analytics": settings.mcp_analytics_url
        }

    async def call_tool(
        self,
        server: str,
        tool_name: str,
        arguments: dict
    ) -> str:
        url = self.servers.get(server)
        if not url:
            raise ValueError(f"Unknown MCP server: {server}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{url}/tools/call",
                json={"name": tool_name, "arguments": arguments}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("content", [{}])[0].get("text", "")

    async def list_tools(self, server: str) -> list[dict]:
        url = self.servers.get(server)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{url}/tools/list")
            return response.json().get("tools", [])


mcp_client = MCPClientManager()
