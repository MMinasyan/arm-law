from bs4 import BeautifulSoup, NavigableString, Tag
from typing import List, Union
import re
import copy
from .unescape_markdown import unescape_markdown


inline_tags = {'a', 'b', 'strong', 'i', 'em', 'u', 'sup', 'sub'}


def handle_text(element: NavigableString, context: dict) -> str:
    """
    Handles text nodes by escaping special Markdown characters that can break formatting.
    Escaping is done blindly for now; unescaping where safe will be handled in future steps.
    """
    text = str(element)
    
    # Special handling for annotation tags - don't escape LaTeX
    if context.get('type') == 'annotation':
        return text

    # If this is just whitespace (newlines, spaces from HTML formatting), ignore it
    if not text.strip():
        return ''
    
    # Normalize internal whitespace (convert newlines/tabs to spaces, collapse multiple)
    text = re.sub(r'\s+', ' ', text)
    
    # Preserve single boundary spaces but remove excessive whitespace
    # Check if text starts/ends with space before stripping
    starts_with_space = text[0] == ' '
    ends_with_space = text[-1] == ' '
    
    # Strip the text
    text = text.strip()
    
    # Restore single boundary spaces if they existed
    if starts_with_space:
        text = ' ' + text
    if ends_with_space:
        text = text + ' '

    # First, escape backslashes
    text = text.replace('\\', '\\\\')

    # Then, escape other special characters
    specials = '*_`~#+-=.|><[]()'
    for char in specials:
        text = text.replace(char, f'\\{char}')

    return text


def get_child_context(parent_context: dict, parent_element: Tag) -> dict:
    """
    Creates a child context based on parent context and element type.
    Tracks nesting levels, list types, table context, and other structural information.
    """
    # Deep copy parent context to avoid ANY mutation issues
    child_context = copy.deepcopy(parent_context)
    
    # Update based on parent element type
    tag_name = parent_element.name
    
    # Track the immediate parent type
    child_context['parent_type'] = parent_context.get('type', 'root')
    
    # Update type based on current tag
    child_context['type'] = tag_name
    
    # Handle list contexts
    if tag_name in ['ul', 'ol']:
        # For nested lists, increase indent level
        child_context['indent_level'] = parent_context.get('indent_level', 0) + 1
        # Store the list type for children to access
        child_context['parent_list_type'] = tag_name
        
    elif tag_name == 'li':
        # Inherit indent level from parent list
        child_context['indent_level'] = parent_context.get('indent_level', 0)
        # Set parent_type to the actual list type (ul or ol)
        child_context['parent_type'] = parent_context.get('parent_list_type', 'root')
        # Note: List item index tracking would need to be done differently
        # when we implement list formatting
            
    # Handle table contexts
    elif tag_name == 'table':
        child_context['in_table'] = True
        
    elif tag_name == 'tr':
        child_context['in_table'] = parent_context.get('in_table', False)
        # Note: Row/column tracking would be done locally in format_table
            
    elif tag_name in ['td', 'th']:
        child_context['in_table'] = parent_context.get('in_table', False)
        child_context['in_table_cell'] = True
            
    elif tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        child_context['heading_level'] = int(tag_name[1])
    
    # Propagate critical context flags for complex nesting
    # List item context propagates to all descendants
    if parent_context.get('type') == 'li' or parent_context.get('in_list_item'):
        child_context['in_list_item'] = True
        # Sub-blocks in list items inherit the list's indent level
        if tag_name in ['p', 'table', 'ul', 'ol', 'figure']:
            child_context['indent_level'] = parent_context.get('indent_level', 0)
    
    # Table cell context propagates to all descendants
    if parent_context.get('in_table_cell'):
        child_context['in_table_cell'] = True
    
    # Table context propagates
    if parent_context.get('in_table'):
        child_context['in_table'] = True
    
    return child_context


