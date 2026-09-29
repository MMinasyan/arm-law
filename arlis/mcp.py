"""ARLIS legal research MCP server (stdio)."""
import arlis
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

mcp = MCPServer(
    "arlis",
    instructions=(
        "Legal research tools for arlis.am, the Armenian legal information "
        "system. search_acts finds acts (laws, decisions, orders) by free "
        "text and enactment-date range; get_act returns one act's metadata, "
        "changes and relations; get_act_markdown also converts the full act "
        "text to markdown. Act arguments accept either an act URL or the "
        "numeric act id. Search before reading: search_acts returns the "
        "ids and titles that get_act / get_act_markdown accept."
    ),
)


@mcp.tool(description=arlis.search_acts.__doc__)
def search_acts(query: str = "", enacted_after: str | None = None,
               enacted_before: str | None = None, limit: int = 20) -> list[dict]:
    try:
        return arlis.search_acts(query=query, enacted_after=enacted_after,
                                 enacted_before=enacted_before, limit=limit)
    except Exception as e:
        raise ToolError(str(e)) from e


@mcp.tool(description=arlis.get_act.__doc__)
def get_act(ref: str | int) -> dict:
    try:
        return arlis.get_act(ref)
    except Exception as e:
        raise ToolError(str(e)) from e


@mcp.tool(description=arlis.get_act_markdown.__doc__)
def get_act_markdown(ref: str | int) -> dict:
    try:
        return arlis.get_act_markdown(ref)
    except Exception as e:
        raise ToolError(str(e)) from e


if __name__ == "__main__":
    mcp.run()
