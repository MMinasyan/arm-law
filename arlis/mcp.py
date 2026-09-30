"""ARLIS legal research MCP server (stdio)."""
import arlis
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

mcp = MCPServer(
    "arlis",
    instructions=(
        "Legal research tools for arlis.am, the Armenian legal information "
        "system. search_acts finds acts (laws, decisions, orders) by free "
        "text and enactment-date range and returns each act's full title, "
        "URL and available metadata. get_act takes one of those URLs, "
        "saves the act's metadata and full text as markdown to a local "
        ".arlis/<number>.md file and returns the absolute saved path "
        "with a short line-numbered heading structure. Search first, "
        "then pass a returned URL to get_act to read and save the act."
    ),
)


@mcp.tool(description=arlis.search_acts.__doc__, structured_output=False)
def search_acts(search_string: str, data_after: str | None = None,
                date_before: str | None = None, active: bool = True) -> str:
    try:
        return arlis.search_acts(search_string, data_after, date_before, active)
    except Exception as e:
        raise ToolError(str(e)) from e


@mcp.tool(description=arlis.get_act.__doc__, structured_output=False)
def get_act(url: str, output_dir: str | None = None) -> str:
    try:
        return arlis.get_act(url, output_dir)
    except Exception as e:
        raise ToolError(str(e)) from e


if __name__ == "__main__":
    mcp.run()