def apply_inline_formatting(tag_name: str, contents: str, attrs: dict, context: dict) -> str:
    """
    Applies inline markdown formatting based on tag type.
    
    Args:
        tag_name: Name of the inline tag (a, b, strong, i, em, u, sup, sub)
        contents: Already processed inner content
        attrs: Tag attributes
        context: Current processing context
    
    Returns:
        Formatted markdown string
    """
    # Don't strip internal newlines (from <br> tags), only leading/trailing whitespace
    # But be careful not to strip the newlines themselves
    if '\n' in contents:
        # Split by newlines, strip each part, rejoin
        parts = contents.split('\n')
        parts = [p.strip() for p in parts]
        contents = '\n'.join(parts)
    else:
        contents = contents.strip()
    
    if not contents and tag_name != 'a':  # Links can be empty
        return ''
    
    # Handle each inline tag type
    if tag_name in ['b', 'strong']:
        return f'**{contents}**'
    
    elif tag_name in ['i', 'em']:
        return f'*{contents}*'
    
    elif tag_name == 'u':
        # Markdown doesn't have native underline, use HTML
        return f'<u>{contents}</u>'
    
    elif tag_name == 'sup':
        return f'<sup>{contents}</sup>'
    
    elif tag_name == 'sub':
        return f'<sub>{contents}</sub>'
    
    elif tag_name == 'a':
        href = attrs.get('href', '')
        if not href:
            # No href, just return the text
            return contents
        # Escape closing parens in href to avoid breaking markdown link syntax
        href = href.replace(')', '\\)')
        return f'[{contents}]({href})'
    
    else:
        # Unknown inline tag, just return contents
        return contents


def format_list(tag_name: str, contents: str, attrs: dict, context: dict) -> str:
    return contents


def format_list_item(tag_name: str, contents: str, attrs: dict, context: dict) -> str:
    # Check parent_list_type, not parent_type!
    parent_list_type = context.get('parent_list_type')  # CHANGED THIS LINE
    
    if parent_list_type == 'ul':  # CHANGED THIS LINE
        return format_ul_item(contents, context)
    elif parent_list_type == 'ol':  # CHANGED THIS LINE
        return format_ol_item(contents, attrs, context)
    else:
        # Fallback - could be a list item not in a list context (edge case)
        return contents


def format_ul_item(contents: str, context: dict) -> str:
    indent_level = context.get('indent_level', 0)
    indent = '    ' * max(0, indent_level - 1)  # Level 1 has no indent
    
    # Strip the contents to remove trailing whitespace
    contents = contents.strip()
    
    # If contents is empty or whitespace only, just return the prefixed empty line
    if not contents:
        return f"{indent}- "
    
    # Special case if contents starts with a nested list without preceding text
    if re.match(r'^\s*[-*\d]', contents):
        return f"{indent}- \n{contents}"
    
    # Split contents into lines
    lines = contents.split('\n')
    
    # First line gets the prefix
    result = [f"{indent}- {lines[0]}"]
    
    # Continuation indent aligns with text after prefix (2 spaces after -)
    cont_indent = '    ' * indent_level
    
    for line in lines[1:]:
        if line.strip():
            if line.startswith('    '):
                result.append(indent + line)
            else:
                result.append(cont_indent + line)
        else:
            result.append('')
    
    return '\n'.join(result)


def format_ol_item(contents: str, attrs: dict, context: dict) -> str:
    indent_level = context.get('indent_level', 0)
    indent = '    ' * max(0, indent_level - 1)
    
    # If contents is empty or whitespace only, check for nested structures or use fallback
    stripped = contents.strip()
    if not stripped:
        return indent  # Just indent for empty
    
    # Special case if contents is only a nested list without preceding text
    if re.match(r'^\s{4,}[-*\d]', contents):
        return f"{indent}\n{contents}"
    
    # Extract prefix with simplified regex: first non-space after opening formatting
    pattern = r'^((?:\*+|<u>)*)([^\s\*<>]+)(\s*)'
    match = re.match(pattern, stripped)
    
    if match:
        opening_format = match.group(1)
        escaped_prefix = match.group(2)
        space_after = match.group(3)
        
        # UNESCAPE the prefix - remove all backslashes that were added by handle_text
        prefix = re.sub(r'\\(.)', r'\1', escaped_prefix)
        
        # Normalize only Armenian period  
        normalized_prefix = prefix.replace('\\', '').replace('․', '.') + ' '
        
        # Get remaining content after prefix
        remaining = stripped[match.end():]
        
        # Clean up leftover formatting
        remaining = re.sub(r'^(?:\*+|\*+|<u>|</u>)+', '', remaining)  # General inline cleanup
        remaining = re.sub(r'^\*+\*+', '', remaining)  # * or **
        remaining = re.sub(r'^_*_*', '', remaining)  # _ or __ if any
        remaining = re.sub(r'^<u></u>', '', remaining)
        remaining = re.sub(r'^</u>', '', remaining)
        remaining = remaining.lstrip()
        
    else:
        # Rare no-match, no fallback as per instructions
        normalized_prefix = ''
        remaining = contents.strip()
    
    if not remaining:
        return f"{indent}{normalized_prefix}".rstrip()
    
    # Split remaining into lines
    lines = remaining.split('\n')
    
    # First line gets prefix
    result = [f"{indent}{normalized_prefix}{lines[0]}"]
    
    # Continuation indent aligns with text after prefix
    cont_indent = '    ' * indent_level
    
    for line in lines[1:]:
        if line.strip():
            if line.startswith('    '):
                result.append(indent + line)
            else:
                result.append(cont_indent + line)
        else:
            result.append('')
    
    return '\n'.join(result)


