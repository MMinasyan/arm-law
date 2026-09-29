"""Read ARLIS acts: metadata, changes, relations, and full text as markdown."""
from __future__ import annotations

import re

from lxml.html import document_fromstring, tostring

from .client import REQUEST_TIMEOUT, new_session, normalize_act_url
from .processing import postprocess, preprocess
from .source import _parse_act, _to_iso_date
from .html2md import html_to_markdown
from .html_tools import (
    add_lists,
    add_style_tag,
    clean_html,
    clean_html_tables,
    merge_same_url_links,
    remove_empty_tags,
    to_soup,
)

_ACT_ID_RE = re.compile(r"/acts/([1-9][0-9]*)")

_DATE_FIELDS = (
    "enactment_date", "signing_date",
    "ratification_date", "effective_date", "interrupt_date",
)

_URL_ENTRY_KEYS = ("changing_act", "changed_act", "incorporation")


def get_act(ref: str | int) -> dict:
    """Fetch one act and return its metadata, changes and relations.

    Use it for an act's identity and metadata and its change and relation
    links - which acts modify it, and its judicial precedents and
    official clarifications. To read the act's full text, use
    get_act_markdown.
    """
    return _serialize(_fetch_record(ref))


def get_act_markdown(ref: str | int) -> dict:
    """Fetch one act and return its metadata plus the full text as markdown.

    Use it to read the act's full text as markdown; for metadata only,
    get_act avoids the conversion.
    """
    record = _fetch_record(ref)
    if not record["full_html"]:
        raise ValueError("presence: 'full_html' must be non-empty")
    result = _serialize(record)
    result["markdown"] = html_to_markdown(postprocess(main_process(preprocess(record))))
    return result


def main_process(html: str) -> str:
    """Generic html_tools processing chain for arlis documents."""
    soup = to_soup(html=html)
    soup = clean_html(soup, base_url="https://www.arlis.am/")
    soup = add_lists(soup, source="arlis", trailing_multiplier=2)
    soup = clean_html_tables(soup)
    add_style_tag(soup)
    soup = merge_same_url_links(soup)
    remove_empty_tags(soup)
    soup.smooth()
    return tostring(document_fromstring(str(soup)), pretty_print=True, encoding="unicode")


def _fetch_record(ref: str | int) -> dict:
    url = normalize_act_url(ref)
    match = _ACT_ID_RE.search(url)
    assert match is not None  # the direct URL always carries the id
    act_id = int(match.group(1))
    response = new_session().get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return _parse_act(response.text, act_id, url)


def _serialize(record: dict) -> dict:
    """New dict: drop full_html/extracted, ISO dates, direct-form URLs."""
    out = {k: v for k, v in record.items() if k not in ("full_html", "extracted")}
    for key in _DATE_FIELDS:
        if out.get(key):
            out[key] = _to_iso_date(out[key])
    if "changes" in out:
        src = out["changes"]
        out["changes"] = {
            "main_act": normalize_act_url(src["main_act"]),
            "change_history": [
                {k: (normalize_act_url(v) if k in _URL_ENTRY_KEYS else v)
                 for k, v in entry.items()}
                for entry in src.get("change_history", ())
            ],
            "changed_acts": [
                {k: (normalize_act_url(v) if k in _URL_ENTRY_KEYS else v)
                 for k, v in entry.items()}
                for entry in src.get("changed_acts", ())
            ],
        }
    if "relations" in out:
        out["relations"] = {
            key: [normalize_act_url(u) for u in urls]
            for key, urls in out["relations"].items()
        }
    return out
