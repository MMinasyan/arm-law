"""Agent-facing tools for legal research on arlis.am (Armenian legal
information system).

- search_acts(search_string, ...): find acts by free text and
  enactment-date range; returns titles, URLs and metadata
- get_act(url, output_dir=None): save one act's metadata and full text
  as a local markdown file; returns its path and heading structure
"""
from .act import get_act
from .search import search_acts

__all__ = ["search_acts", "get_act"]
