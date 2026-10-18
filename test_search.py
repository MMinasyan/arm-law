"""Run with python3 -B test_search.py; no network requests."""
import asyncio
import inspect
import json
from unittest.mock import patch
from urllib.parse import unquote

import arlis
from arlis.mcp import mcp, search_acts


def check():
    for options, excluded in (
        ({}, True),
        ({"incorporations_only": True}, True),
        ({"incorporations_only": False}, False),
    ):
        pages = []

        def fetch_page(session, params, page, timeout):
            expected = {
                "simple_text": "ՔԱՂԱՔԱՑԻԱԿԱՆ ՕՐԵՆՍԳԻՐՔ",
                "status": "1,4,5,7,9,12",
                "text_filter": "1",
            }
            if excluded:
                expected["exclude_changing_acts"] = "true"
            assert json.loads(unquote(params)) == expected
            pages.append(page)
            return [
                {"title": f"Act {i}", "url": f"https://www.arlis.am/hy/acts/{i}/latest"}
                for i in range((page - 1) * 10 + 1, min(page * 10, 21) + 1)
            ], 21

        with patch("arlis.search._fetch_page", side_effect=fetch_page):
            result = search_acts("քաղաքացիական օրենսգիրք", **options)
        count = 20
        assert result.startswith(f"Search results ({count}):\n")
        assert pages == list(range(1, (count + 9) // 10 + 1))

    assert inspect.signature(arlis.search_acts).parameters["incorporations_only"].default is True

    async def check_schema():
        tool = next(t for t in await mcp.list_tools() if t.name == "search_acts")
        assert list(tool.input_schema["properties"]) == [
            "search_string", "search_in_text", "active",
            "incorporations_only", "data_after", "date_before",
        ]
        prop = tool.input_schema["properties"]["incorporations_only"]
        assert prop["type"] == "boolean" and prop["default"] is True
        assert "incorporations_only" not in tool.input_schema["required"]
        assert "include_amendments" not in tool.input_schema["properties"]
        assert "exclude_changing_acts" not in tool.input_schema["properties"]

    asyncio.run(check_schema())
    print("PASS: amendment filtering, request encoding, pagination and MCP schema")


if __name__ == "__main__":
    check()
