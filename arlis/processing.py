from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString, Tag

def preprocess(record: dict) -> str:
    if not isinstance(record, dict) or not isinstance(record.get("full_html"), str):
        raise ValueError("full html: record full_html is missing or not a string")
    full_html = record["full_html"]
    soup = BeautifulSoup(full_html, "html.parser")
    for paragraph in soup.find_all("p"):
        if paragraph.find("a") is not None and paragraph.get_text(strip=True).lower() == "բովանդակություն":
            paragraph.decompose()
    return str(soup)

def clean(full_html: str) -> str:
    return full_html


def postprocess(full_html: str) -> str:
    """
    Handle ARLIS document endings:
    1. Table with first cell starting with <strong> at end -> move to body
    2. Table + specific p paragraph -> move both to body
    3. P element with all content in strong -> move to body
    """
    soup = BeautifulSoup(full_html, "html.parser")
    body = soup.body if soup.body else soup

    def is_paragraph_all_strong(p_elem):
        """Check if all content in paragraph is wrapped in strong tags."""
        if not p_elem or p_elem.name != 'p':
            return False
        # Check if there's any text outside strong tags
        for child in p_elem.children:
            if isinstance(child, NavigableString):
                if child.strip():  # Non-whitespace text outside strong
                    return False
            elif isinstance(child, Tag) and child.name != 'strong':
                return False
        # Check that there's at least one strong with content
        for strong in p_elem.find_all('strong'):
            if strong.get_text(strip=True):
                return True
        return False

    # STEP 1: Handle tables at document end
    # Find last table
    tables = body.find_all('table')
    if tables:
        last_table = tables[-1]

        # Check if it's inside a li
        containing_li = None
        for parent in last_table.parents:
            if parent.name == 'li':
                containing_li = parent
                break

        if containing_li:
            # NEW: Check for table + 1-2 paragraphs (all bold) case
            # Look for up to 2 paragraphs after the table (in same li or after list)
            bold_paragraphs = []

            # First, collect paragraphs in the same li after the table
            found_table = False
            for sibling in containing_li.children:
                if sibling == last_table:
                    found_table = True
                elif found_table and isinstance(sibling, Tag) and sibling.name == 'p':
                    if is_paragraph_all_strong(sibling):
                        bold_paragraphs.append(sibling)
                    else:
                        break  # Stop if we find a non-bold paragraph

            # Find the list containing the li
            parent_list = containing_li.parent

            # Then check for paragraphs after the list (if we have less than 2)
            if len(bold_paragraphs) < 2 and parent_list:
                found_list = False
                for elem in body.children:
                    if elem == parent_list:
                        found_list = True
                    elif found_list and isinstance(elem, Tag):
                        if elem.name == 'p' and is_paragraph_all_strong(elem):
                            bold_paragraphs.append(elem)
                            if len(bold_paragraphs) >= 2:
                                break
                        else:
                            break  # Stop if we find something else

            # Check if we have 1 or 2 bold paragraphs
            if 1 <= len(bold_paragraphs) <= 2:
                # Check that nothing follows the last paragraph
                last_elem = bold_paragraphs[-1]
                found_last = False
                nothing_after_last = True
                for elem in body.descendants:
                    if elem == last_elem:
                        found_last = True
                    elif found_last and isinstance(elem, Tag):
                        if last_elem not in elem.parents:
                            nothing_after_last = False
                            break

                if nothing_after_last:
                    # Check table requirements
                    if not last_table.find('thead'):
                        first_nonempty = None
                        for cell in last_table.find_all(['td', 'th']):
                            if cell.get_text(strip=True):
                                first_nonempty = cell
                                break

                        if first_nonempty:
                            first_child = None
                            for child in first_nonempty.children:
                                if isinstance(child, NavigableString):
                                    if child.strip():
                                        break  # Text before strong
                                elif isinstance(child, Tag):
                                    first_child = child
                                    break

                            if first_child and first_child.name == 'strong':
                                # Move table and all bold paragraphs to body end
                                last_table.extract()
                                body.append(last_table)
                                for p in bold_paragraphs:
                                    p.extract()
                                    body.append(p)
                                # Continue to Step 2 (other checks below)

            # Check for exception case: table followed by specific p in same li
            next_sibling = last_table.find_next_sibling()
            if next_sibling and next_sibling.name == 'p':
                # Check if this p is in the same li
                p_li = None
                for parent in next_sibling.parents:
                    if parent.name == 'li':
                        p_li = parent
                        break

                if p_li == containing_li:
                    # Extract only alphabetic characters from the p
                    p_text = next_sibling.get_text()
                    alphabetic_only = ''.join(c for c in p_text if c.isalpha())

                    if alphabetic_only == "ՀԱՎԱՍՏՎԱԾԷԷԼԵԿՏՐՈՆԱՅԻՆՍՏՈՐԱԳՐՈՒԹՅԱՄԲ":
                        # Check that nothing follows the p
                        found_p = False
                        nothing_after_p = True
                        for elem in body.descendants:
                            if elem == next_sibling:
                                found_p = True
                            elif found_p and isinstance(elem, Tag):
                                if next_sibling not in elem.parents:
                                    nothing_after_p = False
                                    break

                        if nothing_after_p:
                            # Check table requirements
                            if not last_table.find('thead'):
                                first_nonempty = None
                                for cell in last_table.find_all(['td', 'th']):
                                    if cell.get_text(strip=True):
                                        first_nonempty = cell
                                        break

                                if first_nonempty:
                                    first_child = None
                                    for child in first_nonempty.children:
                                        if isinstance(child, NavigableString):
                                            if child.strip():
                                                break  # Text before strong
                                        elif isinstance(child, Tag):
                                            first_child = child
                                            break

                                    if first_child and first_child.name == 'strong':
                                        # Remove both table and p, add to body
                                        last_table.extract()
                                        next_sibling.extract()
                                        body.append(last_table)
                                        body.append(next_sibling)
                                        # REMOVED: return soup
                                        # Continue to Step 2

            # Check if table is last element (nothing follows)
            found_table = False
            nothing_after = True
            for elem in body.descendants:
                if elem == last_table:
                    found_table = True
                elif found_table and isinstance(elem, Tag):
                    if last_table not in elem.parents:
                        nothing_after = False
                        break

            if nothing_after:
                # Check table requirements
                if not last_table.find('thead'):
                    first_nonempty = None
                    for cell in last_table.find_all(['td', 'th']):
                        if cell.get_text(strip=True):
                            first_nonempty = cell
                            break

                    if first_nonempty:
                        first_child = None
                        for child in first_nonempty.children:
                            if isinstance(child, NavigableString):
                                if child.strip():
                                    break  # Text before strong
                            elif isinstance(child, Tag):
                                first_child = child
                                break

                        if first_child and first_child.name == 'strong':
                            # Move table to body
                            last_table.extract()
                            body.append(last_table)
                            # REMOVED: return soup
                            # Continue to Step 2

    # Check for p with all content in strong
    all_p = body.find_all('p')
    if all_p:
        last_p = all_p[-1]

        # Check if it's inside a li
        in_li = False
        for parent in last_p.parents:
            if parent.name == 'li':
                in_li = True
                break

        if in_li:
            # Check if nothing follows it
            found_p = False
            nothing_after = True
            for elem in body.descendants:
                if elem == last_p:
                    found_p = True
                elif found_p and isinstance(elem, Tag):
                    if last_p not in elem.parents:
                        nothing_after = False
                        break

            if nothing_after:
                # Check if ALL content is in strong tag(s) - no text outside at all
                has_text_outside_strong = False

                for child in last_p.children:
                    if isinstance(child, NavigableString):
                        # Any text node outside strong, even whitespace
                        has_text_outside_strong = True
                        break
                    elif isinstance(child, Tag) and child.name != 'strong':
                        # Non-strong tag
                        has_text_outside_strong = True
                        break

                # Check that there is at least one strong tag with content
                has_strong = False
                for strong in last_p.find_all('strong'):
                    if strong.get_text(strip=True):
                        has_strong = True
                        break

                if has_strong and not has_text_outside_strong:
                    # Move p to end of body
                    last_p.extract()
                    body.append(last_p)

    # STEP 2: Handle tables with "Հայաստանի Հանրապետության" in last li
    # This runs AFTER Step 1 completes

    # Function to find the absolute last li in a list structure
    def find_last_li_in_structure(list_elem):
        """Find the last direct li child (not recursive)."""
        if not list_elem or list_elem.name not in ['ul', 'ol']:
            return None

        # Get all direct li children
        li_children = [child for child in list_elem.children if isinstance(child, Tag) and child.name == 'li']
        if not li_children:
            return None

        # Return the last direct li child
        return li_children[-1]

    # Find all top-level lists (lists not inside other lists)
    all_lists = body.find_all(['ul', 'ol'])
    top_level_lists = []

    for lst in all_lists:
        # Check if this list is inside another list
        is_nested = False
        for parent in lst.parents:
            if parent.name in ['ul', 'ol'] and parent != lst:
                is_nested = True
                break

        if not is_nested:
            top_level_lists.append(lst)

    # Process each top-level list
    for top_list in top_level_lists:
        # Find the last li in this list (not recursive - just direct children)
        last_li = find_last_li_in_structure(top_list)

        if not last_li:
            continue

        # Look for our specific table in this last li
        table_to_move = None
        for table in last_li.find_all('table'):
            # Skip if table has thead
            if table.find('thead'):
                continue

            # Check first non-empty cell for "Հայաստանի Հանրապետության"
            first_nonempty = None
            for cell in table.find_all(['td', 'th']):
                if cell.get_text(strip=True):
                    first_nonempty = cell
                    break

            if not first_nonempty:
                continue

            # Check if starts with strong tag
            first_child = None
            for child in first_nonempty.children:
                if isinstance(child, NavigableString):
                    if child.strip():
                        break  # Text before strong
                elif isinstance(child, Tag):
                    first_child = child
                    break

            if not first_child or first_child.name != 'strong':
                continue

            # Check if strong text starts with "Հայաստանի Հանրապետության"
            if first_child.get_text(strip=True).startswith("Հայաստանի Հանրապետության"):
                table_to_move = table
                break

        if not table_to_move:
            continue

        # Found a matching table in the last li
        # Collect the table and everything after it in that li
        elements_to_move = []
        table_found = False

        for elem in list(last_li.children):
            if elem == table_to_move:
                table_found = True
            if table_found:
                if isinstance(elem, Tag) or (isinstance(elem, NavigableString) and elem.strip()):
                    elements_to_move.append(elem)

        if not elements_to_move:
            continue

        # Extract and move after the top-level list
        for elem in elements_to_move:
            elem.extract()

        # Insert after the top-level list in order
        for elem in reversed(elements_to_move):
            top_list.insert_after(elem)

    # STEP 3: Extract "Հավելված" (Appendix) elements from deepest last li
    # Only p and table can be direct children of li at this point
    # (h1-h6 and hr are SECTION_BOUNDARY_TAGS that break lists in add_lists)
    STRUCTURAL_TAGS = {'p', 'table'}

    def find_deepest_last_li(list_elem):
        """Recursively find the deepest last li in a list structure."""
        if not list_elem or list_elem.name not in ['ul', 'ol']:
            return None
        li_children = [c for c in list_elem.children if isinstance(c, Tag) and c.name == 'li']
        if not li_children:
            return None
        last_li = li_children[-1]
        # If last li contains nested lists, recurse into the last one
        nested = last_li.find_all(['ul', 'ol'], recursive=False)
        if nested:
            deeper = find_deepest_last_li(nested[-1])
            if deeper:
                return deeper
        return last_li

    # Process lists that are direct children of body
    for top_list in [c for c in body.children if isinstance(c, Tag) and c.name in ['ul', 'ol']]:
        last_li = find_deepest_last_li(top_list)
        if not last_li:
            continue

        # Find structural tag whose text starts with "Հավելված" and is inside a strong
        appendix_elem = None
        for child in last_li.children:
            if not isinstance(child, Tag) or child.name not in STRUCTURAL_TAGS:
                continue
            # Check if child's text starts with the word, and that text is inside a strong
            text = child.get_text(strip=True)
            if not text.startswith('Հավելված'):
                continue
            # Verify that text is inside a strong by checking first text node
            for desc in child.descendants:
                if isinstance(desc, NavigableString) and desc.strip():
                    # Check if this first text starts with the word and is inside a strong
                    if desc.strip().startswith('Հավելված'):
                        in_strong = any(p.name == 'strong' for p in desc.parents if p != child)
                        if in_strong:
                            appendix_elem = child
                    break
            if appendix_elem:
                break

        if not appendix_elem:
            continue

        # Collect appendix_elem and all following siblings
        elements_to_move = []
        found = False
        for elem in list(last_li.children):
            if elem == appendix_elem:
                found = True
            if found and (isinstance(elem, Tag) or (isinstance(elem, NavigableString) and elem.strip())):
                elements_to_move.append(elem)

        if not elements_to_move:
            continue

        # Extract and insert after the top-level list
        for elem in elements_to_move:
            elem.extract()
        for elem in reversed(elements_to_move):
            top_list.insert_after(elem)

    return str(soup)
