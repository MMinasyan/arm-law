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


_RESULT_COUNT_RE = re.compile(r'result_count.*?\$\{(\d+)\}')
_CARD_LABELS = {
    "Ակտի համար`": "number",
    "Ընդունման ամսաթիվ`": "enactment_date",
    "Ուժի մեջ մտնելու ամսաթիվ`": "effective_date",
    "Կարգավիճակ`": "status",
}
_SEARCH_DATE_FIELDS = frozenset({
    "enactment_date", "effective_date", "interrupt_date",
    "signature_date", "ratification_date",
})

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

from dataclasses import dataclass, field


@dataclass(frozen=True)
class _ChangeData:
    """Validated nodes for one change container consumed by parsers."""
    couples_wrapper: object
    couple_anchors: list


@dataclass(frozen=True)
class _RelationData:
    """Validated anchors for one relation container."""
    anchors: list


@dataclass(frozen=True)
class _PageStructure:
    """Validated BeautifulSoup nodes returned by structure validation.

    Parsers receive these nodes and must not rediscover broader nodes.
    """
    tab_containers: list
    main_anchor: object
    change_data: list
    relation_data: list
    relation_labels: list


# --- discovery helpers ---


def _build_params(filters: dict | None) -> str:
    params: dict = {"simple_text": ""}
    if filters:
        params.update(filters)
    params["include_old_versions"] = "true"
    for field in _SEARCH_DATE_FIELDS:
        if field in params and isinstance(params[field], dict):
            params[field] = json.dumps(params[field])
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
        "discovered": datetime.now().strftime("%Y-%m-%d %H:%M"),
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
    order: str | None,
) -> tuple[list[dict], int | None]:
    order_by = "" if order is None else f"enactment_date {order}"
    url = f"{BASE_URL}/hy/search/page/{page}?{params}&order_by={order_by}"
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
    """Parse changes using exact validated nodes from structure bundle.

    Consumes only pre-validated nodes; does not rediscover any nodes.
    Uses couple_anchors from the validated structure bundle.
    """
    result: dict = {}

    # Main act from validated anchor
    result["main_act"] = _normalize_act_link(structure.main_anchor["href"])

    # Container 0: change history — consume validated change_data[0]
    cd = structure.change_data[0]
    history: list[dict] = []
    for couple_anchors in cd.couple_anchors:
        entry: dict = {}
        if len(couple_anchors) >= 1:
            entry["changing_act"] = _normalize_act_link(couple_anchors[0]["href"])
        if len(couple_anchors) >= 2:
            entry["incorporation"] = _normalize_act_link(couple_anchors[1]["href"])
        history.append(entry)
    result["change_history"] = history

    # Container 1: changed acts — consume validated change_data[1]
    cd = structure.change_data[1]
    modified: list[dict] = []
    for couple_anchors in cd.couple_anchors:
        entry: dict = {}
        if len(couple_anchors) >= 1:
            entry["changed_act"] = _normalize_act_link(couple_anchors[0]["href"])
        if len(couple_anchors) >= 2:
            entry["incorporation"] = _normalize_act_link(couple_anchors[1]["href"])
        modified.append(entry)
    result["changed_acts"] = modified

    return result


def _parse_connections(structure: _PageStructure) -> dict:
    """Parse connections using exact validated nodes from structure bundle.

    Consumes only pre-validated nodes; does not rediscover any nodes.
    Uses relation_labels and relation_data from the validated structure bundle.
    """
    # Labels from validated structure bundle (already extracted during validation)
    labels = structure.relation_labels

    result: dict = {}
    for label, rd in zip(labels, structure.relation_data):
        key = _RELATIONS_LABELS.get(label)
        if not key:
            continue
        urls: list[str] = []
        for anchor in rd.anchors:
            url = _normalize_act_link(anchor["href"])
            urls.append(url)
        result[key] = urls
    return result


def _validate_page_identity(soup, act_id: int) -> None:
    """Validate that page-owned identity evidence matches the requested act ID.

    Requires exactly one #share-act, one #download-act, one #print-act modal.
    Share group is every a[data-sharer] inside #share-act; each must have
    data-url full-matching strict share grammar. Download group is every
    a[onclick] inside #download-act; each onclick must full-match the exact
    planned location.href expression with SAME opening/closing quote.
    Print group is every a[href] inside #print-act; each must full-match
    exact relative print grammar. Each group non-empty. All IDs agree.
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

    if act_id not in found_ids:
        raise ValueError(
            f"page identity mismatch: requested {act_id}, "
            f"page shows {sorted(found_ids)}"
        )
    if len(found_ids) > 1:
        raise ValueError(
            f"page identity conflict: multiple IDs found {sorted(found_ids)}"
        )


def _validate_change_couples_exact(couples_wrapper, role: str) -> None:
    """Validate change history/changed acts couples using exact validated node.

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
    if couples_wrapper is None:
        return  # heading validation already failed

    # Every direct element child must be .act-changes-history__couple
    direct_children = couples_wrapper.find_all(recursive=False)
    couples = []
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


