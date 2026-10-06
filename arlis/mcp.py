"""ARLIS legal research MCP server (stdio)."""
from typing import Annotated

import arlis
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

mcp = MCPServer(
    "arlis",
    instructions=(
        "Legal research tools for arlis.am, the Armenian legal information "
        "system. search_acts finds acts (laws, decisions, orders) by free "
        "text and enactment-date range and returns the latest version only "
        "of up to 20 source entries, newest first by enactment date, with "
        "each act's full title, URL and available metadata. By default "
        "search_acts matches titles only; its optional search_in_text "
        "argument extends the same query to act titles and contents "
        "(titles are still matched, it is not a contents-only mode). "
        "get_act accepts "
        "any valid ARLIS act URL, passed unchanged, and saves the act's "
        "metadata and full text as markdown to "
        "<output_dir>/<numeric URL segment>.md, by default in the .arlis "
        "directory under the server process working directory; output_dir "
        "overrides that destination directory. It returns only the "
        "absolute saved path, the metadata line range and a short "
        "line-numbered heading structure. Use search_acts to discover an "
        "act's URL when you need one; a URL you already have can be passed "
        "directly to get_act. After saving, read the returned file with an "
        "available file-reading tool before using its content."
    ),
)


@mcp.tool(description=arlis.search_acts.__doc__, structured_output=False)
def search_acts(
    search_string: Annotated[
        str,
        Field(description=(
            "Free-text ARLIS query; may be empty when the query is by "
            "enactment date and/or status only. The query text is "
            "normalized (և/եւ/Եւ become ԵՎ) and uppercased "
            "before searching. With search_in_text=False (default) the "
            "query matches act titles only; search_in_text=True matches "
            "act titles and act contents."
        )),
    ],
    data_after: Annotated[
        str | None,
        Field(description=(
            "Optional lower bound on the ENACTMENT date as a real ISO "
            "YYYY-MM-DD date (not the effective, signing or incorporation "
            "date). Omit or null (default) for no lower bound."
        )),
    ] = None,
    date_before: Annotated[
        str | None,
        Field(description=(
            "Optional upper bound on the ENACTMENT date as a real ISO "
            "YYYY-MM-DD date. Omit or null (default) for no upper bound."
        )),
    ] = None,
    active: Annotated[
        bool,
        Field(description=(
            "True (default) restricts results to active and partly active "
            "acts; False removes the status restriction so acts in any "
            "status may be returned, while the text and enactment-date "
            "filters still apply."
        )),
    ] = True,
    search_in_text: Annotated[
        bool,
        Field(description=(
            "False (default) matches the query against act TITLES only. "
            "True extends the same query to act TITLES and act CONTENTS "
            "(body text as well; titles are still matched, it is not a "
            "contents-only mode). The choice has no effect when the "
            "query is empty. Latest-only search, the 20-result bound, "
            "newest-first order and the reply format are unchanged "
            "either way."
        )),
    ] = False,
) -> str:
    try:
        return arlis.search_acts(
            search_string, data_after, date_before, active, search_in_text
        )
    except Exception as e:
        raise ToolError(str(e)) from e


@mcp.tool(description=arlis.get_act.__doc__, structured_output=False)
def get_act(
    url: Annotated[
        str,
        Field(description=(
            "Full HTTPS ARLIS act URL, passed to the server unchanged; "
            "concrete, /latest and fragment forms are all accepted, and "
            "any valid ARLIS act URL works, not only ones returned by "
            "search_acts."
        )),
    ],
    output_dir: Annotated[
        str | None,
        Field(description=(
            "Exact destination directory for the saved markdown file. Omit "
            "or null (default) writes to the .arlis directory under the "
            "server process working directory; a relative path resolves "
            "against that same working directory and an absolute path is "
            "used as given. An empty string is a relative override (the "
            "working directory itself), not the default."
        )),
    ] = None,
) -> str:
    try:
        return arlis.get_act(url, output_dir)
    except Exception as e:
        raise ToolError(str(e)) from e


if __name__ == "__main__":
    mcp.run()
