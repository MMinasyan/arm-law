"""Read ARLIS acts: fetch once, save metadata plus full text as markdown."""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup
from lxml.html import document_fromstring, tostring

from .client import REQUEST_TIMEOUT, new_session
from .processing import postprocess, preprocess
from .source import _ARLIS_ACT_URL_RE, _parse_act, _to_iso_date
from .html2md import html_to_markdown
from .html_tools import (
    add_lists,
    clean_html,
    clean_html_tables,
    ensure_document,
    merge_same_url_links,
    remove_empty_tags,
)

_ACT_ID_RE = re.compile(r"/acts/([1-9][0-9]*)")

_DATE_FIELDS = (
    "enactment_date", "signing_date",
    "ratification_date", "effective_date", "interrupt_date",
)

_NO_ENTRY = "None listed by ARLIS."

# Short ToC: ATX headings and uppercase lines outside backtick/tilde fences.
# Headings allow up to three leading spaces and optional closing hashes.
# Fences track the opening marker and run length: a fence closes only
# on the same marker with at least the opening run of characters and a
# whitespace-only tail, so shorter runs, the other marker and
# info-string/content lines inside a fence never close it.
_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*))?$")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_FENCE_CLOSE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
_CLOSING_HASHES_RE = re.compile(r"[ \t]+#+[ \t]*$")

_CHANGE_BLOCKS = (
    ("change_history", "changing_act", "Amendments to this act:",
     "Amending act"),
    ("changed_acts", "changed_act", "Acts amended by this act:",
     "Amended act"),
)
_RELATION_BLOCKS = (
    ("general_relations", "General related acts:"),
    ("judicial_precedents", "Judicial precedents relating to this act:"),
    ("official_clarifications", "Official clarifications of this act:"),
    ("anti_constitutional", "Unconstitutionality-related acts:"),
)


def get_act(url: str, output_dir: str | None = None) -> str:
    """Fetch one ARLIS act URL and save it as a local markdown file.

    Writes the act's plain-text metadata followed by its full text as markdown to
    <output_dir>/<numeric URL segment>.md (default directory .arlis under
    PLUGIN_DATA, or the server working directory if PLUGIN_DATA is unset or empty).
    Returns only the absolute saved path, the metadata line range and a short
    line-numbered heading structure.
    """
    if not _ARLIS_ACT_URL_RE.match(url):
        raise ValueError(f"not a valid arlis act URL: {url!r}")
    match = _ACT_ID_RE.search(url)
    assert match is not None  # the ARLIS grammar guarantees the segment
    destination = Path(".arlis" if output_dir is None else output_dir)
    if not destination.is_absolute():
        data_dir = os.environ.get("PLUGIN_DATA")
        if data_dir and not Path(data_dir).is_absolute():
            raise ValueError("PLUGIN_DATA must be an absolute directory path")
        base = Path(data_dir) if data_dir else Path.cwd()
        destination = base / destination
        if not destination.is_absolute():
            # Windows drive-relative inputs resolve against the per-drive cwd.
            destination = Path(os.path.abspath(destination))
    metadata, body = _read_act(url)
    lines = _metadata_lines(metadata)
    structure = _structure_lines(lines, body)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{match.group(1)}.md"
    _save(target, "\n".join(lines) + "\n\n" + body)
    return (
        f"Saved: {target}\n"
        f"Metadata: lines 1–{len(lines)}\n"
        "\n"
        f"Structure:\n{structure}"
    )


def main_process(html: str) -> str:
    """html_tools processing chain for arlis documents."""
    soup = BeautifulSoup(html, "html.parser")
    soup = clean_html(soup)
    soup = add_lists(soup)
    soup = clean_html_tables(soup)
    ensure_document(soup)
    soup = merge_same_url_links(soup)
    remove_empty_tags(soup)
    soup.smooth()
    return tostring(document_fromstring(str(soup)), pretty_print=True, encoding="unicode")