def _validate_relation_items_exact(container, index: int) -> None:
    """Validate relation items using exact validated container node.

    Each direct element child must be .act-conection__wrap.
    Each wrap contains exactly one direct .act-conection__item.
    Each item contains exactly one a[href].
    Genuinely empty containers are valid.
    """
    # Every direct element child must be .act-conection__wrap
    direct_children = container.find_all(recursive=False)
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
    # Also collect the couples wrapper and per-couple anchors for _ChangeData
    change_data_list: list[_ChangeData] = []
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

        # Collect the couples wrapper and per-couple anchors from the exact
        # wrapper; every couples-wrapper shape rule (direct couples only,
        # item counts, anchor cardinality) is enforced by
        # _validate_change_couples_exact below.
        cw = couples_wrappers[0]
        couple_anchors_list = []
        for child in cw.find_all(
            class_="act-changes-history__couple", recursive=False
        ):
            couple_anchors_for_this = []
            for ci in child.find_all(
                class_="act-changes-history__item", recursive=False
            ):
                a = ci.select_one("a[href]")
                if a:
                    couple_anchors_for_this.append(a)
            couple_anchors_list.append(couple_anchors_for_this)

        change_data_list.append(_ChangeData(
            couples_wrapper=cw,
            couple_anchors=couple_anchors_list,
        ))

    # Validate couple items (counts, anchors) using exact validated containers
    _validate_change_couples_exact(
        change_data_list[0].couples_wrapper, role="change_history"
    )
    _validate_change_couples_exact(
        change_data_list[1].couples_wrapper, role="changed_acts"
    )

    # Exactly one scoped main_act anchor inside .act-changes
    # Must be DIRECT child of .act-changes (not nested)
    direct_main_anchors = changes_block.find_all(
        "a", class_="act-changes-primary", href=True, recursive=False
    )
    if len(direct_main_anchors) != 1:
        raise ValueError(
            f"expected exactly 1 direct a.act-changes-primary[href] "
            f"child of .act-changes, found {len(direct_main_anchors)}"
        )
    # Globally only one .act-changes-primary anywhere
    all_main = soup.select("a.act-changes-primary")
    if len(all_main) != 1:
        raise ValueError(
            f"globally expected exactly 1 a.act-changes-primary, "
            f"found {len(all_main)}"
        )

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

    # Collect per-container anchors for _RelationData; every wrap/item/anchor
    # shape rule is enforced by _validate_relation_items_exact below.
    relation_data_list: list[_RelationData] = []
    for rc in relation_containers:
        anchors = []
        for wrap in rc.find_all(class_="act-conection__wrap", recursive=False):
            for item in wrap.find_all(
                class_="act-conection__item", recursive=False
            ):
                a = item.select_one("a[href]")
                if a:
                    anchors.append(a)
        relation_data_list.append(_RelationData(anchors=anchors))

    # Validate relation items (wrap counts, anchor cardinality) using exact containers
    for i, rc in enumerate(relation_containers):
        _validate_relation_items_exact(rc, index=i)

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
        main_anchor=direct_main_anchors[0],
        change_data=change_data_list,
        relation_data=relation_data_list,
        relation_labels=relation_labels,
    )


def _validate_changed_acts(changes: dict) -> None:
    """Validate changed_acts entries in the parsed changes dict.

    Every entry must contain ``changed_act`` and optional ``incorporation``.
    Both URLs must be valid ARLIS act URLs (HTTPS, arlis.am host, proper path).
    No extra keys are allowed.
    """
    if "changed_acts" not in changes:
        return

    changed_acts = changes["changed_acts"]
    if not isinstance(changed_acts, list):
        raise ValueError("changed_acts must be a list")

    for i, entry in enumerate(changed_acts):
        if not isinstance(entry, dict):
            raise ValueError(f"changed_acts[{i}] must be a dict")
        if "changed_act" not in entry:
            raise ValueError(
                f"changed_acts[{i}] missing required 'changed_act'"
            )

        changed_act_url = entry["changed_act"]
        if not isinstance(changed_act_url, str):
            raise ValueError(
                f"changed_acts[{i}].changed_act must be a string"
            )
        if not _ARLIS_ACT_URL_RE.match(changed_act_url):
            raise ValueError(
                f"changed_acts[{i}].changed_act is not a valid ARLIS act "
                f"URL: {changed_act_url!r}"
            )

        if "incorporation" in entry:
            incorp_url = entry["incorporation"]
            if not isinstance(incorp_url, str):
                raise ValueError(
                    f"changed_acts[{i}].incorporation must be a string"
                )
            if not _ARLIS_ACT_URL_RE.match(incorp_url):
                raise ValueError(
                    f"changed_acts[{i}].incorporation is not a valid ARLIS "
                    f"act URL: {incorp_url!r}"
                )

        allowed_keys = frozenset({"changed_act", "incorporation"})
        extra = set(entry.keys()) - allowed_keys
        if extra:
            raise ValueError(
                f"changed_acts[{i}] has unexpected keys: {sorted(extra)}"
            )


