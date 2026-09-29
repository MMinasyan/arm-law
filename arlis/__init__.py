"""Agent-facing tools for legal research on arlis.am (Armenian legal
information system).

- search_acts(query, ...): find acts by free text and enactment-date range
- get_act(ref): one act's metadata, changes and relations
- get_act_markdown(ref): the same plus the full act text as markdown

`ref` accepts an act URL or the numeric act id.
"""
from .act import get_act, get_act_markdown
from .search import search_acts

__all__ = ["search_acts", "get_act", "get_act_markdown"]