def _read_act(url: str) -> tuple[dict, str]:
    """Fetch one act once: its serialized metadata and markdown body."""
    record = _fetch_record(url)
    if not record["full_html"]:
        raise ValueError("presence: 'full_html' must be non-empty")
    body = html_to_markdown(postprocess(main_process(preprocess(record))))
    return _serialize(record), body


def _fetch_record(url: str) -> dict:
    """Fetch the supplied URL unchanged; pass its requested act ID.

    The requested ID is the URL's positive numeric path segment for
    every accepted form — the /latest suffix changes nothing, there is
    no suffix dispatch and the ID is never None. The act-family
    identity check itself lives in _parse_act.
    """
    match = _ACT_ID_RE.search(url)
    assert match is not None  # the ARLIS grammar guarantees the segment
    requested_id = int(match.group(1))
    response = new_session().get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return _parse_act(response.text, requested_id, url)


def _serialize(record: dict) -> dict:
    """Plain metadata: drop id/full HTML, ISO dates.

    Change and relation URLs are kept exactly as the source parser
    produced them (path, /latest suffix and fragment intact).
    """
    out = {k: v for k, v in record.items() if k not in ("id", "full_html")}
    for key in _DATE_FIELDS:
        if out.get(key):
            out[key] = _to_iso_date(out[key])
    return out


def _metadata_lines(record: dict) -> list[str]:
    """Plain `key: value` scalars plus labelled relationship blocks."""
    lines: list[str] = []
    for key, value in record.items():
        if key in ("changes", "relations"):
            continue
        lines.append(f"{key}: {' '.join(str(value).split())}")
    changes = record["changes"]
    for key, act_key, label, role in _CHANGE_BLOCKS:
        entries = changes[key]
        if not entries:
            lines.append(f"{label} {_NO_ENTRY}")
            continue
        lines.append(label)
        for entry in entries:
            lines.append(f"- {role}: {entry[act_key]}")
            version = entry.get("incorporation")
            if version:
                lines.append(
                    f"  Incorporated version after this amendment: {version}"
                )
    relations = record["relations"]
    for key, label in _RELATION_BLOCKS:
        urls = relations[key]
        if not urls:
            lines.append(f"{label} {_NO_ENTRY}")
            continue
        lines.append(label)
        lines.extend(f"- {url}" for url in urls)
    return lines


def _structure_lines(metadata_lines: list[str], body: str) -> str:
    """The two shallowest heading levels plus uppercase lines, in file order."""
    headings: list[tuple[int, int | None, str]] = []
    fence: tuple[str, int] | None = None
    for lineno, line in enumerate(body.split("\n"), start=1):
        if fence is None:
            open_match = _FENCE_RE.match(line)
            if open_match:
                run = open_match.group(1)
                fence = (run[0], len(run))
                continue
        else:
            close_match = _FENCE_CLOSE_RE.match(line)
            if (close_match
                    and close_match.group(1)[0] == fence[0]
                    and len(close_match.group(1)) >= fence[1]):
                fence = None
            continue
        match = _HEADING_RE.match(line)
        if match:
            title = _CLOSING_HASHES_RE.sub("", match.group(2) or "").strip()
            headings.append((lineno, len(match.group(1)), title))
        elif line.isupper():
            headings.append((lineno, None, line.strip()))
    if not headings:
        return "No top-level headings."
    levels = sorted({level for _, level, _ in headings if level is not None})
    keep = set(levels[:2])
    offset = len(metadata_lines) + 1
    return "\n".join(
        title if level is None else f"{title}: line {offset + lineno}"
        for lineno, level, title in headings
        if level in keep or title.isupper()
    )


def _save(target: Path, text: str) -> None:
    """Atomically publish text as UTF-8 bytes at target.

    A unique temporary sibling in the destination is closed before
    os.replace; an unpublished temporary file is removed on failure so
    a previous complete file survives every failed publication.
    """
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=target.parent, delete=False) as handle:
            temp_name = handle.name
            handle.write(text.encode("utf-8"))
        os.replace(temp_name, target)
    except BaseException:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
        raise
