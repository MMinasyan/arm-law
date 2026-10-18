"""ARLIS legal research MCP server (stdio)."""
from typing import Annotated

import arlis
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

mcp = MCPServer("arlis")


@mcp.tool(description=arlis.search_acts.__doc__, structured_output=False)
def search_acts(
    search_string: Annotated[
        str,
        Field(description=(
            "Exact string to match inside act titles or, if search_in_text is true, "
            "also inside their contents. Case-insensitive; և/եւ/Եւ/ԵՎ normalized."
        )),
    ],
    search_in_text: Annotated[
        bool,
        Field(description=(
            "False (default): search for matches in act TITLES only. "
            "Use true to also search act CONTENTS."
        )),
    ] = False,
    active: Annotated[
        bool,
        Field(description=(
            "True (default): search active or partly active acts only. "
            "Use false to include all statuses."
        )),
    ] = True,
    incorporations_only: Annotated[
        bool,
        Field(description=(
            "True (default): search only incorporations with all amendments included. "
            "Use false to also search amendment acts."
        )),
    ] = True,
    data_after: Annotated[
        str | None,
        Field(description=(
            "Null (default): no lower bound. "
            "Use YYYY-MM-DD to set the earliest ENACTMENT date."
        )),
    ] = None,
    date_before: Annotated[
        str | None,
        Field(description=(
            "Null (default): no upper bound. "
            "Use YYYY-MM-DD to set the latest ENACTMENT date."
        )),
    ] = None,
) -> str:
    try:
        return arlis.search_acts(
            search_string, data_after, date_before, active, search_in_text,
            incorporations_only,
        )
    except Exception as e:
        raise ToolError(str(e)) from e


@mcp.tool(description=arlis.get_act.__doc__, structured_output=False)
def get_act(
    url: Annotated[
        str,
        Field(description="ARLIS act url to save"),
    ],
    output_dir: Annotated[
        str | None,
        Field(description=(
            "Destination directory where the act’s Markdown file will be saved. "
            "Omit this parameter to use .arlis under the MCP server’s working directory."
        )),
    ] = None,
) -> str:
    try:
        return arlis.get_act(url, output_dir)
    except Exception as e:
        raise ToolError(str(e)) from e


if __name__ == "__main__":
    mcp.run()
