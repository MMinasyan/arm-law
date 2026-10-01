from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

_PAGE_SIZE = 10
BASE_URL = "https://www.arlis.am"

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_SEARCH_HEADERS = {
    "Referer": f"{BASE_URL}/hy/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

# Strict ARLIS act URL validation: HTTPS, arlis.am host, /hy/acts/{id} path, no leading zero
# Optional fragment must be non-empty; empty '#' is rejected
_ARLIS_ACT_URL_RE = re.compile(
    r"^https://(www\.)?arlis\.am/hy/acts/[1-9][0-9]*(?:/latest)?(?:#[^\s]+)?$"
)

# Designated complete action grammars for page identity validation.
# These use full-match semantics, rejecting arbitrary /acts/{id} substrings
# from external or malformed URLs.

# Share data-url must be a valid full ARLIS act URL (captures ID in group 2).
_SHARE_IDENTITY_RE = re.compile(
    r"^https://(www\.)?arlis\.am/hy/acts/([1-9][0-9]*)(?:/latest)?(?:#[^\s]+)?$"
)

# Download onclick: full-match after whitespace normalization.
# Matches location.href='...' or location.href="..." with SAME quote via backreference,
# /hy/acts/{id}/download/{action}, optional trailing semicolon and whitespace.
# Group 1 = quote char, group 2 = ID.
_DOWNLOAD_IDENTITY_RE = re.compile(
    r"^location\.href=([\"'])/hy/acts/([1-9][0-9]*)/download/(?:act|act_changes)\1;?\s*$"
)

# Print href: full-match /hy/acts/{id}/print/{action}. Captures ID in group 1.
_PRINT_IDENTITY_RE = re.compile(
    r"^/hy/acts/([1-9][0-9]*)/print/(?:act|act_changes)$"
)

# Relative act-link grammar for raw href validation before urljoin.
# Requires /hy/ prefix, positive ID, optional /latest, non-empty fragment.
# Rejects empty fragment, dot segments, protocol-relative/external/malformed links.
_ARLIS_RELATIVE_LINK_RE = re.compile(
    r"^/hy/acts/[1-9][0-9]*(?:/latest)?(?:#[^\s]+)?$"
)


def _normalize_act_link(href: str | None) -> str | None:
    """Validate a raw act link and return canonical absolute URL.

    Full-matches the strict absolute or relative grammar BEFORE urljoin.
    Rejects empty fragments, dot segments, protocol-relative/external/malformed
    links. Converts valid relative links to canonical https://www.arlis.am form.
    """
    if href is None:
        return None
    if href == "":
        raise ValueError("malformed act link: ''")
    # Try absolute grammar first
    if _ARLIS_ACT_URL_RE.match(href):
        return href
    # Try relative grammar, then convert to absolute
    if _ARLIS_RELATIVE_LINK_RE.match(href):
        return f"{BASE_URL}{href}"
    raise ValueError(f"malformed act link: {href!r}")


def _act_link_id(url: str) -> int:
    """The positive numeric act segment of a normalized act link."""
    match = re.search(r"/acts/([1-9][0-9]*)", url)
    assert match is not None  # _normalize_act_link's grammar guarantees it
    return int(match.group(1))


_RESULT_COUNT_RE = re.compile(r'result_count.*?\$\{(\d+)\}')
_CARD_LABELS = {
    "Ակտի համար`": "number",
    "Ընդունման ամսաթիվ`": "enactment_date",
    "Ուժի մեջ մտնելու ամսաթիվ`": "effective_date",
    "Կարգավիճակ`": "status",
}

_ACT_INFO_LABELS = {
    "Համար": "number",
    "Տիպ": "type",
    "Փաստաթղթի տեսակ": "act_type",
    "Կարգավիճակ": "status",
    "Սկզբնաղբյուր": "arlis_source",
    "Ընդունող մարմին": "enactment_organisation",
    "Ընդունման ամսաթիվ": "enactment_date",
    "Ընդունման վայր": "enactment_location",
    "Ստորագրող մարմին": "signing_organisation",
    "Ստորագրման ամսաթիվ": "signing_date",
    "Վավերացնող մարմին": "ratification_organisation",
    "Վավերացման ամսաթիվ": "ratification_date",
    "Ուժի մեջ մտնելու ամսաթիվ": "effective_date",
    "Ուժը կորցրել է": "interrupt_date",
}

_RELATIONS_LABELS = {
    "Ընդհանուր կապեր": "general_relations",
    "Դատական նախադեպեր": "judicial_precedents",
    "Պաշտոնական պարզաբանումներ": "official_clarifications",
    "Հակասահմանադրական կապեր": "anti_constitutional",
}

# --- tab structure constants ---

_ACT_TAB_LABELS = [
    "Ակտի վավերապայմաններ",
    "ՓՈՓՈԽՈՂՆԵՐ ԵՎ ԻՆԿՈՐՊՈՐԱՑԻԱՆԵՐ",
    "Կապեր",
]

_CHANGE_SUBTAB_LABELS = [
    "Փոփոխման պատմություն",
    "Փոփոխվող ակտ",
]

_CHANGE_HEADING_FIRST_SPANS = [
    "Փոփոխող ակտ",
    "Փոփոխություններ է կատարել հետևյալ ակտերում",
]

_CHANGE_HEADING_SECOND_SPANS = [
    "Ինկորպորացիա",
    "Յուրաքանչյուր փոփոխվողին համապատասխանող ինկորպորացիան",
]

_RELATION_SUBTAB_LABELS = [
    "Ընդհանուր կապեր",
    "Դատական նախադեպեր",
    "Պաշտոնական պարզաբանումներ",
    "Հակասահմանադրական կապեր",
]


# --- page structure node bundle ---

from dataclasses import dataclass


@dataclass(frozen=True)
class _PageStructure:
    """Validated BeautifulSoup nodes returned by structure validation.

    Parsers receive these nodes and must not rediscover broader nodes.
    `change_anchors` holds one list of couple-anchor lists per change
    container; `relation_anchors` holds one anchor list per relation
    container; `primary_id` is the act ID declared by the page's unique
    primary act link.
    """
    tab_containers: list
    change_anchors: list
    relation_anchors: list
    relation_labels: list
    primary_id: int


# --- discovery helpers ---


def _build_params(filters: dict) -> str:
    """Encode the search request params used by search_acts.

    `enactment_date` is the only dict field and is JSON-stringified;
    `simple_text` and `status` pass through. `include_old_versions` is
    deliberately omitted for latest-only search: sending it (even as a
    raw "false" string) re-enables old versions on the site.
    """
    params: dict = {"simple_text": filters.get("simple_text", "")}
    if "enactment_date" in filters:
        params["enactment_date"] = json.dumps(filters["enactment_date"])
    if "status" in filters:
        params["status"] = filters["status"]
    return quote(json.dumps(params))


def _parse_card(card) -> dict:
    """Parse a discovery card with strict anchor cardinality.

    Requires exactly one a[href] in the card. Zero or multiple anchors
    fail, even if one candidate is valid. A non-anchor div[href] does not
    count as an anchor. The single raw href is normalized through the
    shared normalizer.
    """
    # Find all anchor tags with href attribute
    anchors = card.find_all("a", href=True)

    if len(anchors) != 1:
        raise ValueError(
            f"act card must have exactly one a[href], found {len(anchors)}"
        )

    # Normalize the single anchor's href through the shared normalizer
    try:
        normalized = _normalize_act_link(anchors[0]["href"])
    except ValueError as e:
        raise ValueError(f"act card link: {e}") from e

    # Extract ID from normalized URL
    match = re.search(r"/acts/([1-9][0-9]*)", normalized)
    if not match:
        raise ValueError(f"act card link has unparseable href: {anchors[0]['href']!r}")
    act_id = int(match.group(1))

    title_span = card.select_one("span.text-content")
    title = title_span.get_text(strip=True) if title_span else ""

    info: dict = {
        "id": act_id,
        "url": normalized,
        "title": title,
    }

    for item in card.find_all("div", class_="act-card__about-item"):
        label_div = item.select_one(".act-card__about-title")
        value_div = item.select_one(".act-card__about-value") or item.select_one(".act-card__status")
        if not label_div or not value_div:
            continue
        label = label_div.get_text(strip=True)
        value = value_div.get_text(strip=True)
        key = _CARD_LABELS.get(label)
        if key:
            info[key] = value

    return info


def _extract_result_count(html: str) -> int | None:
    match = _RESULT_COUNT_RE.search(html)
    if not match:
        return None
    return int(match.group(1))


def _fetch_page(
    session: requests.Session,
    params: str,
    page: int,
    request_timeout: float,
) -> tuple[list[dict], int | None]:
    url = f"{BASE_URL}/hy/search/page/{page}?{params}&order_by=enactment_date DESC"
    response = session.get(url, headers=_SEARCH_HEADERS, timeout=request_timeout)
    response.raise_for_status()
    data = response.json()
    if data.get("status") != 0:
        raise ValueError(
            f"page {page}: application error: status={data.get('status')!r} message={data.get('message')!r}"
        )
    html = data.get("html", "")
    if not html:
        raise ValueError(f"page {page}: empty html with status 0")
    total = _extract_result_count(html)
    soup = BeautifulSoup(html, "lxml")
    cards = soup.find_all("div", class_="act-card")
    return [_parse_card(card) for card in cards], total
def _to_iso_date(ddmmyyyy: str) -> str:
    return datetime.strptime(ddmmyyyy, "%d.%m.%Y").strftime("%Y-%m-%d")
# --- act page parsing helpers ---


def _parse_validity(container) -> dict:
    result: dict = {}
    for item in container.select(".act-info__item"):
        label_div = item.select_one(".act-info__label")
        value_div = item.select_one(".act-info__value")
        if not label_div or not value_div:
            continue
        label = label_div.get_text(strip=True)
        key = _ACT_INFO_LABELS.get(label)
        if not key:
            continue
        value = value_div.get_text(strip=True)
        result[key] = value
    return result


def _parse_changes(structure: _PageStructure) -> dict:
    """Parse changes from the validated couple anchors in the bundle.

    Each couple contributes its required first-act anchor and, when a
    second anchor exists, its incorporation anchor.
    """
    history: list[dict] = []
    for couple_anchors in structure.change_anchors[0]:
        entry: dict = {"changing_act": _normalize_act_link(couple_anchors[0]["href"])}
        if len(couple_anchors) >= 2:
            entry["incorporation"] = _normalize_act_link(couple_anchors[1]["href"])
        history.append(entry)

    modified: list[dict] = []
    for couple_anchors in structure.change_anchors[1]:
        entry = {"changed_act": _normalize_act_link(couple_anchors[0]["href"])}
        if len(couple_anchors) >= 2:
            entry["incorporation"] = _normalize_act_link(couple_anchors[1]["href"])
        modified.append(entry)

    return {"change_history": history, "changed_acts": modified}


def _parse_connections(structure: _PageStructure) -> dict:
    """Parse connections from the validated anchors in the bundle.

    Consumes only pre-validated anchors; does not rediscover any nodes.
    """
    labels = structure.relation_labels

    result: dict = {}
    for label, anchors in zip(labels, structure.relation_anchors):
        key = _RELATIONS_LABELS.get(label)
        if not key:
            continue
        result[key] = [_normalize_act_link(anchor["href"]) for anchor in anchors]
    return result


def _validate_page_identity(soup) -> int:
    """Validate page-owned identity evidence and return the served act ID.

    Requires exactly one #share-act, one #download-act, one #print-act modal.
    Share group is every a[data-sharer] inside #share-act; each must have
    data-url full-matching strict share grammar. Download group is every
    a[onclick] inside #download-act; each onclick must full-match the exact
    planned location.href expression with SAME opening/closing quote.
    Print group is every a[href] inside #print-act; each must full-match
    exact relative print grammar. Each group non-empty. All IDs agree.
    The requested-versus-served family check runs in _parse_act against
    the page's validated act-family evidence; there is no requested-ID
    comparison here and no URL-form exemption.
    """
    # Require exactly one of each modal
    share_modals = soup.select("#share-act")
    if len(share_modals) != 1:
        raise ValueError(
            f"page identity: expected exactly one #share-act, "
            f"found {len(share_modals)}"
        )
    download_modals = soup.select("#download-act")
    if len(download_modals) != 1:
        raise ValueError(
            f"page identity: expected exactly one #download-act, "
            f"found {len(download_modals)}"
        )
    print_modals = soup.select("#print-act")
    if len(print_modals) != 1:
        raise ValueError(
            f"page identity: expected exactly one #print-act, "
            f"found {len(print_modals)}"
        )

    found_ids: set[int] = set()

    # Share: every a[data-sharer] inside #share-act; each must have data-url
    share_links = share_modals[0].select("a[data-sharer]")
    if not share_links:
        raise ValueError("page identity: missing share identity evidence")
    for link in share_links:
        url = link.get("data-url")
        if url is None:
            raise ValueError(
                "page identity: share anchor missing required data-url"
            )
        match = _SHARE_IDENTITY_RE.match(url)
        if not match:
            raise ValueError(
                f"page identity: malformed share data-url: {url!r}"
            )
        found_ids.add(int(match.group(2)))

    # Download: every a[onclick] inside #download-act
    download_links = download_modals[0].select("a[onclick]")
    if not download_links:
        raise ValueError("page identity: missing download identity evidence")
    for link in download_links:
        onclick = link.get("onclick", "")
        normalized = " ".join(onclick.split())
        match = _DOWNLOAD_IDENTITY_RE.match(normalized)
        if not match:
            raise ValueError(
                f"page identity: malformed download onclick: {onclick!r}"
            )
        # group(2) is the ID from the backreference-aware regex
        found_ids.add(int(match.group(2)))

    # Print: every a[href] inside #print-act
    print_links = print_modals[0].select("a[href]")
    if not print_links:
        raise ValueError("page identity: missing print identity evidence")
    for link in print_links:
        href = link.get("href", "")
        match = _PRINT_IDENTITY_RE.match(href)
        if not match:
            raise ValueError(
                f"page identity: malformed print href: {href!r}"
            )
        found_ids.add(int(match.group(1)))

    if len(found_ids) > 1:
        raise ValueError(
            f"page identity conflict: multiple IDs found {sorted(found_ids)}"
        )
    return next(iter(found_ids))


def _validate_change_couples_exact(couples_wrapper, role: str) -> list[list]:
    """Validate change history/changed acts couples using exact validated node.

    Returns one anchor list per couple, in document order: the required
    first item's anchor plus the second item's anchor when the second
    item has one (the "---------" marker shape contributes no anchor).

    Receives the exact direct couples wrapper node identified during
    structure validation — never re-selects or re-discovers nodes.

    Each couple must have exactly 1 or 2 items (changed_act + optional
    incorporation). A couple with 0 items or 3+ items is malformed.
    The required first item must contain exactly one a[href].
    The optional second item must contain exactly one a[href], or exactly
    one direct span whose normalized text is "---------" with no anchor
    (unavailable incorporation, parsed as no incorporation).
    No couple item may contain additional anchors or href-less anchors.
    A couple may additionally contain exactly one direct
    .act-changes-history__couple-compare comparison control, which must
    contain no anchor and is not parsed as an item; a duplicate control
    or any other unexpected direct element child is terminal.
    Genuinely empty containers (no couples at all) are valid.
    Any unexpected direct element child in a couples wrapper is terminal.
    Uses direct-child selectors for couples and items.
    """
    # Every direct element child must be .act-changes-history__couple
    direct_children = couples_wrapper.find_all(recursive=False)
    couples = []
    anchors: list[list] = []
    for child in direct_children:
        if child.name == "div" and "act-changes-history__couple" in child.get("class", []):
            couples.append(child)
        else:
            raise ValueError(
                f"unexpected direct element child in {role} couples wrapper: "
                f"{child.name}"
            )

    for i, couple in enumerate(couples):
        # Every direct element child must be .act-changes-history__item or,
        # at most once, a .act-changes-history__couple-compare control.
        couple_direct = couple.find_all(recursive=False)
        items = []
        compare_controls = []
        for child in couple_direct:
            classes = child.get("class", [])
            if child.name == "div" and "act-changes-history__item" in classes:
                items.append(child)
            elif child.name == "div" and "act-changes-history__couple-compare" in classes:
                compare_controls.append(child)
            else:
                raise ValueError(
                    f"unexpected direct element child in {role} couple {i}: "
                    f"{child.name}"
                )
        if len(compare_controls) > 1:
            raise ValueError(
                f"malformed {role} couple {i}: "
                f"expected at most 1 comparison control, "
                f"found {len(compare_controls)}"
            )
        if compare_controls and compare_controls[0].find("a"):
            raise ValueError(
                f"malformed {role} couple {i}: "
                f"comparison control must not contain an anchor"
            )
        if len(items) == 0:
            raise ValueError(
                f"malformed {role} couple {i}: no items"
            )
        if len(items) > 2:
            raise ValueError(
                f"malformed {role} couple {i}: "
                f"expected at most 2 items, found {len(items)}"
            )
        # First item: exactly one a[href]
        first_item = items[0]
        first_links = first_item.select("a[href]")
        first_all_links = first_item.select("a")
        if len(first_links) != 1:
            raise ValueError(
                f"malformed {role} couple {i}: "
                f"first item must have exactly one a[href], "
                f"found {len(first_links)}"
            )
        if len(first_all_links) != 1:
            raise ValueError(
                f"malformed {role} couple {i}: "
                f"first item has href-less anchor"
            )
        couple_anchors: list = [first_links[0]]

        # Second item (optional). Two allowed shapes:
        #   1. exactly one a[href] -> incorporation;
        #   2. exactly one direct span whose normalized text is "---------"
        #      and no anchor -> unavailable incorporation, which parses as
        #      no incorporation.
        # Blank items, other text, nested/extra elements, anchors in the
        # marker shape, multiple spans, or mixed marker/anchor shapes are
        # malformed.
        if len(items) >= 2:
            second_item = items[1]
            second_links = second_item.select("a[href]")
            second_all_links = second_item.select("a")
            marker_spans = second_item.find_all("span", recursive=False)
            if second_links:
                # Anchor shape: exactly one a[href], no href-less anchors,
                # and no direct marker span (mixed marker/anchor is
                # malformed).
                if len(second_links) != 1:
                    raise ValueError(
                        f"malformed {role} couple {i}: "
                        f"second item must have exactly one a[href], "
                        f"found {len(second_links)}"
                    )
                if len(second_all_links) != 1:
                    raise ValueError(
                        f"malformed {role} couple {i}: "
                        f"second item has href-less anchor"
                    )
                if marker_spans:
                    raise ValueError(
                        f"malformed {role} couple {i}: "
                        f"second item cannot mix an anchor and a marker span"
                    )
                couple_anchors.append(second_links[0])
            else:
                # Marker shape (or malformed): no anchors at all, and the
                # only direct element child must be the marker span.
                if second_all_links:
                    raise ValueError(
                        f"malformed {role} couple {i}: "
                        f"second item has href-less anchor"
                    )
                direct_elements = second_item.find_all(recursive=False)
                if len(direct_elements) != 1 or len(marker_spans) != 1:
                    raise ValueError(
                        f"malformed {role} couple {i}: "
                        f"second item must have exactly one a[href] or "
                        f"exactly one direct '---------' span with no "
                        f"other elements, found {len(direct_elements)} "
                        f"direct elements"
                    )
                normalized = " ".join(
                    marker_spans[0].get_text(strip=True).split()
                )
                if normalized != "---------":
                    raise ValueError(
                        f"malformed {role} couple {i}: "
                        f"second item marker span must be '---------' "
                        f"with no anchor, got {normalized!r}"
                    )

        anchors.append(couple_anchors)

    return anchors


def _validate_relation_items_exact(container, index: int) -> list:
    """Validate relation items using exact validated container node.

    Returns one anchor per wrap, in document order.

    Each direct element child must be .act-conection__wrap.
    Each wrap contains exactly one direct .act-conection__item.
    Each item contains exactly one a[href].
    Genuinely empty containers are valid.
    """
    # Every direct element child must be .act-conection__wrap
    direct_children = container.find_all(recursive=False)
    anchors: list = []
    for i, child in enumerate(direct_children):
        if child.name != "div" or "act-conection__wrap" not in child.get("class", []):
            raise ValueError(
                f"malformed relation container {index} direct child {i}: "
                f"expected .act-conection__wrap, got {child.name}"
            )
        # Each wrap has exactly one direct .act-conection__item
        wrap_direct = child.find_all(recursive=False)
        wrap_items = []
        for wc in wrap_direct:
            if wc.name == "div" and "act-conection__item" in wc.get("class", []):
                wrap_items.append(wc)
            else:
                raise ValueError(
                    f"unexpected direct element child in relation container "
                    f"{index} wrap {i}: {wc.name}"
                )
        if len(wrap_items) != 1:
            raise ValueError(
                f"malformed relation container {index} wrap {i}: "
                f"expected exactly 1 direct .act-conection__item, "
                f"found {len(wrap_items)}"
            )
        item = wrap_items[0]
        links = item.select("a[href]")
        all_links = item.select("a")
        if len(links) != 1:
            raise ValueError(
                f"malformed relation item {index}.{i}: "
                f"expected exactly one a[href], found {len(links)}"
            )
        if len(all_links) != 1:
            raise ValueError(
                f"malformed relation item {index}.{i}: "
                f"has href-less anchor"
            )
        anchors.append(links[0])

    return anchors


def _validate_tab_structure(soup) -> _PageStructure:
    """Validate the complete tab structure on the act page and return nodes.

    Requires all three top-level tab containers with correct labels, both
    change sub-tabs with expected headings, and all four relation sub-tabs
    with matching containers. Uses explicit scoped/direct-child logic.
    Returns a _PageStructure bundle of exact validated nodes for parsers.
    """
    # --- Top-level tabs: same parent, direct-child ownership ---
    act_tabs_list = soup.select(".act-tabs")
    if len(act_tabs_list) != 1:
        raise ValueError(
            f"expected exactly 1 .act-tabs, found {len(act_tabs_list)}"
        )
    act_tabs_container_list = soup.select(".act-tabs-container")
    if len(act_tabs_container_list) != 1:
        raise ValueError(
            f"expected exactly 1 .act-tabs-container, "
            f"found {len(act_tabs_container_list)}"
        )
    # Same parent check
    if act_tabs_list[0].parent != act_tabs_container_list[0].parent:
        raise ValueError(
            ".act-tabs and .act-tabs-container must share the same parent"
        )

    # .act-tabs has exactly one direct .tabs wrapper
    tabs_wrappers = act_tabs_list[0].find_all(class_="tabs", recursive=False)
    if len(tabs_wrappers) != 1:
        raise ValueError(
            f"expected exactly 1 direct .tabs in .act-tabs, "
            f"found {len(tabs_wrappers)}"
        )
    tabs_wrapper = tabs_wrappers[0]

    # .tabs has exactly three direct .tab controls
    tab_controls = tabs_wrapper.find_all(class_="tab", recursive=False)
    if len(tab_controls) != 3:
        raise ValueError(
            f"expected exactly 3 direct .tab controls, "
            f"found {len(tab_controls)}"
        )

    # Each .tab has exactly one direct label span
    for i, tab in enumerate(tab_controls):
        spans = tab.find_all("span", recursive=False)
        if len(spans) != 1:
            raise ValueError(
                f"tab {i}: expected exactly 1 direct label span, "
                f"found {len(spans)}"
            )

    # Top-level tab containers: exactly 3 direct children
    tab_containers = act_tabs_container_list[0].find_all(
        class_="tab-container", recursive=False
    )
    if len(tab_containers) != 3:
        raise ValueError(
            f"expected 3 top-level tab containers, found {len(tab_containers)}"
        )

    # Top-level tab labels from validated direct children
    tab_labels = [
        tab.find_all("span", recursive=False)[0].get_text(strip=True)
        for tab in tab_controls
    ]
    if tab_labels != _ACT_TAB_LABELS:
        raise ValueError(
            f"top-level tab labels mismatch: expected {_ACT_TAB_LABELS}, "
            f"got {tab_labels}"
        )

    # Scoped blocks: .act-changes must be a DIRECT child of tab_containers[1],
    # .act-conection must be a DIRECT child of tab_containers[2].
    # Descendant substitutes (nested in intermediate wrappers) are rejected.
    changes_in_tab2 = tab_containers[1].find_all(
        class_="act-changes", recursive=False
    )
    if len(changes_in_tab2) != 1:
        raise ValueError(
            f"expected exactly one direct .act-changes child of second tab, "
            f"found {len(changes_in_tab2)}"
        )
    conection_in_tab3 = tab_containers[2].find_all(
        class_="act-conection", recursive=False
    )
    if len(conection_in_tab3) != 1:
        raise ValueError(
            f"expected exactly one direct .act-conection child of third tab, "
            f"found {len(conection_in_tab3)}"
        )
    # Ensure no stray blocks exist outside validated tabs
    if len(soup.select(".act-changes")) != 1:
        raise ValueError(
            f"stray .act-changes blocks outside second tab: "
            f"found {len(soup.select('.act-changes'))}"
        )
    if len(soup.select(".act-conection")) != 1:
        raise ValueError(
            f"stray .act-conection blocks outside third tab: "
            f"found {len(soup.select('.act-conection'))}"
        )

    # --- Changes block: scoped to .act-changes ---
    changes_block = soup.select_one(".act-changes")

    # .act-changes has exactly one direct .act-changes-block
    changes_blocks = changes_block.find_all(
        class_="act-changes-block", recursive=False
    )
    if len(changes_blocks) != 1:
        raise ValueError(
            f"expected exactly 1 direct .act-changes-block, "
            f"found {len(changes_blocks)}"
        )
    changes_block_inner = changes_blocks[0]

    # .act-changes-block has exactly one direct .act-nested-tabs
    changes_label_groups = changes_block_inner.find_all(
        class_="act-nested-tabs", recursive=False
    )
    if len(changes_label_groups) != 1:
        raise ValueError(
            f"expected exactly 1 direct changes label group, "
            f"found {len(changes_label_groups)}"
        )

    # Change sub-tab labels from direct .nested-tab children
    changes_label_group = changes_label_groups[0]
    change_tab_controls = changes_label_group.find_all(
        class_="nested-tab", recursive=False
    )
    if len(change_tab_controls) != 2:
        raise ValueError(
            f"expected exactly 2 change sub-tabs, found {len(change_tab_controls)}"
        )
    # Each change sub-tab must own exactly one direct span
    for i, tab in enumerate(change_tab_controls):
        spans = tab.find_all("span", recursive=False)
        if len(spans) != 1:
            raise ValueError(
                f"change sub-tab {i}: expected exactly 1 direct span, "
                f"found {len(spans)}"
            )
    change_labels = [
        tab.find_all("span", recursive=False)[0].get_text(strip=True)
        for tab in change_tab_controls
    ]
    if change_labels != _CHANGE_SUBTAB_LABELS:
        raise ValueError(
            f"change sub-tab labels mismatch: expected {_CHANGE_SUBTAB_LABELS}, "
            f"got {change_labels}"
        )

    # .act-changes-block has exactly one direct .act-nested-tabs-container
    changes_wrappers = changes_block_inner.find_all(
        class_="act-nested-tabs-container", recursive=False
    )
    if len(changes_wrappers) != 1:
        raise ValueError(
            f"expected exactly 1 direct changes nested-tabs wrapper, "
            f"found {len(changes_wrappers)}"
        )

    # Change containers: exactly two DIRECT children of the wrapper
    changes_wrapper = changes_wrappers[0]
    change_nested = changes_wrapper.find_all(
        class_="nested-tab-container", recursive=False
    )
    if len(change_nested) != 2:
        raise ValueError(
            f"expected exactly 2 change containers, "
            f"found {len(change_nested)}"
        )

    # Each direct change container: exactly one direct .act-changes-history
    # Both headings are validated first; each couples wrapper is collected
    # for validation after the loop.
    couples_wrappers_list: list = []
    for i, cn in enumerate(change_nested):
        histories = cn.find_all(
            class_="act-changes-history", recursive=False
        )
        if len(histories) != 1:
            raise ValueError(
                f"change container {i}: expected exactly 1 "
                f".act-changes-history, found {len(histories)}"
            )
        history = histories[0]

        # .act-changes-history has exactly one direct heading
        headings = history.find_all(
            class_="act-changes-history__heading", recursive=False
        )
        if len(headings) != 1:
            raise ValueError(
                f"change container {i}: expected exactly 1 heading, "
                f"found {len(headings)}"
            )
        heading = headings[0]
        spans = heading.find_all("span", recursive=False)
        if len(spans) != 2:
            raise ValueError(
                f"change container {i} heading: expected 2 spans, "
                f"found {len(spans)}"
            )
        first_span = spans[0].get_text(strip=True)
        second_span = spans[1].get_text(strip=True)
        if not first_span or not second_span:
            raise ValueError(
                f"change container {i} heading: span text is empty"
            )
        expected_first = _CHANGE_HEADING_FIRST_SPANS[i]
        expected_second = _CHANGE_HEADING_SECOND_SPANS[i]
        if first_span != expected_first:
            raise ValueError(
                f"change container {i} heading first span mismatch: "
                f"expected {expected_first!r}, got {first_span!r}"
            )
        if second_span != expected_second:
            raise ValueError(
                f"change container {i} heading second span mismatch: "
                f"expected {expected_second!r}, got {second_span!r}"
            )

        # .act-changes-history has exactly one direct couples wrapper
        couples_wrappers = history.find_all(
            class_="act-changes-history__couples", recursive=False
        )
        if len(couples_wrappers) != 1:
            raise ValueError(
                f"change container {i}: expected exactly 1 "
                f".act-changes-history__couples wrapper, "
                f"found {len(couples_wrappers)}"
            )

        # Collect the couples wrapper; every couples-wrapper shape rule
        # (direct couples only, item counts, anchor cardinality) is enforced
        # by _validate_change_couples_exact below, which returns the
        # validated per-couple anchors.
        couples_wrappers_list.append(couples_wrappers[0])

    # Validate couple items (counts, anchors) using exact validated
    # containers, after both change-heading validations
    change_anchors = [
        _validate_change_couples_exact(
            couples_wrappers_list[0], role="change_history"
        ),
        _validate_change_couples_exact(
            couples_wrappers_list[1], role="changed_acts"
        ),
    ]

    # Primary act proof: exactly one direct a.act-changes-primary[href]
    # child of the validated .act-changes block, and none anywhere else
    # (a second anchor elsewhere would make the declared primary ambiguous).
    direct_primary = changes_block.find_all(
        "a", class_="act-changes-primary", href=True, recursive=False
    )
    if len(direct_primary) != 1:
        raise ValueError(
            f"expected exactly 1 direct a.act-changes-primary[href] "
            f"child of .act-changes, found {len(direct_primary)}"
        )
    all_primary = soup.select("a.act-changes-primary")
    if len(all_primary) != 1:
        raise ValueError(
            f"globally expected exactly 1 a.act-changes-primary, "
            f"found {len(all_primary)}"
        )
    try:
        primary_href = _normalize_act_link(direct_primary[0]["href"])
    except ValueError as e:
        raise ValueError(f"primary act link: {e}") from e
    assert primary_href is not None  # the href attribute is present
    primary_id = _act_link_id(primary_href)

    # --- Relations block: scoped to .act-conection ---
    relation_block = soup.select_one(".act-conection")

    # .act-conection has exactly one direct .act-nested-tabs
    relation_label_groups = relation_block.find_all(
        class_="act-nested-tabs", recursive=False
    )
    if len(relation_label_groups) != 1:
        raise ValueError(
            f"expected exactly 1 direct relation label group, "
            f"found {len(relation_label_groups)}"
        )

    # Relation sub-tab labels from direct .nested-tab children
    relation_label_group = relation_label_groups[0]
    relation_tab_controls = relation_label_group.find_all(
        class_="nested-tab", recursive=False
    )
    if len(relation_tab_controls) != 4:
        raise ValueError(
            f"expected exactly 4 relation sub-tabs, "
            f"found {len(relation_tab_controls)}"
        )
    # Each relation sub-tab must own exactly one direct span
    for i, tab in enumerate(relation_tab_controls):
        spans = tab.find_all("span", recursive=False)
        if len(spans) != 1:
            raise ValueError(
                f"relation sub-tab {i}: expected exactly 1 direct span, "
                f"found {len(spans)}"
            )
    relation_labels = [
        tab.find_all("span", recursive=False)[0].get_text(strip=True)
        for tab in relation_tab_controls
    ]
    if relation_labels != _RELATION_SUBTAB_LABELS:
        raise ValueError(
            f"relation sub-tab labels mismatch: expected "
            f"{_RELATION_SUBTAB_LABELS}, got {relation_labels}"
        )

    # .act-conection has exactly one direct .act-nested-tabs-container
    relation_wrappers = relation_block.find_all(
        class_="act-nested-tabs-container", recursive=False
    )
    if len(relation_wrappers) != 1:
        raise ValueError(
            f"expected exactly 1 direct relation nested-tabs wrapper, "
            f"found {len(relation_wrappers)}"
        )

    # Relation containers: exactly four DIRECT children of the wrapper
    relation_wrapper = relation_wrappers[0]
    relation_containers = relation_wrapper.find_all(
        class_="nested-tab-container", recursive=False
    )
    if len(relation_containers) != 4:
        raise ValueError(
            f"expected 4 relation containers, found {len(relation_containers)}"
        )

    # Validate relation items (wrap counts, anchor cardinality) using exact
    # containers; each container returns its validated anchors. This runs
    # before the global exclusivity checks.
    relation_anchors = [
        _validate_relation_items_exact(rc, index=i)
        for i, rc in enumerate(relation_containers)
    ]

    # --- Global exclusivity checks ---
    # Every .act-nested-tabs on page must be exactly one of the two validated groups
    all_nested_tabs = soup.select(".act-nested-tabs")
    if len(all_nested_tabs) != 2:
        raise ValueError(
            f"stray .act-nested-tabs: expected 2 total, "
            f"found {len(all_nested_tabs)}"
        )

    # Every .act-nested-tabs-container on page must be exactly one of the two validated wrappers
    all_nested_tabs_containers = soup.select(".act-nested-tabs-container")
    if len(all_nested_tabs_containers) != 2:
        raise ValueError(
            f"stray .act-nested-tabs-container: expected 2 total, "
            f"found {len(all_nested_tabs_containers)}"
        )

    # No stray nested containers outside validated wrappers
    all_nested = soup.select(".nested-tab-container")
    # Expected: 2 change + 4 relation = 6
    if len(all_nested) != 6:
        raise ValueError(
            f"stray nested containers: expected 6 total, "
            f"found {len(all_nested)}"
        )

    return _PageStructure(
        tab_containers=tab_containers,
        change_anchors=change_anchors,
        relation_anchors=relation_anchors,
        relation_labels=relation_labels,
        primary_id=primary_id,
    )


def _parse_act(html: str, act_id: int, url: str) -> dict:
    """Parse one validated act page; `act_id` is the supplied URL's ID.

    The record is returned only under one uniform identity rule for
    every accepted URL form: both the requested ID and the served ID
    must belong to the act family the page declares — its primary act
    plus the incorporations of its inbound change history. Membership
    proves the same legal-act family, not a concrete URL's numeric
    version.
    """
    soup = BeautifulSoup(html, "lxml")

    # Validate page identity and structure before constructing record.
    served_id = _validate_page_identity(soup)
    structure = _validate_tab_structure(soup)

    title_div = soup.select_one(".act-info__title")
    title = title_div.get_text(strip=True) if title_div else ""

    result: dict = {
        "id": served_id,
        "url": url,
        "title": title,
        "source": "arlis",
    }

    # Parse all three validated tabs from the structure bundle
    result.update(_parse_validity(structure.tab_containers[0]))
    changes = _parse_changes(structure)
    result["changes"] = changes

    # Act-family membership: primary act plus the second (incorporation)
    # anchors of the inbound change-history couples only. Amending acts,
    # outbound couples and relation links are not family evidence.
    family = {structure.primary_id} | {
        _act_link_id(entry["incorporation"])
        for entry in changes["change_history"]
        if entry.get("incorporation")
    }
    for role, identity in (("requested", act_id), ("served", served_id)):
        if identity not in family:
            raise ValueError(
                f"page identity: {role} {identity} is not in the page's "
                f"act family {sorted(family)}"
            )

    result["relations"] = _parse_connections(structure)

    main_block = soup.select_one(".act-block_main .act-block__section")
    result["full_html"] = str(main_block) if main_block else ""

    return result
