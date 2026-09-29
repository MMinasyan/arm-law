"""HTTP session construction and the act URL/id grammar for arlis.am."""
from __future__ import annotations

import re

import requests

from .source import BASE_URL, _ARLIS_ACT_URL_RE, _USER_AGENT

REQUEST_TIMEOUT = 30.0

_DIGITS_RE = re.compile(r"^[1-9][0-9]*$")
_ACT_ID_RE = re.compile(r"/acts/([1-9][0-9]*)")


def new_session() -> requests.Session:
    """Fresh per-call session with the vendored UA header.

    No warm-up, no retry, no shared state: transport errors propagate to
    the caller on first occurrence.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": _USER_AGENT})
    return session


def normalize_act_url(ref: str | int) -> str:
    """One string-form rule: ref -> act id -> direct URL.

    Digit strings and ints resolve to the act id's own page; URL inputs
    drop /latest and fragments (the site serves a different act's page for
    /latest on superseded acts, which the page-identity validation
    rejects). Everything else fails with one uniform error.
    """
    value = str(ref).strip()
    if _DIGITS_RE.fullmatch(value):
        return f"{BASE_URL}/hy/acts/{value}"
    if _ARLIS_ACT_URL_RE.match(value):
        match = _ACT_ID_RE.search(value)
        assert match is not None  # the vendored grammar guarantees the id
        return f"{BASE_URL}/hy/acts/{match.group(1)}"
    raise ValueError(f"not a valid arlis act URL or id: {ref!r}")