def format_table(tag_name: str, contents: str, attrs: dict, context: dict, element: Tag = None) -> str:
    """
    Format tables with proper structure, handling colspan/rowspan.
    Creates a 2D grid representation first, then converts to markdown.
    """
    if not element:
        # Fallback if no element provided
        return contents
    
    # First, analyze table structure to create a 2D grid
    rows = element.find_all('tr', recursive=False)
    if not rows:
        # Also check in thead, tbody, tfoot
        rows = []
        for section in ['thead', 'tbody', 'tfoot']:
            section_elem = element.find(section)
            if section_elem:
                rows.extend(section_elem.find_all('tr', recursive=False))
    
    if not rows:
        return contents
    
    # Determine table dimensions
    max_cols = 0
    for row in rows:
        cells = row.find_all(['td', 'th'], recursive=False)
        col_count = sum(int(cell.get('colspan', 1)) for cell in cells)
        max_cols = max(max_cols, col_count)
    
    # Create 2D grid
    grid = [['' for _ in range(max_cols)] for _ in range(len(rows))]
    cell_spans = [[None for _ in range(max_cols)] for _ in range(len(rows))]
    
    # Fill the grid
    for row_idx, row in enumerate(rows):
        cells = row.find_all(['td', 'th'], recursive=False)
        col_idx = 0
        
        for cell in cells:
            # Skip columns that are occupied by rowspan from previous rows
            while col_idx < max_cols and cell_spans[row_idx][col_idx] is not None:
                col_idx += 1
            
            if col_idx >= max_cols:
                break
            
            colspan = int(cell.get('colspan', 1))
            rowspan = int(cell.get('rowspan', 1))
            
            # Process cell content recursively
            cell_context = get_child_context(context, cell)
            cell_contents = []
            for child in cell.children:
                child_md = process_element(child, cell_context)
                if child_md:
                    cell_contents.append(child_md)
            
            # Combine cell contents
            cell_text = combine_contents(cell_contents, cell.name, cell_context)
            
            # Replace newlines with <br> with spaces around it
            cell_text = cell_text.strip()
            if '\n' in cell_text:
                cell_text = cell_text.replace('\n\n', '\n')
                # Replace newlines with " <br> "
                cell_text = cell_text.replace('\n', ' <br> ')
            
            # Fill all cells covered by colspan/rowspan
            for r in range(row_idx, min(row_idx + rowspan, len(rows))):
                for c in range(col_idx, min(col_idx + colspan, max_cols)):
                    grid[r][c] = cell_text
                    if r > row_idx or c > col_idx:
                        cell_spans[r][c] = (row_idx, col_idx)  # Mark as spanned
            
            col_idx += colspan
    
    # Generate markdown table
    md_lines = []
    
    # Check if first row contains headers (any th elements)
    first_row_cells = rows[0].find_all(['td', 'th'], recursive=False) if rows else []
    has_header = len(first_row_cells) > 0 and any(cell.name == 'th' for cell in first_row_cells)
    
    if not has_header:
        # Add empty header row
        md_lines.append('| ' + ' | '.join([''] * max_cols) + ' |')
        md_lines.append('|' + '|'.join(['---'] * max_cols) + '|')
    
    # Add rows
    for row_idx, row in enumerate(grid):
        if row_idx == 0 and has_header:
            # This is the header row
            md_lines.append('| ' + ' | '.join(cell if cell else '' for cell in row) + ' |')
            md_lines.append('|' + '|'.join(['---'] * max_cols) + '|')
        else:
            # Regular row
            md_lines.append('| ' + ' | '.join(cell if cell else '' for cell in row) + ' |')
    
    return '\n'.join(md_lines)


def format_math(tag_name: str, contents: str, attrs: dict, context: dict, element: Tag = None) -> str:
    """
    Format math content as inline or display math.
    Contents should contain only the LaTeX from the annotation tag.
    """
    # Find the annotation tag within the math element
    if element:
        annotation = element.find('annotation')
        if annotation:
            latex = annotation.get_text().strip()
        else:
            latex = contents.strip()
    else:
        latex = contents.strip()
    
    if not latex:
        # No LaTeX content found
        return ''
    
    # Strip {\displaystyle ...} wrapper if present
    if latex.startswith('{\\displaystyle ') and latex.endswith('}'):
        latex = latex[15:-1].strip()
    
    # Determine if it's display or inline math
    is_display = False
    
    # Check for display style indicators
    if '\\displaystyle' in latex:
        is_display = True
    elif any(env in latex for env in ['\\begin{', '\\end{', '\\[', '\\]']):
        is_display = True
    
    # For this specific case, since it had displaystyle, it's display math
    if element and element.find('annotation'):
        annotation_text = element.find('annotation').get_text()
        if '\\displaystyle' in annotation_text:
            is_display = True
    
    if is_display:
        # Display math with $$ 
        return f'$$ {latex} $$'
    else:
        # Inline math with single $ - THIS LINE IS NOW COMPLETE
        return f'${latex}$'