def _validate_change_history(changes: dict) -> None:
    """Validate change_history entries in the parsed changes dict.

    Every entry must contain ``changing_act`` and optional ``incorporation``.
    Both URLs must be valid ARLIS act URLs. No extra keys are allowed.
    """
    if "change_history" not in changes:
        return

    change_history = changes["change_history"]
    if not isinstance(change_history, list):
        raise ValueError("change_history must be a list")

    for i, entry in enumerate(change_history):
        if not isinstance(entry, dict):
            raise ValueError(f"change_history[{i}] must be a dict")
        if "changing_act" not in entry:
            raise ValueError(
                f"change_history[{i}] missing required 'changing_act'"
            )

        changing_act_url = entry["changing_act"]
        if not isinstance(changing_act_url, str):
            raise ValueError(
                f"change_history[{i}].changing_act must be a string"
            )
        if not _ARLIS_ACT_URL_RE.match(changing_act_url):
            raise ValueError(
                f"change_history[{i}].changing_act is not a valid ARLIS act "
                f"URL: {changing_act_url!r}"
            )

        if "incorporation" in entry:
            incorp_url = entry["incorporation"]
            if not isinstance(incorp_url, str):
                raise ValueError(
                    f"change_history[{i}].incorporation must be a string"
                )
            if not _ARLIS_ACT_URL_RE.match(incorp_url):
                raise ValueError(
                    f"change_history[{i}].incorporation is not a valid ARLIS "
                    f"act URL: {incorp_url!r}"
                )

        allowed_keys = frozenset({"changing_act", "incorporation"})
        extra = set(entry.keys()) - allowed_keys
        if extra:
            raise ValueError(
                f"change_history[{i}] has unexpected keys: {sorted(extra)}"
            )


def _validate_main_act(changes: dict) -> None:
    """Validate the main_act URL in the parsed changes dict."""
    if "main_act" not in changes:
        raise ValueError("missing required 'main_act'")
    main_act_url = changes["main_act"]
    if not isinstance(main_act_url, str):
        raise ValueError("main_act must be a string")
    if not _ARLIS_ACT_URL_RE.match(main_act_url):
        raise ValueError(
            f"main_act is not a valid ARLIS act URL: {main_act_url!r}"
        )


def _validate_relation_urls(relations: dict) -> None:
    """Validate that all relation URLs are valid ARLIS act URLs.

    Requires HTTPS, arlis.am host, proper locale/acts path, positive ID.
    Rejects external hosts, credentials, ports, query strings, extra suffixes.
    Requires exactly four expected relation keys.
    """
    expected_keys = frozenset({
        "general_relations", "judicial_precedents",
        "official_clarifications", "anti_constitutional",
    })
    actual_keys = set(relations.keys())
    if actual_keys != expected_keys:
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        parts = []
        if missing:
            parts.append(f"missing {sorted(missing)}")
        if extra:
            parts.append(f"unexpected {sorted(extra)}")
        raise ValueError(
            f"relations keys mismatch: {', '.join(parts)}"
        )
    for key, urls in relations.items():
        if not isinstance(urls, list):
            raise ValueError(f"relations.{key} must be a list")
        for j, url in enumerate(urls):
            if not isinstance(url, str):
                raise ValueError(
                    f"relations.{key}[{j}] must be a string"
                )
            if not _ARLIS_ACT_URL_RE.match(url):
                raise ValueError(
                    f"relations.{key}[{j}] is not a valid ARLIS act URL: "
                    f"{url!r}"
                )


def _parse_act(html: str, act_id: int, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    # Validate page identity and structure before constructing record
    _validate_page_identity(soup, act_id)
    structure = _validate_tab_structure(soup)

    title_div = soup.select_one(".act-info__title")
    title = title_div.get_text(strip=True) if title_div else ""

    result: dict = {
        "id": act_id,
        "url": url,
        "title": title,
        "source": "arlis",
        "extracted": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # Use exact validated nodes from structure bundle
    if len(structure.tab_containers) >= 1:
        result.update(_parse_validity(structure.tab_containers[0]))
    if len(structure.tab_containers) >= 2:
        result["changes"] = _parse_changes(structure)
        _validate_main_act(result["changes"])
        _validate_change_history(result["changes"])
        _validate_changed_acts(result["changes"])
    if len(structure.tab_containers) >= 3:
        result["relations"] = _parse_connections(structure)
        _validate_relation_urls(result["relations"])

    main_block = soup.select_one(".act-block_main .act-block__section")
    result["full_html"] = str(main_block) if main_block else ""

    return result
