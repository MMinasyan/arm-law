import re
from bs4 import NavigableString, Tag, Comment


arm_numerals = ['ա', 'բ', 'գ', 'դ', 'ե', 'զ', 'է', 'ը', 'թ', 'ժ',
                'ժա', 'ժբ', 'ժգ', 'ժդ', 'ժե', 'ժզ', 'ժէ', 'ժը', 'ժթ', 'ի',
                'իա', 'իբ', 'իգ', 'իդ', 'իե', 'իզ', 'իէ', 'իը', 'իթ', 'լ',
                'լա', 'լբ', 'լգ', 'լդ', 'լե', 'լզ', 'լէ', 'լը', 'լթ', 'խ',
                'խա', 'խբ', 'խգ', 'խդ', 'խե', 'խզ', 'խէ', 'խը', 'խթ']
sorted_arm_numerals = sorted(arm_numerals, key=len, reverse=True)
arm_pattern = "|".join(re.escape(num) for num in sorted_arm_numerals)

# Comparative length rule: absorb an element if n <= multiplier * n_prev.
_TRAILING_MULTIPLIER = 2

def get_list_info(p):
    """Detect if paragraph is a list item and return its properties."""
    text = p.text
    if m := re.match(r"(\s*\d{1,3}[\.․](?!\d)\s*)(.*)", text):
        prefix = m.group(1)
        number = int(re.search(r"\d+", prefix).group())
        item_text = m.group(2)
        return (0, number, item_text, prefix)
    elif m := re.match(r"(\s*\d{1,3}\)(?!\d)\s*)(.*)", text):
        prefix = m.group(1)
        number = int(re.search(r"\d+", prefix).group())
        item_text = m.group(2)
        return (1, number, item_text, prefix)
    elif m := re.match(r"(\s*(" + arm_pattern + r")[\.)/]\s*)(.*)", text):
        prefix = m.group(1)
        numeral = m.group(2)
        number = arm_numerals.index(numeral) + 1
        item_text = m.group(3)
        return (2, number, item_text, prefix)
    elif m := re.match(r"(\s*[a-z][\.)։]\s*)(.*)", text):
        prefix = m.group(1)
        letter = re.search(r"[a-z]", prefix).group()
        number = ord(letter) - ord('a') + 1
        item_text = m.group(2)
        return (3, number, item_text, prefix)
    elif m := re.match(r"(\s*(?:[•◦∙●]\s*|-\s+))(.*)", text):
        prefix = m.group(1)
        item_text = m.group(2)
        return (4, None, item_text, prefix)
    return None


def add_li(soup, list_tag, p, prefix):
    """Convert paragraph to list item."""
    li = soup.new_tag('li')
    if list_tag.name == 'ul':
        # For unordered lists, remove the bullet prefix
        if p.contents:
            first_content = p.contents[0]
            if isinstance(first_content, str) and first_content.startswith(prefix):
                remaining_text = first_content[len(prefix):]
                if remaining_text:
                    li.append(remaining_text)
                for content in p.contents[1:]:
                    li.append(content.extract())
            else:
                li.append(' ')
                for content in p.contents[:]:
                    li.append(content.extract())
    else:
        # For ordered lists, consume prefix text length and add space if needed
        prefix_len = len(prefix)
        consumed = 0
        while consumed < prefix_len and p.contents:
            content = p.contents[0]
            if isinstance(content, str):
                content_len = len(content)
                if consumed + content_len <= prefix_len:
                    li.append(content.extract())
                    consumed += content_len
                else:
                    split = prefix_len - consumed
                    li.append(content[:split])
                    remaining = content[split:]
                    content.replace_with(remaining)
                    consumed += split
                    break
            else:
                break
        if consumed == prefix_len and not prefix.endswith(' '):
            if p.contents:
                next_content = p.contents[0]
                if not (isinstance(next_content, str) and next_content.startswith(' ')):
                    li.append(' ')
            else:
                li.append(' ')
        for content in p.contents[:]:
            li.append(content.extract())
    list_tag.append(li)
    p.decompose()
    return li