def format_figure(tag_name: str, contents: str, attrs: dict, context: dict) -> str:
    """
    Format figure elements. 
    By this point, img and figcaption children are already processed.
    """
    # Figure is just a container, return its contents
    # The img and figcaption inside are already formatted
    return contents


def format_figcaption(tag_name: str, contents: str, attrs: dict, context: dict) -> str:
    """
    Format figcaption as a blockquote with > prefix.
    Handle indentation if nested.
    """
    # Get current indentation level
    indent_level = context.get('indent_level', 0)
    indent = '    ' * indent_level  # 4 spaces per level
    
    # Format as blockquote with proper indentation
    # Split by lines in case figcaption has multiple lines
    lines = contents.split('\n')
    quoted_lines = []
    for line in lines:
        if line.strip():
            quoted_lines.append(f"{indent}> {line}")
        else:
            # Empty line still needs > prefix
            quoted_lines.append(f"{indent}>")
    
    return '\n'.join(quoted_lines)


def apply_block_formatting(tag_name: str, contents: str, attrs: dict, context: dict, element: Tag = None) -> str:
    """
    Applies block markdown formatting based on tag type.
    """
    if contents is None:
        contents = ''
    
    # Handle block tags
    if tag_name == 'p':
        return contents + '\n'
    
    elif tag_name == 'br':
        return '\n'
    
    elif tag_name == 'hr':
        return '---\n'
    
    elif tag_name in ['ul', 'ol']:
        return format_list(tag_name, contents, attrs, context)
    
    elif tag_name == 'li':
        return format_list_item(tag_name, contents, attrs, context)
    
    elif tag_name == 'img':
        src = attrs.get('src', '')
        alt = attrs.get('alt', contents.strip())  # Use alt attr if present, else contents
        width = attrs.get('width', '')
        height = attrs.get('height', '')
        img_md = f'![{alt}]({src})'
        if width or height:
            img_md = f'<img src="{src}" alt="{alt}" width="{width}" height="{height}">'
        return img_md + '\n\n'
    
    elif tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        level = int(tag_name[1])  # Extract from tag_name, not context
        return '#' * level + ' ' + contents + '\n\n'
    
    # BUG FIX: Add missing 'table' case
    elif tag_name == 'table':
        return format_table(tag_name, contents, attrs, context, element)
    
    elif tag_name in ['tr', 'td', 'th', 'thead', 'tbody', 'tfoot']:
        # Table sub-elements are handled by their parent processors
        return contents
    
    elif tag_name == 'math':
        return format_math(tag_name, contents, attrs, context, element)
    
    elif tag_name == 'figure':
        return format_figure(tag_name, contents, attrs, context)
    
    elif tag_name == 'figcaption':
        return format_figcaption(tag_name, contents, attrs, context)
    
    # Math-related tags that appear inside <math>
    elif tag_name in ['mi', 'mo', 'mn', 'mtext', 'mrow', 'mfrac', 'msqrt', 'mroot', 
                      'mstyle', 'msub', 'msup', 'msubsup', 'semantics',
                      'munder', 'mover', 'munderover', 'mmultiscripts', 'mtable', 
                      'mtr', 'mtd', 'maction']:
        # Return empty string - we only care about annotation content
        return ''
    
    elif tag_name == 'annotation':
        # Return the LaTeX content directly
        return contents
    
    # Unknown block tag - just return contents
    else:
        return contents


