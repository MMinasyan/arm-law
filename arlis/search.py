"""Search acts on arlis.am via the vendored search helpers."""
from __future__ import annotations

from datetime import datetime
import re

from .client import REQUEST_TIMEOUT, new_session
from .source import _PAGE_SIZE, _build_params, _fetch_page, _to_iso_date

_DATE_KEYS = ("enactment_date", "effective_date")

_ACTIVE_STATUSES = "1,4,5,7,9,12"

# ponytail: title fallback for amendments misclassified by ARLIS; use native metadata if exposed.
_AMENDMENT_TITLE_RE = re.compile(
    r"(?:ՓՈՓՈԽՈՒԹՅՈՒՆ(?:ՆԵՐ)?|ԼՐԱՑՈՒՄ(?:ՆԵՐ)?)\s+ԿԱՏԱՐԵԼՈՒ\s+ՄԱՍԻՆ[»\".։\s]*$"
)

_METADATA_LABELS = (
    ("number", "Number"),
    ("enactment_date", "Enactment date"),
    ("effective_date", "Effective date"),
    ("status", "Status"),
)


def _check_iso_date(value: object, arg: str) -> None:
    ok = isinstance(value, str)
    if ok:
        try:
            ok = datetime.strptime(value, "%Y-%m-%d").date().isoformat() == value
        except ValueError:
            ok = False
    if not ok:
        raise ValueError(f"{arg} must be an ISO YYYY-MM-DD date, got {value!r}")


def search_acts(
    search_string: str,
    data_after: str | None = None,
    date_before: str | None = None,
    active: bool = True,
    search_in_text: bool = False,
    incorporations_only: bool = True,
    limit: int = 5,
) -> str:
    """Search ARLIS for acts and return their titles, URLs and metadata.
    Latest versions only, in ARLIS's default order. Use get_act to
    retrieve the text.
    Use only the search_string parameter; others default to what you will
    need in 99% of cases. Don't use optional parameters without a reason.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError(f"limit must be a positive integer, got {limit!r}")
    simple_text = (
        search_string.replace("և", "ԵՎ")
        .replace("եւ", "ԵՎ")
        .replace("Եւ", "ԵՎ")
        .upper()
    )
    if data_after is not None:
        _check_iso_date(data_after, "data_after")
    if date_before is not None:
        _check_iso_date(date_before, "date_before")

    filters: dict = {
        "simple_text": simple_text,
        "exclude_changing_acts": incorporations_only,
    }
    if data_after is not None or date_before is not None:
        filters["enactment_date"] = {
            "start": data_after or "",
            "end": date_before or "",
        }
    if active:
        filters["status"] = _ACTIVE_STATUSES
    filters["text_filter"] = "2" if search_in_text else "1"
    params = _build_params(filters)

    session = new_session()
    results: list[dict] = []
    page = 1
    while True:
        cards, total = _fetch_page(session, params, page, REQUEST_TIMEOUT)
        results.extend(
            _clean_card(card) for card in cards
            if not incorporations_only or not _AMENDMENT_TITLE_RE.search(card["title"].upper())
        )
        if len(results) >= limit:
            break
        if total is None or page * _PAGE_SIZE >= total:
            break
        page += 1
    return _render_results(results[:limit])


def _render_results(results: list[dict]) -> str:
    """Numbered plain-text entries; no IDs, no JSON wrapper."""
    if not results:
        return "No acts found."
    entries = []
    for number, card in enumerate(results, start=1):
        lines = [f"{number}. {card['title']}", f"URL: {card['url']}"]
        for key, label in _METADATA_LABELS:
            value = card.get(key)
            if value:
                lines.append(f"{label}: {value}")
        entries.append("\n".join(lines))
    return f"Search results ({len(results)}):\n\n" + "\n\n".join(entries)


def _clean_card(card: dict) -> dict:
    """Card with ISO dates; the URL is kept exactly as the source parser
    returned it, including /latest and fragments. A date field is absent
    when the card's about-item is missing or its value is empty (undated
    acts are a normal site state).
    """
    out = dict(card)
    for key in _DATE_KEYS:
        value = out.get(key)
        if value:
            out[key] = _to_iso_date(value)
        else:
            out.pop(key, None)
    return out