def wrap_leading_text(soup, li):
    """Wrap leading text and inline elements in list item in a paragraph, stopping at structural tags."""
    # Define structural/block-level tags that should NOT be wrapped in <p>
    STRUCTURAL_TAGS = {'p', 'div', 'table', 'ul', 'ol', 'li', 'h1', 'h2', 'h3',
                       'h4', 'h5', 'h6', 'hr', 'blockquote', 'pre', 'dl', 'dd',
                       'dt', 'section', 'article', 'aside', 'header', 'footer',
                       'nav', 'form', 'fieldset'}

    # If first child is not a NavigableString, don't wrap
    if not li.contents or not isinstance(li.contents[0], NavigableString):
        return

    first_p = soup.new_tag('p')

    # Extract content (text and inline tags) until we hit a structural tag
    while li.contents:
        first_child = li.contents[0]

        # If it's a structural tag, stop
        if isinstance(first_child, Tag) and first_child.name in STRUCTURAL_TAGS:
            break

        # Otherwise (NavigableString or inline tag), extract and add to paragraph
        first_p.append(first_child.extract())

    # Only insert the paragraph if it has content
    if first_p.contents:
        li.insert(0, first_p)

def add_prefixes_to_ol_li(soup):
    """Add numeric prefixes to ordered list items."""
    void_elements = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 
                     'link', 'meta', 'param', 'source', 'track', 'wbr'}
    
    for ol in soup.find_all('ol'):
        start = int(ol.attrs.get('start', 1))
        for index, li in enumerate(ol.find_all('li', recursive=False), start=start):
            prefix = f"{index}. "
            found = False

            for node in li.descendants:
                if isinstance(node, Comment):
                    continue
                if isinstance(node, NavigableString) and node.strip():
                    node.replace_with(prefix + node)
                    found = True
                    break
                if isinstance(node, Tag) and node.get_text(strip=True):
                    if node.name in void_elements:
                        node.insert_before(prefix)
                    else:
                        node.insert(0, prefix)
                    found = True
                    break

            if not found:
                li.insert(0, prefix)
        ol.attrs.pop('start', None)
    return soup

