from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tracker", instructions="Tracker MCP server. Use list_projects to discover projects, then list_cards to find work. Claim a card before starting, then post_log and post_milestone as you work.", streamable_http_path="/")

from backend.mcp import tools  # noqa: F401, E402 — registers tools
from backend.mcp import resources  # noqa: F401, E402 — registers resources

mcp_app = mcp.streamable_http_app()
