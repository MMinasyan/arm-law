"""Search acts on arlis.am via the vendored search helpers."""
from __future__ import annotations

from datetime import datetime

from .client import REQUEST_TIMEOUT, new_session, normalize_act_url
from .source import _PAGE_SIZE, _build_params, _fetch_page, _to_iso_date

_DATE_KEYS = ("enactment_date", "effective_date")


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
    query: str = "",
    enacted_after: str | None = None,
    enacted_before: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Find acts on arlis.am by free text and/or enactment-date range.

    Use it to find acts by free-text query and/or enactment-date range;
    each returned card's id/url feeds the read tools' ref. Cards are
    bounded by limit, newest first by enactment date; each card is
    {"id", "url" (direct form), "title", "number"?, "enactment_date"
    (ISO)?, "effective_date" (ISO)?, "status"?}.
    """
    if not (isinstance(limit, int) and limit > 0):
        raise ValueError(f"limit must be a positive int, got {limit!r}")
    if enacted_after is not None:
        _check_iso_date(enacted_after, "enacted_after")
    if enacted_before is not None:
        _check_iso_date(enacted_before, "enacted_before")

    filters: dict = {}
    if query:
        filters["simple_text"] = query
    if enacted_after is not None or enacted_before is not None:
        filters["enactment_date"] = {
            "start": enacted_after or "",
            "end": enacted_before or "",
        }
    params = _build_params(filters)

    session = new_session()
    results: list[dict] = []
    page = 1
    while True:
        cards, total = _fetch_page(session, params, page, REQUEST_TIMEOUT, "DESC")
        results.extend(_clean_card(card) for card in cards)
        if len(results) >= limit:
            break
        if total is None or page * _PAGE_SIZE >= total:
            break
        page += 1
    return results[:limit]


def _clean_card(card: dict) -> dict:
    """Card with ISO dates, direct-form url, no scrape-moment fields.

    A date field is absent when the card's about-item is missing or its
    value is empty (undated acts are a normal site state).
    """
    out = {k: v for k, v in card.items() if k != "discovered"}
    out["url"] = normalize_act_url(out["id"])
    for key in _DATE_KEYS:
        value = out.get(key)
        if value:
            out[key] = _to_iso_date(value)
        else:
            out.pop(key, None)
    return out