def process_lists(soup, element):
    """
    Convert pseudo-lists to real lists with comparative length rule for all absorption decisions.
    Section boundaries (including Հոդված paragraphs) always terminate lists.
    
    Args:
        soup: BeautifulSoup object
        element: Element to process
    """
    # Tags that truly indicate a new document section - should never be inside a list item
    SECTION_BOUNDARY_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr'}
    
    # Get ALL children, not just paragraphs
    all_children = [tag for tag in element.children if tag.name]
    
    # Create mapping from element id to index for O(1) lookup in sibling loops
    elem_to_idx = {id(child): idx for idx, child in enumerate(all_children)}
    
    def is_section_boundary_paragraph(p, idx=None, level=None, expected_number=None):
        """Check if paragraph is a section boundary.

        A paragraph is a section boundary if:
        1. It starts with <strong>Հոդված [digit]</strong>, OR
        2. It contains at least 1 uppercase letter and no lowercase letters,
           AND is NOT between items of the same level list

        Args:
            p: The paragraph element to check
            idx: Current index in all_children (for lookahead)
            level: Current list level (for checking if between items)
            expected_number: Expected next item number at current level
        """
        if not p or p.name != 'p':
            return False

        # Check 1: <strong>Հոդված [digit]</strong> pattern (always a boundary)
        first_child = None
        for child_elem in p.children:
            if isinstance(child_elem, NavigableString):
                if child_elem.strip():
                    break
            elif isinstance(child_elem, Tag):
                first_child = child_elem
                break

        if first_child and first_child.name == 'strong':
            strong_text = first_child.get_text().strip()
            if bool(re.match(r'^Հոդված\s+\d', strong_text)):
                return True

        # Check 2: All uppercase paragraph not between items of same level list
        # (at least 1 uppercase letter, no lowercase letters in any alphabet)
        text = p.get_text()
        has_upper = any(char.isupper() for char in text)
        has_lower = any(char.islower() for char in text)

        if has_upper and not has_lower:
            # If no list context, it's a boundary (not inside a list)
            if idx is None or level is None:
                return True

            # Check if there's a continuation of the current list after this paragraph
            for k in range(idx + 1, len(all_children)):
                if is_section_boundary(all_children[k], k, level, expected_number):
                    # Hit a boundary, no continuation possible
                    return True
                if all_children[k].name == 'p':
                    info = get_list_info(all_children[k])
                    if info:
                        if info[0] == level:
                            # Same level - check if it continues the sequence
                            if level == 4 or info[1] == expected_number:
                                # Found continuation - paragraph IS between items
                                return False
                            else:
                                # Different sequence - not between items
                                return True
                        elif info[0] < level:
                            # Hit a shallower level - not between items
                            return True
            # No more items found - not between items
            return True

        return False

    def is_section_boundary(elem, idx=None, level=None, expected_number=None):
        """Check if element is a section boundary.

        Args:
            elem: Element to check
            idx: Current index in all_children (for lookahead in all-uppercase check)
            level: Current list level (for checking if between items)
            expected_number: Expected next item number at current level
        """
        return elem.name in SECTION_BOUNDARY_TAGS or is_section_boundary_paragraph(elem, idx, level, expected_number)
    
    def will_have_more_items(start_idx, level, expected_number):
        """Check if there will be more items that continue this list."""
        for k in range(start_idx + 1, len(all_children)):
            if is_section_boundary(all_children[k], k, level, expected_number):
                return False
            if all_children[k].name == 'p':
                info = get_list_info(all_children[k])
                if info:
                    if info[0] == level:
                        # Same level - check if it continues the sequence
                        if level == 4 or info[1] == expected_number:
                            return True
                        else:
                            return False
                    elif info[0] < level:
                        # Hit a shallower level, no more items at our level
                        return False
                elif level == 4:
                    # For unordered lists, check if next paragraph is also a bullet
                    # If not, bullets are not adjacent and likely in different lists
                    if k + 1 < len(all_children) and all_children[k + 1].name == 'p':
                        next_info = get_list_info(all_children[k + 1])
                        if not (next_info and next_info[0] == 4):
                            return False
                    else:
                        return False
        return False
    
    def count_li_content(li):
        """Count elements absorbed into a list item (including the item line itself)."""
        inline_tags = {'a', 'b', 'strong', 'i', 'em', 'u', 'sup', 'sub', 'br'}
        children = list(li.children)

        if not children:
            return 1

        # Find first meaningful child (skip whitespace-only text nodes)
        first_meaningful_idx = 0
        for i, child in enumerate(children):
            if isinstance(child, NavigableString):
                if child.strip():
                    break
            else:
                first_meaningful_idx = i
                break

        if first_meaningful_idx >= len(children):
            return 1

        first_child = children[first_meaningful_idx]

        # If first meaningful child is <p>, it's the wrapped first line
        if hasattr(first_child, 'name') and first_child.name == 'p':
            first_line_end = first_meaningful_idx
        else:
            # First child is text/inline. First line ends at first non-inline element.
            first_line_end = None
            for i, child in enumerate(children):
                if child.name and child.name not in inline_tags:
                    first_line_end = i - 1
                    break

            if first_line_end is None:
                # No non-inline elements found, entire content is first line
                return 1

        # Count all tags after the first line
        count = 0
        for i, child in enumerate(children):
            if i > first_line_end and child.name:
                count += 1
        return count + 1
    
    def get_previous_li_at_same_level(stack, level, expected_number):
        """Find the previous list item at the same level and list."""
        for i in range(len(stack) - 1, -1, -1):
            if stack[i][0] == level:
                list_tag = stack[i][1]
                # Find all li elements in this list at this level
                all_li = list_tag.find_all('li', recursive=False)
                if len(all_li) >= 2:
                    # Return the second-to-last li (the one before current)
                    return all_li[-2]
                break
        return None
    
    def get_n_prev_for_trailing(stack):
        """Get the appropriate n_prev for trailing element comparison."""
        # Get the list tag and find previous sibling
        list_tag = stack[-1][1]
        all_li = list_tag.find_all('li', recursive=False)
        
        if len(all_li) >= 2:
            # Use the previous sibling's count
            prev_li = all_li[-2]
            result = count_li_content(prev_li)
            return result
        else:
            # No previous sibling, use current if it has content
            if stack[-1][4] > 1:
                return stack[-1][4]
            else:
                return 1
    
    # Enhanced stack to track element counts: (level, list_tag, expected_number, current_li, absorbed_count)
    stack = []
    i = 0
    
    while i < len(all_children):
        child = all_children[i]
        
        # Check for section boundaries FIRST
        # Pass context from stack if available for all-uppercase boundary check
        if stack:
            is_boundary = is_section_boundary(child, i, stack[-1][0], stack[-1][2])
        else:
            is_boundary = is_section_boundary(child, i, None, None)
        if is_boundary:
            # Section boundary - always breaks the list
            while stack:
                stack.pop()
            i += 1
            continue
        
        # Only process if it's a paragraph
        if child.name != 'p':
            # Check for pre-existing list that should be merged into active same-type list
            if child.name in ('ol', 'ul') and stack and stack[-1][1].name == child.name:
                lis = child.find_all('li', recursive=False)
                if lis:
                    list_tag = stack[-1][1]
                    last_li = None
                    for li_item in lis:
                        li_item.extract()
                        list_tag.append(li_item)
                        last_li = li_item
                    child.decompose()
                    stack[-1] = (stack[-1][0], list_tag, stack[-1][2], last_li, stack[-1][4] + len(lis))
                    i += 1
                    continue
            # Check for pre-existing ol/ul that should be adopted into stack
            if child.name in ('ol', 'ul') and not stack:
                lis = child.find_all('li', recursive=False)
                if lis:
                    last_li = lis[-1]
                    info = get_list_info(last_li)
                    if info:
                        level, number = info[0], info[1]
                        expected = number + 1 if level < 4 else None
                        if will_have_more_items(i, level, expected):
                            # Adopt this pre-existing list into the stack
                            stack.append((level, child, expected, last_li, len(lis)))
                            i += 1
                            continue
            # Non-paragraph element
            if stack:
                # We're inside a list structure
                # Check if this is between items or trailing
                # For nested structures, apply comparative length rule
                if len(stack) > 1:
                    # Nested structure - always absorb to current item for now
                    # (will be handled properly in lookahead)
                    li = stack[-1][3]
                    child.extract()
                    li.append(child)
                    stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + 1)
                else:
                    # Top level - check if trailing
                    is_trailing = True
                    for k in range(i + 1, len(all_children)):
                        if all_children[k].name == 'p':
                            info = get_list_info(all_children[k])
                            if info and info[0] == stack[-1][0]:
                                is_trailing = False
                                break
                    
                    if is_trailing:
                        # Apply comparative length rule for trailing
                        # Count trailing elements
                        trailing_count = 0
                        temp_idx = i
                        while temp_idx < len(all_children):
                            if is_section_boundary(all_children[temp_idx], temp_idx, stack[-1][0], stack[-1][2]):
                                break
                            if all_children[temp_idx].name:
                                trailing_count += 1
                            temp_idx += 1
                        
                        n = trailing_count + 1  # +1 conceptually for consistency
                        n_prev = get_n_prev_for_trailing(stack)
                        
                        if n <= _TRAILING_MULTIPLIER * n_prev:
                            # Absorb
                            li = stack[-1][3]
                            child.extract()
                            li.append(child)
                            stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + 1)
                        else:
                            # Don't absorb - clear stack
                            while stack:
                                stack.pop()
                    else:
                        # Between items - always absorb
                        li = stack[-1][3]
                        child.extract()
                        li.append(child)
                        stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + 1)
            i += 1
            continue
        
        p = child
        list_info = get_list_info(p)
        
        if list_info:
            level, number, item_text, prefix = list_info
            
            # Save position BEFORE moving the paragraph
            after_p = p.next_sibling
            
            # Pop levels deeper than current
            while stack and stack[-1][0] > level:
                popped = stack.pop()
            
            if stack and stack[-1][0] == level:
                # Same level as current stack top
                if level == 4 or (number == stack[-1][2]):
                    # Continue the list normally
                    list_tag = stack[-1][1]
                    li = add_li(soup, list_tag, p, prefix)
                    
                    stack[-1] = (level, list_tag, number + 1 if level < 4 else None, li, 1)
                else:
                    # Number sequence broken
                    if not will_have_more_items(i, level, number + 1 if level < 4 else None):
                        # Single item - treat as regular paragraph
                        if stack:
                            li = stack[-1][3]
                            p.extract()
                            li.append(p)
                            stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + 1)
                    else:
                        # Multiple items - create new list
                        if level == stack[0][0]:
                            # At outermost level - clear entire stack
                            stack = []
                            new_list = soup.new_tag('ol' if level < 4 else 'ul')
                            if level < 4 and number != 1:
                                new_list['start'] = str(number)
                            p.insert_before(new_list)
                            li = add_li(soup, new_list, p, prefix)
                            stack.append((level, new_list, number + 1 if level < 4 else None, li, 1))
                        else:
                            # Nested level - only clear current level
                            while stack and stack[-1][0] >= level:
                                stack.pop()
                            new_list = soup.new_tag('ol' if level < 4 else 'ul')
                            if level < 4 and number != 1:
                                new_list['start'] = str(number)
                            stack[-1][3].append(new_list)
                            li = add_li(soup, new_list, p, prefix)
                            stack.append((level, new_list, number + 1 if level < 4 else None, li, 1))
            else:
                # New list at this level
                if not will_have_more_items(i, level, number + 1 if level < 4 else None):
                    # Single item - treat as regular paragraph
                    if stack:
                        li = stack[-1][3]
                        p.extract()
                        li.append(p)
                        stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + 1)
                else:
                    # Multiple items - create list
                    new_list = soup.new_tag('ol' if level < 4 else 'ul')
                    if level < 4 and number != 1:
                        new_list['start'] = str(number)
                    if stack:
                        stack[-1][3].append(new_list)
                    else:
                        p.insert_before(new_list)
                    li = add_li(soup, new_list, p, prefix)
                    stack.append((level, new_list, number + 1 if level < 4 else None, li, 1))
            
            i += 1
            
            # Look ahead for absorption with COMPARATIVE LENGTH RULE
            if stack:
                j = i
                # Search for next list item, but stop at section boundaries and pre-existing lists
                while j < len(all_children):
                    if is_section_boundary(all_children[j], j, stack[-1][0], stack[-1][2]):
                        # Hit a section boundary - stop searching
                        break
                    if all_children[j].name in ('ul', 'ol'):
                        # Pre-existing list is a structural boundary - stop searching
                        break
                    if all_children[j].name == 'p':
                        if get_list_info(all_children[j]) is not None:
                            # Found next list item
                            break
                    j += 1

                next_p = None
                next_info = None
                if j < len(all_children) and all_children[j].name == 'p':
                    temp_info = get_list_info(all_children[j])
                    if temp_info:
                        next_level_temp, next_number_temp = temp_info[0], temp_info[1]

                        # Check if next item is outside current list structure scope
                        # This happens when we're nested and find an item that doesn't continue any list in stack
                        if len(stack) > 1 and next_level_temp <= stack[-2][0]:
                            # Next item is at parent level or shallower
                            # Check if it continues any list in our stack
                            continues_stack_level = False
                            for stack_entry in stack:
                                if stack_entry[0] == next_level_temp:
                                    # Check if it continues this level's list
                                    if next_level_temp == 4 or next_number_temp == stack_entry[2]:
                                        continues_stack_level = True
                                        break

                            if not continues_stack_level:
                                # Next item doesn't continue any list in stack - it's outside our scope
                                # Treat as "no next item found"
                                temp_info = None

                        if temp_info:
                            next_p = all_children[j]
                            next_info = temp_info
                
                # Determine start point for counting elements
                if len(stack) == 1:
                    start_point = stack[0][1].next_sibling
                else:
                    start_point = after_p
                
                # Count elements between current and next list item (or end)
                elem_count = 0
                current_sib = start_point
                while current_sib and current_sib != next_p:
                    if current_sib.name:
                        elem_count += 1
                    current_sib = current_sib.next_sibling
                
                if next_p and next_info:  # We found a next list item
                    next_level, next_number = next_info[0], next_info[1]
                    
                    # Get current level and expected number
                    current_level = stack[-1][0]
                    current_expected = stack[-1][2]
                    
                    # Check if next continues current list
                    continues_current = (
                        next_level == current_level and 
                        (current_level == 4 or next_number == current_expected)
                    )
                    
                    # Apply absorption rules
                    if continues_current:
                        # Between consecutive items of same list - ALWAYS absorb unless hard section boundary
                        li = stack[-1][3]
                        if start_point and start_point != next_p:
                            wrap_leading_text(soup, li)
                        current_sib = start_point
                        absorbed = 0
                        while current_sib and current_sib != next_p:
                            # Check for section boundary (headers, hr, Հdelays pattern)
                            if is_section_boundary(current_sib, elem_to_idx.get(id(current_sib)), stack[-1][0], stack[-1][2]):
                                # Clear stack and stop
                                while stack:
                                    stack.pop()
                                break
                            next_sib = current_sib.next_sibling
                            li.append(current_sib)
                            absorbed += 1
                            current_sib = next_sib
                        else:
                            # Only update stack if we didn't hit section boundary
                            if stack:
                                stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + absorbed)
                                i = j
                    elif next_level > current_level:
                        # Next is deeper level - absorb to current (preamble) unless hard section boundary
                        li = stack[-1][3]
                        if start_point and start_point != next_p:
                            wrap_leading_text(soup, li)
                        current_sib = start_point
                        absorbed = 0
                        while current_sib and current_sib != next_p:
                            # Check for section boundary (headers, hr, Հdelays pattern)
                            if is_section_boundary(current_sib, elem_to_idx.get(id(current_sib)), stack[-1][0], stack[-1][2]):
                                # Clear stack and stop
                                while stack:
                                    stack.pop()
                                break
                            next_sib = current_sib.next_sibling
                            li.append(current_sib)
                            absorbed += 1
                            current_sib = next_sib
                        else:
                            # Only update stack if we didn't hit section boundary
                            if stack:
                                stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + absorbed)
                                i = j
                    else:
                        # next_level <= current_level: Apply COMPARATIVE LENGTH RULE
                        if len(stack) > 1:
                            # We're in nested structure - apply comparative length rule
                            n = elem_count + 1  # +1 for the next item line itself
                            
                            # Find previous item at same level to get n_prev
                            prev_li = get_previous_li_at_same_level(stack, current_level, current_expected)
                            if prev_li:
                                n_prev = count_li_content(prev_li)
                            else:
                                # No previous item found, use current item as baseline
                                n_prev = stack[-1][4]
                            
                            if n <= _TRAILING_MULTIPLIER * n_prev:
                                # Absorb to current item
                                li = stack[-1][3]
                                if start_point and start_point != next_p:
                                    wrap_leading_text(soup, li)
                                current_sib = start_point
                                absorbed = 0
                                while current_sib and current_sib != next_p:
                                    # Check for section boundary
                                    if is_section_boundary(current_sib, elem_to_idx.get(id(current_sib)), stack[-1][0], stack[-1][2]):
                                        # Clear stack and stop
                                        while stack:
                                            stack.pop()
                                        break
                                    next_sib = current_sib.next_sibling
                                    li.append(current_sib)
                                    absorbed += 1
                                    current_sib = next_sib
                                else:
                                    # Only update if we didn't hit section boundary
                                    if stack:
                                        stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + absorbed)
                                        i = j
                            else:
                                # Don't absorb to current, pop level and absorb to parent
                                stack.pop()
                                if stack:
                                    parent_li = stack[-1][3]
                                    if start_point and start_point != next_p:
                                        wrap_leading_text(soup, parent_li)
                                    current_sib = start_point
                                    absorbed = 0
                                    while current_sib and current_sib != next_p:
                                        # Check for section boundary
                                        if is_section_boundary(current_sib, elem_to_idx.get(id(current_sib)), stack[-1][0], stack[-1][2]):
                                            # Clear stack and stop
                                            while stack:
                                                stack.pop()
                                            break
                                        next_sib = current_sib.next_sibling
                                        parent_li.append(current_sib)
                                        absorbed += 1
                                        current_sib = next_sib
                                    else:
                                        # Only update if we didn't hit section boundary
                                        if stack:
                                            stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], parent_li, stack[-1][4] + absorbed)
                                            i = j
                        else:
                            # Top level - apply comparative length rule
                            n = elem_count + 1
                            
                            # For top level, use previous sibling's count when current is empty
                            if stack[-1][4] == 1:
                                # Just added, get previous sibling's count
                                list_tag = stack[-1][1]
                                all_li = list_tag.find_all('li', recursive=False)
                                if len(all_li) >= 2:
                                    prev_li = all_li[-2]
                                    n_prev = count_li_content(prev_li)
                                else:
                                    n_prev = 1
                            else:
                                n_prev = stack[-1][4]
                            
                            if n <= _TRAILING_MULTIPLIER * n_prev:
                                li = stack[-1][3]
                                if start_point and start_point != next_p:
                                    wrap_leading_text(soup, li)
                                current_sib = start_point
                                absorbed = 0
                                while current_sib and current_sib != next_p:
                                    # Check for section boundary
                                    if is_section_boundary(current_sib, elem_to_idx.get(id(current_sib)), stack[-1][0], stack[-1][2]):
                                        # Clear stack and stop
                                        while stack:
                                            stack.pop()
                                        break
                                    next_sib = current_sib.next_sibling
                                    li.append(current_sib)
                                    absorbed += 1
                                    current_sib = next_sib
                                else:
                                    # Only update if we didn't hit section boundary
                                    if stack:
                                        stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + absorbed)
                                        i = j
                            else:
                                # Don't absorb, clear stack
                                while stack:
                                    stack.pop()
                else:
                    # No next list item found - these are trailing elements
                    # Recount elements stopping at section boundaries
                    trailing_count = 0
                    temp_sib = start_point
                    while temp_sib:
                        if is_section_boundary(temp_sib, elem_to_idx.get(id(temp_sib)), stack[-1][0], stack[-1][2]):
                            break
                        if temp_sib.name:
                            trailing_count += 1
                        temp_sib = temp_sib.next_sibling

                    if trailing_count > 0:
                        n = trailing_count + 1  # +1 for consistency
                        n_prev = get_n_prev_for_trailing(stack)

                        if n <= _TRAILING_MULTIPLIER * n_prev:
                            # Absorb trailing elements
                            li = stack[-1][3]
                            if start_point:
                                wrap_leading_text(soup, li)
                            current_sib = start_point
                            absorbed = 0
                            while current_sib:
                                if is_section_boundary(current_sib, elem_to_idx.get(id(current_sib)), stack[-1][0], stack[-1][2]):
                                    # Clear stack and stop
                                    while stack:
                                        stack.pop()
                                    break
                                next_sib = current_sib.next_sibling
                                li.append(current_sib)
                                absorbed += 1
                                current_sib = next_sib
                            else:
                                # Only update if we didn't hit section boundary
                                if stack:
                                    stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + absorbed)
                                    # Skip the absorbed elements
                                    i = i + absorbed
                        else:
                            # Threshold exceeded - don't absorb, close all lists
                            while stack:
                                stack.pop()
        else:
            # Non-list paragraph
            if stack:
                # Inside list structure
                if len(stack) > 1:
                    # Nested - always absorb
                    li = stack[-1][3]
                    p.extract()
                    li.append(p)
                    stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + 1)
                else:
                    # Top level - check if trailing
                    is_trailing = True
                    for k in range(i + 1, len(all_children)):
                        if all_children[k].name == 'p':
                            info = get_list_info(all_children[k])
                            if info and info[0] == stack[-1][0]:
                                is_trailing = False
                                break
                    
                    if is_trailing:
                        # Apply comparative length rule for trailing
                        trailing_count = 0
                        temp_idx = i
                        while temp_idx < len(all_children):
                            if is_section_boundary(all_children[temp_idx], temp_idx, stack[-1][0], stack[-1][2]):
                                break
                            if all_children[temp_idx].name:
                                trailing_count += 1
                            temp_idx += 1
                        
                        n = trailing_count + 1
                        n_prev = get_n_prev_for_trailing(stack)
                        
                        if n <= _TRAILING_MULTIPLIER * n_prev:
                            li = stack[-1][3]
                            p.extract()
                            li.append(p)
                            stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + 1)
                        else:
                            while stack:
                                stack.pop()
                    else:
                        # Between items - always absorb
                        li = stack[-1][3]
                        p.extract()
                        li.append(p)
                        stack[-1] = (stack[-1][0], stack[-1][1], stack[-1][2], li, stack[-1][4] + 1)
            i += 1
    
    # Handle trailing elements after the last list item
    if stack and stack[0][1].next_sibling:
        first_trailing = stack[0][1].next_sibling

        # Check if first trailing is a section boundary
        if is_section_boundary(first_trailing, elem_to_idx.get(id(first_trailing)), stack[-1][0], stack[-1][2]):
            # Don't absorb - clear stack
            while stack:
                stack.pop()
        else:
            # Apply comparative length rule
            # Count trailing elements
            elem_count = 0
            temp_sib = first_trailing

            while temp_sib:
                if temp_sib.name:
                    if is_section_boundary(temp_sib, elem_to_idx.get(id(temp_sib)), stack[-1][0], stack[-1][2]):
                        break
                    elem_count += 1
                temp_sib = temp_sib.next_sibling

            n = elem_count + 1  # +1 for consistency
            n_prev = get_n_prev_for_trailing(stack)

            if n <= _TRAILING_MULTIPLIER * n_prev:
                # Absorb trailing elements
                li = stack[-1][3]
                wrap_leading_text(soup, li)
                current_sib = first_trailing
                while current_sib:
                    if is_section_boundary(current_sib, elem_to_idx.get(id(current_sib)), stack[-1][0], stack[-1][2]):
                        # Clear stack and stop
                        while stack:
                            stack.pop()
                        break
                    next_sib = current_sib.next_sibling
                    li.append(current_sib)
                    current_sib = next_sib
            else:
                # Threshold exceeded - don't absorb, close all lists
                while stack:
                    stack.pop()

    # Recursive processing for non-paragraph children
    for child in element.children:
        if child.name and child.name not in ['p', 'table', 'ul', 'ol', 'img', 'hr']:
            process_lists(soup, child)

