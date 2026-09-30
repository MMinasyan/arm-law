"""HTTP session construction for arlis.am."""
from __future__ import annotations

import requests

from .source import _USER_AGENT

REQUEST_TIMEOUT = 30.0


def new_session() -> requests.Session:
    """Fresh per-call session with the vendored UA header.

    No warm-up, no retry, no shared state: transport errors propagate to
    the caller on first occurrence.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": _USER_AGENT})
    return session
