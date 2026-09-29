from bs4 import NavigableString, Tag, Comment
from .utilities import is_empty_element, has_direct_nonempty_text

# get_table_grid(), get_rows(), normalize_tables(), clean_html_tables()
# fix_incorrect_structures() - orphaned elements
# propagate_inline_to_leaves() - illegal nesting fixes
# convert_pseudo_headers() - fake headers to real headers
# process_meter(), split_p_by_br() - paragraph restructuring


def get_rows(table):
    """Get all rows from a table."""
    rows = []
    for child in table.children:
        if child.name in ['thead', 'tbody', 'tfoot']:
            rows += child.find_all('tr', recursive=False)
        elif child.name == 'tr':
            rows.append(child)
    return rows

def get_table_grid(table):
    """Build a 2D grid representation of table cells."""
    rows = get_rows(table)
    if not rows:
        return [], 0, {}
    
    grid = [[] for _ in rows]
    cell_start = {}
    
    for row_i in range(len(rows)):
        tr = rows[row_i]
        current_col = 0
        for cell in tr.find_all(['td', 'th'], recursive=False):
            while current_col < len(grid[row_i]) and grid[row_i][current_col] is not None:
                current_col += 1
            
            try:
                colspan = int(cell.get('colspan', '1'))
            except ValueError:
                colspan = 1
                
            try:
                rowspan = int(cell.get('rowspan', '1'))
            except ValueError:
                rowspan = 1
                
            cell_start[cell] = (row_i, current_col)
            
            for r in range(row_i, min(row_i + rowspan, len(grid))):
                while current_col + colspan > len(grid[r]):
                    grid[r].append(None)
                for c in range(colspan):
                    grid[r][current_col + c] = cell
            current_col += colspan
            
    col_count = max(len(row) for row in grid) if grid else 0
    for row in grid:
        while len(row) < col_count:
            row.append(None)
            
    return grid, col_count, cell_start

def normalize_tables(soup):
    """Ensure all cells are within tr tags."""
    for table in soup.find_all('table', recursive=True):
        sections = [table] + table.find_all(['thead', 'tbody', 'tfoot'], recursive=False)
        for sec in sections:
            new_children = []
            current_tr = None
            for child in list(sec.children):
                if child.name == 'tr':
                    if current_tr:
                        new_children.append(current_tr)
                    current_tr = None
                    new_children.append(child)
                elif child.name in ['td', 'th']:
                    if current_tr is None:
                        current_tr = soup.new_tag('tr')
                    current_tr.append(child)
                else:
                    if current_tr:
                        new_children.append(current_tr)
                    current_tr = None
                    new_children.append(child)
            if current_tr:
                new_children.append(current_tr)
            sec.clear()
            for nc in new_children:
                sec.append(nc)