def join_ul(soup):
    """
    Join all consecutive <ul> tags found anywhere in the document.
    Consecutive means 2 or more <ul> tags with no other tags between them.
    Works even when <ul> tags are not siblings.

    Args:
        soup: BeautifulSoup object to process

    Returns:
        soup: Processed BeautifulSoup object with consecutive <ul> tags joined
    """
    def get_next_element_in_doc_order(element):
        """Get the next element tag in document order, skipping text/comments."""
        current = element

        while current:
            # Try to find next sibling
            next_node = current.next_sibling
            while next_node:
                if isinstance(next_node, Tag):
                    return next_node
                next_node = next_node.next_sibling

            # No next sibling, go up to parent and continue
            current = current.parent
            # Stop at document root
            if not current or not hasattr(current, 'name') or current.name in [None, '[document]']:
                return None

        return None

    # Process until no more merges are needed
    changed = True
    while changed:
        changed = False

        # Find all <ul> tags
        ul_tags = soup.find_all('ul')

        for ul in ul_tags:
            # Check if this ul still exists in the tree (might have been removed)
            if ul.parent is None:
                continue

            # Get next element in document order
            next_elem = get_next_element_in_doc_order(ul)

            # If next element is also a <ul>, merge them
            if next_elem and next_elem.name == 'ul':
                # Move all <li> children from next_elem to ul
                for li in next_elem.find_all('li', recursive=False):
                    ul.append(li.extract())

                # Remove the now-empty next_elem
                next_elem.decompose()
                changed = True
                break  # Restart the search after a change

    return soup

def add_lists(soup):
    """
    Main function to process lists using comparative length rule for all absorption decisions.

    Args:
        soup: BeautifulSoup object to process

    Returns:
        soup: Processed BeautifulSoup object with lists converted
    """

    soup = add_prefixes_to_ol_li(soup)
    process_lists(soup, soup)
    soup = join_ul(soup)
    return soup