def combine_contents(child_contents: List[str], tag_name: str, context: dict) -> str:
    """
    Combines child child_contents based on parent tag type.
    Most formatting decisions are deferred to apply_block_formatting.
    """
    if not child_contents:
        return ''
    
    # For table cells, join with \n to preserve block separation (will be replaced with <br> later)
    if tag_name in ['td', 'th']:
        result_parts = []
        for child_md in child_contents:
            # Special case: preserve newlines from <br> tags
            if child_md == '\n':
                result_parts.append(child_md)
                continue
                
            stripped = child_md.strip()
            if stripped:
                # Check for block elements
                if re.match(r'^\s*([-*]\s|\d+[.)]\s|#\s|\|\s|!\[|\$|>\s|---)', stripped):
                    if result_parts:
                        result_parts.append('\n')  # Single newline, not double!
                result_parts.append(child_md)
        return ''.join(result_parts)
    
    # For list items, special handling for multiple blocks
    elif tag_name == 'li':
        result_parts = []
        is_first = True
        indent_level = context.get('indent_level', 0)  # Get indent level
        continuation_indent = '    ' * indent_level      # 4 spaces per level
        
        for child_md in child_contents:
            stripped = child_md.strip()
            if stripped:
                if is_first:
                    result_parts.append(child_md.rstrip('\n'))
                    is_first = False
                else:
                    result_parts.append('\n\n')
                    lines = stripped.split('\n')
                    indented_lines = [continuation_indent + line for line in lines]  # Use 4 spaces per level
                    result_parts.append('\n'.join(indented_lines))
        return ''.join(result_parts)
    
    # For paragraphs, join with '' to preserve \n from br
    elif tag_name == 'p':
        return ''.join(child_contents)
    
    # For lists, join with \n\n to separate items with blank lines
    elif tag_name in ['ul', 'ol']:
        return '\n\n'.join(child_contents)
    
    # For other containers, join with ''
    else:
        return ''.join(child_contents)


def process_element(element: Union[NavigableString, Tag], context: dict = None) -> str:
    """
    Processes a single element (text or tag) recursively.
    """
    if context is None:
        context = {'type': 'root', 'indent_level': 0}

    # Step 3: Determine element type
    if isinstance(element, NavigableString):
        # Step 4: Handle text node
        return handle_text(element, context)

    elif isinstance(element, Tag):
        # Step 5: Get all attributes as-is
        attrs = element.attrs.copy()
        
        # Minimal handling only for required attributes
        if element.name == 'a' and 'href' not in attrs:
            attrs['href'] = ''
        if element.name == 'img' and 'src' not in attrs:
            attrs['src'] = ''
        
        # Special handling for li elements
        if element.name == 'li':
            # Check if all child tags are inline (or if there are no tags)
            has_block_tags = False
            for child in element.children:
                if isinstance(child, Tag) and child.name not in inline_tags:
                    has_block_tags = True
                    break
            
            if not has_block_tags:
                # No block tags - wrap content in a virtual <p> tag
                wrapped = BeautifulSoup(f'<p>{element.decode_contents()}</p>', 'html.parser')
                p_element = wrapped.find('p')
                
                # Process the virtual <p> tag with li's context
                p_context = get_child_context(context, element)
                p_context['type'] = 'p'
                p_md = process_element(p_element, p_context)
                
                # Then format as list item
                return apply_block_formatting('li', p_md, attrs, context)
        
        # Step 6: Recurse into tag contents
        child_contents: List[str] = []
        for child in element.children:
            child_md = process_element(child, get_child_context(context, element))
            if child_md:
                child_contents.append(child_md)

        contents = combine_contents(child_contents, element.name, context)

        # Steps 7-8: Apply formatting based on tag type
        if element.name in inline_tags:
            return apply_inline_formatting(element.name, contents, attrs, context)
        else:
            # Pass original element for tables that need structure
            # BUG FIX: Also pass element for 'math' tag
            if element.name in ['table', 'math']:
                return apply_block_formatting(element.name, contents, attrs, context, element)
            else:
                return apply_block_formatting(element.name, contents, attrs, context)

    else:
        # Ignore other types (e.g., comments, doctype)
        return ''


def collect_outputs(parts: List[str]) -> str:
    """Combine top-level parts with proper separation"""
    # Trim each part to avoid extra whitespace
    trimmed_parts = [p.strip() for p in parts if p.strip()]
    return '\n\n'.join(trimmed_parts)


def prepare_soup(soup: BeautifulSoup) -> BeautifulSoup:
    body = soup.find('body')
    if body:
        inner_html = body.decode_contents()
        return BeautifulSoup(inner_html, 'html.parser')
    return soup


def html_to_markdown(html: str) -> str:
    """
    Main entry point for conversion.
    """
    soup = BeautifulSoup(html, 'html.parser')
    processed_soup = prepare_soup(soup)

    # Step 2: Start iterating through the body's children
    markdown_parts: List[str] = []
    for child in processed_soup.children:
        part = process_element(child)
        if part:
            markdown_parts.append(part)

    # Step 10: Collect and combine outputs with proper separation
    md = collect_outputs(markdown_parts)
    return unescape_markdown(md)