def clean_html_tables(soup):
    """Clean and normalize HTML tables."""
    normalize_tables(soup)

    # Clean up invalid direct children of table elements
    valid_table_children = {'tr', 'thead', 'tbody', 'tfoot', 'caption', 'colgroup'}
    valid_row_children = {'td', 'th'}
    for table in soup.find_all('table'):
        for child in list(table.children):
            if isinstance(child, Tag) and child.name not in valid_table_children:
                child.decompose()
        for tr in table.find_all('tr'):
            for child in list(tr.children):
                if isinstance(child, Tag) and child.name not in valid_row_children:
                    child.decompose()

    tables = list(soup.find_all('table', recursive=True))[::-1]
    
    for table in tables:
        # Handle nested tables within cells
        for tr in get_rows(table):
            for cell in tr.find_all(['td', 'th'], recursive=False):
                inner_tables = cell.find_all('table', recursive=False)
                for inner_table in inner_tables:
                    grid, _, _ = get_table_grid(inner_table)
                    non_empty_cells = set()
                    for row in grid:
                        for covering_cell in row:
                            if covering_cell is not None and not is_empty_element(covering_cell):
                                non_empty_cells.add(covering_cell)
                    if len(non_empty_cells) == 0:
                        inner_table.extract()
                    elif len(non_empty_cells) == 1:
                        single_cell = list(non_empty_cells)[0]
                        inner_table.replace_with(*single_cell.contents)
                        
        # Remove empty rows and columns
        grid, col_count, cell_start = get_table_grid(table)
        empty_rows = [i for i, row in enumerate(grid) 
                     if all(grid[i][j] is None or is_empty_element(grid[i][j]) 
                           for j in range(col_count))]
        empty_cols = [j for j in range(col_count) 
                     if all(grid[i][j] is None or is_empty_element(grid[i][j]) 
                           for i in range(len(grid)))]
        
        # Remove empty columns
        if empty_cols:
            set_empty_cols = set(empty_cols)
            for tr in get_rows(table):
                current_cells = tr.find_all(['td', 'th'], recursive=False)
                new_cells = []
                for cell in current_cells:
                    if cell not in cell_start:
                        continue
                    start_row, start_col = cell_start[cell]
                    try:
                        colspan = int(cell.get('colspan', '1'))
                    except ValueError:
                        colspan = 1
                    kept_count = sum(1 for c in range(start_col, start_col + colspan) 
                                   if c not in set_empty_cols)
                    if kept_count > 0:
                        if kept_count > 1:
                            cell['colspan'] = str(kept_count)
                        else:
                            cell.attrs.pop('colspan', None)
                        new_cells.append(cell)
                tr.clear()
                for cell in new_cells:
                    tr.append(cell)
                    
        # Remove empty rows
        rows = get_rows(table)
        for i in sorted(empty_rows, reverse=True):
            rows[i].extract()
            
        # Handle table conditions
        remaining_trs = get_rows(table)
        if not remaining_trs:
            if table.parent is not None:
                table.extract()
            else:
                soup.clear()
        else:
            all_cells = [cell for tr in get_rows(table) 
                        for cell in tr.find_all(['td', 'th'], recursive=False)]
            only_tables = all(
                cell.find_all('table', recursive=False) and not cell.find(
                    lambda tag: tag.name != 'table' and not is_empty_element(tag), recursive=False
                ) and not has_direct_nonempty_text(cell)
                for cell in all_cells if not is_empty_element(cell)
            ) if all_cells else False
            
            if only_tables and all_cells:
                inner_tables = []
                for cell in all_cells:
                    for inner in cell.find_all('table', recursive=False):
                        inner_tables.append(inner.extract())
                if table.parent is not None:
                    table.replace_with(*inner_tables)
                else:
                    soup.clear()
                    for it in inner_tables:
                        soup.append(it)

            elif len(all_cells) == 1:
                single_cell = all_cells[0]
                
                # Segregate content into blocks and inline/text
                block_tags = {'p', 'ul', 'ol', 'table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'br'}
                blocks = []
                inline_content = []
                
                for content in single_cell.contents[:]:
                    if isinstance(content, Tag):
                        if content.name == 'br':
                            # BR stays with inline content
                            inline_content.append(content)
                        elif content.name in block_tags:
                            # Other block tags cause a split
                            if inline_content:
                                p_tag = soup.new_tag('p')
                                for item in inline_content:
                                    p_tag.append(item)
                                blocks.append(p_tag)
                                inline_content = []
                            blocks.append(content)
                        else:
                            # Inline elements
                            inline_content.append(content)
                    else:
                        # Text content
                        if isinstance(content, NavigableString):
                            if content.strip():
                                inline_content.append(content)
                            elif inline_content:  # Preserve space between words
                                inline_content.append(' ')
                
                # Handle any remaining inline content
                if inline_content:
                    p_tag = soup.new_tag('p')
                    for item in inline_content:
                        p_tag.append(item)
                    blocks.append(p_tag)
                
                # Replace the table with the processed content
                if table.parent is not None:
                    table.replace_with(*blocks)
                else:
                    soup.clear()
                    for block in blocks:
                        soup.append(block)
                        
    return soup


def fix_incorrect_structures(soup):
    """
    Fix incorrect HTML structures by unwrapping orphaned structural elements.
    Simply unwraps elements that are not inside their required parent structures.
    Continues until all orphaned elements are processed.
    """
    # Define parent-child relationships that must be respected
    required_parents = {
        'li': {'ul', 'ol'},
        'td': {'tr'},
        'th': {'tr'},
        'tr': {'table', 'thead', 'tbody', 'tfoot'},
        'thead': {'table'},
        'tbody': {'table'},
        'tfoot': {'table'},
        'caption': {'table'},
        'colgroup': {'table'},
        'col': {'colgroup', 'table'}
    }

    # Table elements require DIRECT parenthood, not just ancestry
    # (e.g., td must be direct child of tr, not just have tr somewhere above)
    strict_parent_elements = {'td', 'th', 'tr', 'thead', 'tbody', 'tfoot', 'caption', 'colgroup', 'col'}

    # Keep processing until no more orphaned elements are found
    while True:
        orphaned = []

        # Find all orphaned elements in this pass
        for tag_name, valid_parents in required_parents.items():
            for element in soup.find_all(tag_name):
                has_valid_parent = False

                if tag_name in strict_parent_elements:
                    # For table elements, check DIRECT parent only
                    if element.parent and element.parent.name in valid_parents:
                        has_valid_parent = True
                else:
                    # For other elements (like li), check ancestry
                    current = element.parent
                    while current:
                        if current.name in valid_parents:
                            has_valid_parent = True
                            break
                        # Stop at body/html to avoid going too far up
                        if current.name in ['body', 'html', '[document]'] or current == soup:
                            break
                        current = current.parent

                if not has_valid_parent:
                    orphaned.append(element)

        # If no orphaned elements found, we're done
        if not orphaned:
            break

        # Process all orphaned elements found in this pass
        for element in orphaned:
            if element.name in ['caption', 'colgroup', 'col']:
                # These table-specific elements have no meaning outside tables
                element.decompose()
            else:
                # Just unwrap - preserve content in its original location
                element.unwrap()

    return soup


def propagate_inline_to_leaves(struct_tag, inline_name, inline_attrs, soup, structural_tags):
    """Propagate inline formatting to leaf nodes of structural tags."""
    expanded_structural = structural_tags | {'tbody', 'thead', 'tfoot', 'tr', 'td', 'th'}
    structural_children = [ch for ch in struct_tag.children if isinstance(ch, Tag) and ch.name in expanded_structural]
    if not structural_children:
        contents = list(struct_tag.contents)
        inline_copy = soup.new_tag(inline_name, attrs=inline_attrs)
        for cont in contents:
            inline_copy.append(cont)
        if inline_copy.get_text(strip=True):
            struct_tag.clear()
            struct_tag.append(inline_copy)
    else:
        for sch in structural_children:
            propagate_inline_to_leaves(sch, inline_name, inline_attrs, soup, structural_tags)


def convert_pseudo_headers(soup):
    """Convert bold uppercase paragraphs to headers."""
    # Find existing headers
    existing = [i for i in range(1, 7) if soup.find(f'h{i}')]

    # Calculate header levels
    if existing:
        lowest_existing = max(existing)  # Highest number = least important
        highest_existing = min(existing)  # Lowest number = most important
        base_level = min(6, max(4, lowest_existing + 1))
        # top_level: one level more important than highest existing, cannot be higher than h1
        top_level = max(1, highest_existing - 1)
    else:
        base_level = 4
        top_level = 3

    # Calculate middle level: between top and base if there's room
    middle_level = base_level - 1 if base_level > top_level + 1 else base_level

    structural_tags = {'p', 'ul', 'ol', 'li', 'table', 'thead', 'tbody', 'tfoot',
                      'tr', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'img'}

    def is_spaced_single_letters(text):
        """Check if text consists of spaced single letters (e.g., 'Ո Ր Ո Շ ՈՒ Մ')."""
        import re
        # Normalize &nbsp; to regular spaces
        text = text.replace('\u00a0', ' ').replace('&nbsp;', ' ')
        # Remove all spaces
        text_no_spaces = text.replace(' ', '')
        if not text_no_spaces:
            return False
        # Check each character/letter
        # ՈՒ (U+0548 U+0552) is considered a single letter
        letters = []
        i = 0
        while i < len(text_no_spaces):
            if i + 1 < len(text_no_spaces) and text_no_spaces[i:i+2] == 'ՈՒ':
                letters.append('ՈՒ')
                i += 2
            else:
                letters.append(text_no_spaces[i])
                i += 1

        # Check if original text has spaces between letters
        # Pattern: letter (space) letter (space) ...
        pattern_parts = []
        for letter in letters:
            if letter == 'ՈՒ':
                pattern_parts.append('ՈՒ')
            else:
                pattern_parts.append(re.escape(letter))
        pattern = r'^\s*' + r'\s+'.join(pattern_parts) + r'\s*$'
        # Replace &nbsp; in original text for matching
        text_normalized = text.replace('&nbsp;', ' ')
        return bool(re.match(pattern, text_normalized))

    def section_marker_word(p):
        """Structural word of a section-marker paragraph: its first line
        (text before the first <br>) is spaced single letters plus a
        number, like 'Գ Լ ՈՒ Խ 1', 'Բ Ա Ժ Ի Ն 2', 'Ո Ր Ո Շ ՈՒ Մ N 59'. The
        marker word may be followed by its title in the same paragraph.
        Letterhead lines ('Օ Ր Ե Ն Ք Ը') carry no number and are not
        markers."""
        import re
        parts = []
        for node in p.descendants:
            if isinstance(node, Tag):
                if node.name == 'br':
                    break
            else:
                parts.append(str(node))
        first_line = ''.join(parts).replace('\u00a0', ' ').strip()
        m = re.match(r'((?:[Ա-Ֆ](?:Ւ)?\s+)+)(?:N\s*)?\d+\s*$', first_line)
        return m.group(1).replace(' ', '') if m else None

    def is_pseudo_header(p):
        if not p.parent or p.name != 'p' or not (p.find('strong') or p.find('b')):
            return False
        if any(p.find(tag) for tag in structural_tags):
            return False
        # All text must be bold
        for node in p.descendants:
            if isinstance(node, NavigableString) and not isinstance(node, Comment) and node.strip():
                parent = node.parent
                while parent and parent != p:
                    if parent.name in ['strong', 'b']:
                        break
                    parent = parent.parent
                else:
                    return False
        # All uppercase
        text = p.get_text().strip()
        return text and sum(c.isupper() for c in text) > 2 and sum(c.islower() for c in text) == 0

    #Process root/body elements
    processed = set()
    for container in ([soup.body] if soup.body else [soup]):
        # Track if we're at the very beginning
        first_content_elem = None
        for child in container.children:
            if isinstance(child, Tag):
                first_content_elem = child
                break

        for elem in list(container.children):
            if not isinstance(elem, Tag) or id(elem) in processed:
                continue

            if is_pseudo_header(elem):
                seq = [elem]
                processed.add(id(elem))

                # Collect consecutive pseudo-headers
                current = elem
                while True:
                    nxt = current.next_sibling
                    while nxt and isinstance(nxt, str) and not nxt.strip():
                        nxt = nxt.next_sibling
                    if nxt and isinstance(nxt, Tag) and is_pseudo_header(nxt):
                        seq.append(nxt)
                        processed.add(id(nxt))
                        current = nxt
                    else:
                        break

                # Determine which level to use
                is_at_beginning = (elem == first_content_elem)
                first_line_text = seq[0].get_text()
                has_spaced_letters = is_spaced_single_letters(first_line_text)

                if is_at_beginning:
                    level = top_level
                elif has_spaced_letters:
                    level = middle_level
                else:
                    level = base_level

                def merge_into(header, lines):
                    for p in lines:
                        header.append(soup.new_tag('br'))
                        for c in list(p.contents):
                            header.append(c)
                        p.decompose()

                def merge_until_by_length(start, stop):
                    # Index of first line longer than its predecessor, or stop
                    for i in range(start, stop):
                        if len(seq[i].get_text().strip()) > len(seq[i-1].get_text().strip()):
                            return i
                    return stop

                def make_header(head, name, lines):
                    head.name = name
                    merge_into(head, lines)
                    for b in head.find_all(['strong', 'b']):
                        b.unwrap()

                # Section-marker lines start their own headers; the length
                # rule alone would glue a marker into the previous header and
                # orphan its title. Known structural words get a level depth
                # ('ԲԱԺԻՆ' is a subsection of 'ԳԼՈՒԽ'); unknown words sit at
                # base level.
                marker_depth = {'ԳԼՈՒԽ': 0, 'ԲԱԺԻՆ': 1}
                marker_words = [section_marker_word(p) for p in seq]
                marker_positions = [i for i, w in enumerate(marker_words) if w]

                if not marker_positions:
                    make_header(seq[0], f'h{level}',
                                seq[1:merge_until_by_length(1, len(seq))])
                else:
                    # Pre-marker segment: length rule, unchanged
                    first_marker = marker_positions[0]
                    if first_marker > 0:
                        make_header(seq[0], f'h{level}',
                                    seq[1:merge_until_by_length(1, first_marker)])
                    # Marker segments: split at every marker; a marker
                    # absorbs the first following line when it is not itself
                    # a marker, then the length rule resumes
                    for n, m in enumerate(marker_positions):
                        if m == 0 and elem == first_content_elem:
                            name = f'h{top_level}'
                        else:
                            name = f'h{min(6, base_level + marker_depth.get(marker_words[m], 0))}'
                        next_marker = (marker_positions[n + 1]
                                       if n + 1 < len(marker_positions)
                                       else len(seq))
                        make_header(seq[m], name,
                                    seq[m + 1:merge_until_by_length(m + 2, next_marker)])

    return soup


