import re

def unescape_markdown(md: str) -> str:
    """
    Intelligently unescapes markdown special characters.
    - unescapes characters that were escaped in handle_text() function if unescaping them won't create/change formatting or render differently.
    - keeps escaped those that will create/change formatting or render differently if unescaped.
    - FULLY unescapes everything inside code blocks and inline code
    """
    
    lines = md.split('\n')
    result_lines = []
    
    # Track if we're in a fenced code block
    in_fenced_code = False
    fence_pattern = None
    
    # First pass: identify table context for pipes
    keep_pipes_escaped_lines = set()
    
    for i in range(len(lines)):
        # Skip if in code block
        if lines[i].strip().startswith('```'):
            continue
            
        # Check what line would look like with pipes unescaped
        test_line = lines[i].replace('\\|', '|').strip()
        
        # Would this form a separator row?
        test_with_dashes = test_line.replace('\\-', '-')
        if re.match(r'^\|[\s:|-]+\|$', test_with_dashes) and '-' in test_with_dashes:
            inner = test_with_dashes[1:-1]
            sep_chars = sum(1 for c in inner if c in '-:| \t')
            if sep_chars == len(inner):
                keep_pipes_escaped_lines.add(i)
                if i > 0:
                    keep_pipes_escaped_lines.add(i - 1)
                j = i + 1
                while j < len(lines):
                    next_test = lines[j].replace('\\|', '|').strip()
                    if next_test.startswith('|') and next_test.endswith('|') and '|' in next_test[1:-1]:
                        keep_pipes_escaped_lines.add(j)
                        j += 1
                    else:
                        break
    
    # Process each line
    for i, line in enumerate(lines):
        # Check for fenced code block markers
        if line.strip().startswith('```'):
            if not in_fenced_code:
                # Starting a code block
                in_fenced_code = True
                fence_pattern = re.match(r'^(\s*)(```+)', line)
            elif fence_pattern:
                # Check if this closes the code block
                close_pattern = re.match(r'^(\s*)(```+)', line)
                if close_pattern and len(close_pattern.group(2)) >= len(fence_pattern.group(2)):
                    in_fenced_code = False
                    fence_pattern = None
            
            # Process the fence line itself normally
            result_lines.append(process_line(line, i in keep_pipes_escaped_lines, in_code_block=False))
        elif in_fenced_code:
            # Inside a fenced code block - unescape EVERYTHING
            result_lines.append(unescape_all(line))
        else:
            # Normal line - process with inline code detection
            result_lines.append(process_line_with_inline_code(line, i in keep_pipes_escaped_lines))
    
    return '\n'.join(result_lines)


def unescape_all(text: str) -> str:
    """Unescape ALL escaped characters (for use inside code blocks)."""
    result = []
    i = 0
    
    while i < len(text):
        if i < len(text) - 1 and text[i] == '\\':
            next_char = text[i+1]
            if next_char == '\\':
                # Escaped backslash -> single backslash
                result.append('\\')
                i += 2
            elif next_char in '*_`~#+-=.|><[](){}!':
                # Escaped special char -> just the char
                result.append(next_char)
                i += 2
            else:
                # Not an escape sequence
                result.append(text[i])
                i += 1
        else:
            result.append(text[i])
            i += 1
    
    return ''.join(result)


def process_line_with_inline_code(line: str, keep_pipes_escaped: bool = False) -> str:
    """Process a line, handling inline code sections specially."""
    
    # Find all inline code spans (but skip escaped backticks)
    code_spans = []
    
    # First, identify positions of escaped backticks to exclude them
    escaped_backtick_positions = set()
    i = 0
    while i < len(line) - 1:
        if line[i] == '\\' and line[i+1] == '`':
            escaped_backtick_positions.add(i+1)  # Position of the backtick
            i += 2
        else:
            i += 1
    
    # Find double-backtick code spans (excluding escaped ones)
    i = 0
    while i < len(line) - 1:
        if line[i:i+2] == '``' and i not in escaped_backtick_positions and i+1 not in escaped_backtick_positions:
            # Found opening ``
            j = i + 2
            while j < len(line) - 1:
                if line[j:j+2] == '``' and j not in escaped_backtick_positions and j+1 not in escaped_backtick_positions:
                    # Found closing ``
                    code_spans.append((i, j+2))
                    i = j + 2
                    break
                j += 1
            else:
                i += 1
        else:
            i += 1
    
    # Find single-backtick code spans (excluding escaped ones and not overlapping with double)
    i = 0
    while i < len(line):
        if line[i] == '`' and i not in escaped_backtick_positions:
            # Check if this is part of an already found double-backtick span
            in_existing = False
            for start, end in code_spans:
                if start <= i < end:
                    in_existing = True
                    break
            
            if not in_existing:
                # Found opening `
                j = i + 1
                while j < len(line):
                    if line[j] == '`' and j not in escaped_backtick_positions:
                        # Found closing `
                        code_spans.append((i, j+1))
                        i = j + 1
                        break
                    j += 1
                else:
                    i += 1
            else:
                i += 1
        else:
            i += 1
    
    # Sort spans by start position
    code_spans.sort()
    
    # Build result by processing sections
    result = []
    last_end = 0
    
    for start, end in code_spans:
        # Process text before code span normally
        if start > last_end:
            result.append(process_line(line[last_end:start], keep_pipes_escaped))
        
        # Add code span with everything unescaped
        code_content = line[start:end]
        # Find the backticks and content
        if code_content.startswith('``'):
            # Double backtick
            inner_start = 2
            inner_end = len(code_content) - 2
            result.append('``' + unescape_all(code_content[inner_start:inner_end]) + '``')
        elif code_content.startswith('`'):
            # Single backtick
            inner_start = 1
            inner_end = len(code_content) - 1
            result.append('`' + unescape_all(code_content[inner_start:inner_end]) + '`')
        else:
            # Shouldn't happen, but handle gracefully
            result.append(code_content)
        
        last_end = end
    
    # Process remaining text after last code span
    if last_end < len(line):
        result.append(process_line(line[last_end:], keep_pipes_escaped))
    
    return ''.join(result)


def process_line(line: str, keep_pipes_escaped: bool = False, in_code_block: bool = False) -> str:
    """Process a single line, unescaping safe characters."""
    
    if in_code_block:
        return unescape_all(line)
    
    # First pass: identify all escape sequences
    escape_map = {}  # position -> (character, is_escaped_backslash)
    i = 0
    
    while i < len(line):
        if i < len(line) - 1 and line[i] == '\\':
            next_char = line[i+1]
            if next_char == '\\':
                escape_map[i] = ('\\', True)
                i += 2
            elif next_char in '*_`~#+-=.|><[](){}!':
                escape_map[i] = (next_char, False)
                i += 2
            else:
                i += 1
        else:
            i += 1
    
    # Process asterisks
    asterisk_groups = []
    processed_asterisks = set()
    
    for pos in sorted(escape_map.keys()):
        char, is_backslash = escape_map[pos]
        if char == '*' and not is_backslash and pos not in processed_asterisks:
            group = [pos]
            processed_asterisks.add(pos)
            next_pos = pos + 2
            
            while next_pos in escape_map:
                next_char, next_is_backslash = escape_map[next_pos]
                if next_char == '*' and not next_is_backslash:
                    group.append(next_pos)
                    processed_asterisks.add(next_pos)
                    next_pos += 2
                else:
                    break
            
            asterisk_groups.append(group)
    
    # Find matching asterisk emphasis pairs
    paired_asterisk_positions = set()
    used_asterisk_groups = set()
    
    for i, group1 in enumerate(asterisk_groups):
        if i in used_asterisk_groups:
            continue
            
        group1_start = group1[0]
        group1_count = len(group1)
        group1_end = group1_start + group1_count * 2
        
        # Check if followed by non-space
        if group1_end >= len(line) or line[group1_end] == ' ':
            continue
        
        # Look for matching group
        for j in range(i + 1, len(asterisk_groups)):
            if j in used_asterisk_groups:
                continue
                
            group2 = asterisk_groups[j]
            group2_start = group2[0]
            group2_count = len(group2)
            
            # Check if same count
            if group2_count != group1_count:
                continue
            
            # Check if preceded by non-space
            if group2_start > 0 and line[group2_start - 1] != ' ':
                # Check there's content between them
                between = line[group1_end:group2_start]
                if between and not between.isspace():
                    # Found a matching pair!
                    paired_asterisk_positions.update(group1)
                    paired_asterisk_positions.update(group2)
                    used_asterisk_groups.add(i)
                    used_asterisk_groups.add(j)
                    break
    
    # Process underscores similarly
    underscore_groups = []
    processed_underscores = set()
    
    for pos in sorted(escape_map.keys()):
        char, is_backslash = escape_map[pos]
        if char == '_' and not is_backslash and pos not in processed_underscores:
            group = [pos]
            processed_underscores.add(pos)
            next_pos = pos + 2
            
            while next_pos in escape_map:
                next_char, next_is_backslash = escape_map[next_pos]
                if next_char == '_' and not next_is_backslash:
                    group.append(next_pos)
                    processed_underscores.add(next_pos)
                    next_pos += 2
                else:
                    break
            
            underscore_groups.append(group)
    
    # Find matching underscore emphasis pairs
    paired_underscore_positions = set()
    used_underscore_groups = set()
    
    for i, group1 in enumerate(underscore_groups):
        if i in used_underscore_groups:
            continue
            
        group1_start = group1[0]
        group1_count = len(group1)
        group1_end = group1_start + group1_count * 2
        
        # For underscores, check word boundaries
        # Opening emphasis: not preceded by word char, followed by non-space
        if group1_start > 0 and line[group1_start - 1].isalnum():
            continue  # Can't start emphasis mid-word
        if group1_end >= len(line) or line[group1_end] == ' ':
            continue  # Must be followed by non-space
        
        # Look for matching group
        for j in range(i + 1, len(underscore_groups)):
            if j in used_underscore_groups:
                continue
                
            group2 = underscore_groups[j]
            group2_start = group2[0]
            group2_count = len(group2)
            group2_end = group2_start + group2_count * 2
            
            # Check if same count (1 or 2 for emphasis)
            if group2_count != group1_count or group2_count > 2:
                continue
            
            # Closing emphasis: preceded by non-space, not followed by word char
            if group2_start > 0 and line[group2_start - 1] == ' ':
                continue  # Must be preceded by non-space
            if group2_end < len(line) and line[group2_end].isalnum():
                continue  # Can't end emphasis mid-word
            
            # Check there's content between them
            between = line[group1_end:group2_start]
            if between and not between.isspace():
                # Found a matching pair!
                paired_underscore_positions.update(group1)
                paired_underscore_positions.update(group2)
                used_underscore_groups.add(i)
                used_underscore_groups.add(j)
                break
    
    # Process backticks - simple rule: if only one sequence in line, unescape
    backtick_groups = []
    processed_backticks = set()
    
    for pos in sorted(escape_map.keys()):
        char, is_backslash = escape_map[pos]
        if char == '`' and not is_backslash and pos not in processed_backticks:
            group = [pos]
            processed_backticks.add(pos)
            next_pos = pos + 2
            
            while next_pos in escape_map:
                next_char, next_is_backslash = escape_map[next_pos]
                if next_char == '`' and not next_is_backslash:
                    group.append(next_pos)
                    processed_backticks.add(next_pos)
                    next_pos += 2
                else:
                    break
            
            backtick_groups.append(group)
    
    # Decide which positions to unescape
    positions_to_unescape = set()
    
    # Process asterisk groups
    for group in asterisk_groups:
        if group[0] in paired_asterisk_positions:
            continue  # Keep escaped - part of emphasis
        
        if should_unescape_asterisk_group(line, group):
            positions_to_unescape.update(group)
    
    # Process underscore groups
    for group in underscore_groups:
        if group[0] in paired_underscore_positions:
            continue  # Keep escaped - part of emphasis
        
        group_start = group[0]
        group_end = group_start + len(group) * 2
        
        # Check for horizontal rule (3+ underscores on a line by themselves)
        if len(group) >= 3:
            # Check if line contains only underscores and whitespace
            test_line = line.replace('\\_', '').replace('_', '').strip()
            if not test_line:
                continue  # Keep escaped - would form horizontal rule
        
        # Determine what's before and after
        before_char = line[group_start - 1] if group_start > 0 else ''
        after_char = line[group_end] if group_end < len(line) else ''
        
        # Safe to unescape if:
        
        # 1. Intraword underscore (surrounded by alphanumeric)
        if before_char.isalnum() and after_char.isalnum():
            positions_to_unescape.update(group)
            continue
        
        # 2. Has spaces on both sides (can't form emphasis)
        if (not before_char or before_char == ' ') and (not after_char or after_char == ' '):
            positions_to_unescape.update(group)
            continue
        
        # 3. Single underscore that can't form valid emphasis
        if len(group) == 1:
            # Check if this could form valid emphasis
            can_open = (not before_char.isalnum() if before_char else True) and after_char and after_char != ' '
            can_close = before_char and before_char != ' ' and (not after_char.isalnum() if after_char else True)
            
            if not can_open and not can_close:
                # Can't be part of emphasis
                positions_to_unescape.update(group)
                continue
            
            # Check if there's a potential matching underscore
            has_match = False
            for other_group in underscore_groups:
                if other_group == group or len(other_group) != 1:
                    continue
                
                other_start = other_group[0]
                other_end = other_start + 2
                other_before = line[other_start - 1] if other_start > 0 else ''
                other_after = line[other_end] if other_end < len(line) else ''
                
                if can_open and group_start < other_start:
                    # This could be opening, check if other can close
                    other_can_close = other_before and other_before != ' ' and (not other_after.isalnum() if other_after else True)
                    if other_can_close:
                        between = line[group_end:other_start]
                        if between and not between.isspace():
                            has_match = True
                            break
                
                elif can_close and other_start < group_start:
                    # This could be closing, check if other can open
                    other_can_open = (not other_before.isalnum() if other_before else True) and other_after and other_after != ' '
                    if other_can_open:
                        between = line[other_end:group_start]
                        if between and not between.isspace():
                            has_match = True
                            break
            
            if not has_match:
                positions_to_unescape.update(group)
    
    # Process backticks
    # If only one backtick sequence in line, it's safe to unescape
    # Exception: ``` at line start (code block fence)
    if len(backtick_groups) == 1:
        group = backtick_groups[0]
        group_start = group[0]
        group_count = len(group)
        
        # Check for code block fence: ``` at line start
        if group_count == 3:
            before = line[:group_start]
            if not re.match(r'^\s*$', before):
                # Not at line start, safe to unescape
                positions_to_unescape.update(group)
        else:
            # Not triple backticks, safe to unescape
            positions_to_unescape.update(group)
    
    # Process angle brackets as pairs
    # First, find all valid \<...\> pairs that should stay escaped
    valid_angle_pairs = set()
    
    # Find all < and > positions in escape_map
    lt_positions = []
    gt_positions = []
    for pos, (char, is_backslash) in escape_map.items():
        if not is_backslash:
            if char == '<':
                lt_positions.append(pos)
            elif char == '>':
                gt_positions.append(pos)
    
    # Check each < to see if it forms a valid pair with a >
    for lt_pos in lt_positions:
        # Find the nearest > after this <
        for gt_pos in gt_positions:
            if gt_pos > lt_pos:
                # Check content between \< and \>
                content = line[lt_pos+2:gt_pos]
                
                is_valid = False
                
                # Check if content forms valid patterns
                if content:
                    # Check for URL autolink
                    if re.match(r'^https?://[^\s>]+$', content) or re.match(r'^[a-z][a-z0-9+.-]*:[^\s>]+$', content):
                        is_valid = True
                    # Check for email autolink
                    elif re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', content):
                        is_valid = True
                    # Check for HTML tag - be strict about what's valid
                    elif not ' ' in content:
                        # No spaces - simple tag like div, /div, br/
                        if re.match(r'^/?[a-zA-Z][a-zA-Z0-9-]*/?$', content):
                            is_valid = True
                    else:
                        # Has spaces - check if it's a tag with attributes
                        # Split on first space
                        parts = content.split(' ', 1)
                        if len(parts) == 2:
                            tagname, attrs = parts
                            # Tag name must be valid
                            if re.match(r'^/?[a-zA-Z][a-zA-Z0-9-]*$', tagname):
                                # Attributes must contain = (key=value) to be valid
                                if '=' in attrs:
                                    is_valid = True
                
                if is_valid:
                    # Mark both positions as part of valid pair
                    valid_angle_pairs.add(lt_pos)
                    valid_angle_pairs.add(gt_pos)
                
                # Only check the first > after each <
                break
    
    # Process other characters
    for pos, (char, is_backslash) in escape_map.items():
        if is_backslash:
            continue  # Keep escaped backslashes
        if char in ['*', '_', '`']:
            continue  # Already processed
        
        if char == '#':
            # Keep escaped if at line start (would form header)
            if not re.match(r'^\s*\\#', line[:pos+2]):
                positions_to_unescape.add(pos)
        elif char == '+':
            # Keep escaped if forms list marker
            before = line[:pos]
            after = line[pos+2:] if pos+2 < len(line) else ''
            if not (re.match(r'^\s*$', before) and after.startswith(' ')):
                positions_to_unescape.add(pos)
        elif char == '-':
            # Keep escaped if forms list marker or horizontal rule
            before = line[:pos]
            after = line[pos+2:] if pos+2 < len(line) else ''
            if re.match(r'^\s*$', before) and after.startswith(' '):
                continue  # List marker
            
            # Check for horizontal rule
            dash_count = line.count('\\-') + line.count('-')
            if dash_count >= 3:
                clean = line.replace('\\-', '').replace('-', '').strip()
                if not clean:
                    continue  # Horizontal rule
            
            positions_to_unescape.add(pos)
        elif char == '.':
            # Keep escaped if forms ordered list marker
            before = line[:pos]
            after = line[pos+2:] if pos+2 < len(line) else ''
            if not (re.match(r'^\s*\d+$', before) and (after.startswith(' ') or not after)):
                positions_to_unescape.add(pos)
        elif char == ')':
            # Keep escaped if forms ordered list marker
            before = line[:pos]
            after = line[pos+2:] if pos+2 < len(line) else ''
            if re.match(r'^\s*\d+$', before) and (after.startswith(' ') or not after):
                continue  # Keep escaped - would form list marker
            
            # Check if part of \[...\]\(...\) pattern with no spaces
            paren_start = before.rfind('\\(')
            if paren_start != -1:
                paren_content = before[paren_start+2:]
                if ' ' not in paren_content:
                    # Check if \( is preceded by \]
                    pre_paren = before[:paren_start]
                    if pre_paren.endswith('\\]'):
                        # Look for \[
                        bracket_start = pre_paren[:-2].rfind('\\[')
                        if bracket_start != -1:
                            bracket_content = pre_paren[bracket_start+2:-2]
                            if ' ' not in bracket_content:
                                # Valid link pattern - keep escaped
                                continue
            
            # All other cases - unescape
            positions_to_unescape.add(pos)
        elif char == '[':
            # Check if part of \[...\]\(...\) pattern with no spaces
            after = line[pos+2:]
            
            # Look for closing \]
            bracket_end = after.find('\\]')
            if bracket_end != -1:
                bracket_content = after[:bracket_end]
                if ' ' not in bracket_content:
                    # No spaces in bracket, check if \( follows
                    after_bracket = after[bracket_end+2:]
                    if after_bracket.startswith('\\('):
                        # Found \]\( pattern, check paren content
                        paren_start = bracket_end + 4
                        remaining = after[paren_start:]
                        paren_end = remaining.find('\\)')
                        if paren_end != -1:
                            paren_content = remaining[:paren_end]
                            if ' ' not in paren_content:
                                # Valid link pattern - keep escaped
                                continue
            
            # All other cases - unescape
            positions_to_unescape.add(pos)
        elif char == ']':
            # Check if part of \[...\]\(...\) pattern with no spaces
            before = line[:pos]
            after = line[pos+2:] if pos+2 < len(line) else ''
            
            # Look back for \[
            bracket_start = before.rfind('\\[')
            if bracket_start != -1:
                bracket_content = before[bracket_start+2:]
                if ' ' not in bracket_content:
                    # No spaces in bracket, check if \( follows
                    if after.startswith('\\('):
                        # Found \]\( pattern, check paren content
                        remaining = after[2:]
                        paren_end = remaining.find('\\)')
                        if paren_end != -1:
                            paren_content = remaining[:paren_end]
                            if ' ' not in paren_content:
                                # Valid link pattern - keep escaped
                                continue
            
            # All other cases - unescape
            positions_to_unescape.add(pos)
        elif char == '(':
            # Check if part of \[...\]\(...\) pattern with no spaces
            before = line[:pos]
            
            # Check if preceded by \]
            if before.endswith('\\]'):
                # Look back for \[
                bracket_start = before[:-2].rfind('\\[')
                if bracket_start != -1:
                    bracket_content = before[bracket_start+2:-2]
                    if ' ' not in bracket_content:
                        # No spaces in bracket, check paren content
                        after = line[pos+2:] if pos+2 < len(line) else ''
                        paren_end = after.find('\\)')
                        if paren_end != -1:
                            paren_content = after[:paren_end]
                            if ' ' not in paren_content:
                                # Valid link pattern - keep escaped
                                continue
            
            # All other cases - unescape
            positions_to_unescape.add(pos)
        elif char == '<':
            # Check if this is part of a valid pair
            if pos not in valid_angle_pairs:
                # Not part of a valid tag/autolink pair - safe to unescape
                positions_to_unescape.add(pos)
            
        elif char == '>':
            # Check if at line start (would form blockquote)
            before = line[:pos]
            if re.match(r'^\s*$', before):
                # At line start - would form blockquote, keep escaped
                continue
            
            # Check if this is part of a valid pair
            if pos not in valid_angle_pairs:
                # Not part of a valid tag/autolink pair - safe to unescape
                positions_to_unescape.add(pos)
        elif char == '|':
            # Pipe handling based on table context from unescape_markdown
            if keep_pipes_escaped:
                continue  # Keep escaped - would form/break table
            else:
                positions_to_unescape.add(pos)  # Safe to unescape
        elif char == '~':
            # Check for strikethrough (~~text~~)
            tilde_groups = []
            for p in sorted(escape_map.keys()):
                c, is_bs = escape_map[p]
                if c == '~' and not is_bs:
                    if not tilde_groups or p != tilde_groups[-1][-1] + 2:
                        tilde_groups.append([p])
                    else:
                        tilde_groups[-1].append(p)
            
            # Check if this tilde is part of a potential strikethrough pair
            in_pair = False
            for group in tilde_groups:
                if pos in group and len(group) == 2:
                    # Look for matching pair
                    for other_group in tilde_groups:
                        if other_group != group and len(other_group) == 2:
                            in_pair = True
                            break
            
            if not in_pair:
                positions_to_unescape.add(pos)
        elif char == '=':
            # Keep escaped if line would be only ='s and whitespace (Setext heading)
            test_line = line.replace('\\=', '=')
            if re.match(r'^\s*=+\s*$', test_line):
                continue  # Keep escaped - would form Setext heading
            positions_to_unescape.add(pos)
        else:
            # Other characters are generally safe
            positions_to_unescape.add(pos)
    
    # Build result
    result = []
    i = 0
    
    while i < len(line):
        if i in escape_map:
            char, is_backslash = escape_map[i]
            
            if is_backslash:
                result.append('\\\\')
                i += 2
            elif i in positions_to_unescape:
                result.append(char)
                i += 2
            else:
                result.append('\\')
                result.append(char)
                i += 2
        else:
            result.append(line[i])
            i += 1
    
    return ''.join(result)


def should_unescape_asterisk_group(line: str, group: list) -> bool:
    """Check if a group of consecutive escaped asterisks should be unescaped."""
    
    group_start = group[0]
    group_count = len(group)
    group_end = group_start + group_count * 2
    
    # Count total asterisks
    total_asterisks = 0
    i = 0
    while i < len(line):
        if i < len(line) - 1 and line[i:i+2] == '\\*':
            i += 2
            total_asterisks += 1
        elif line[i] == '*':
            i += 1
            total_asterisks += 1
        else:
            i += 1
    
    # Check if it's a list marker
    if group_count == 1:
        before = line[:group_start]
        after = line[group_end:] if group_end < len(line) else ''
        if re.match(r'^\s*$', before) and after.startswith(' '):
            return False
    
    # Rule 1: Only one asterisk in the line
    if total_asterisks == 1:
        return True
    
    # Rule 2: Only one sequence of asterisks
    sequences = 0
    i = 0
    while i < len(line):
        if i < len(line) - 1 and line[i:i+2] == '\\*':
            sequences += 1
            i += 2
            while i < len(line) - 1 and line[i:i+2] == '\\*':
                i += 2
        elif line[i] == '*':
            sequences += 1
            i += 1
            while i < len(line) and line[i] == '*':
                i += 1
        else:
            i += 1
    
    if sequences == 1:
        # Check for horizontal rule
        if group_count >= 3:
            clean = line.replace('\\*', '').replace('*', '').strip()
            if not clean:
                return False
        return True
    
    # Rule 3 & 4: Spaces on both sides
    has_space_before = group_start == 0 or line[group_start - 1] == ' '
    has_space_after = group_end >= len(line) or line[group_end] == ' '
    
    if has_space_before and has_space_after:
        return True
    
    # Rule 5: Unmatched asterisk
    return is_unmatched_asterisk(line, group_start, group_count, group_end)


def is_unmatched_asterisk(line: str, group_start: int, group_count: int, group_end: int) -> bool:
    """Check if asterisk group is unmatched on both sides."""
    
    # Check LEFT side
    if group_start > 0 and line[group_start - 1] == ' ':
        unmatched_left = True
    else:
        # Look for asterisk on the left that's not followed by space
        left_part = line[:group_start]
        found_match = False
        
        i = 0
        while i < len(left_part):
            if i < len(left_part) - 1 and left_part[i:i+2] == '\\*':
                # Count backslashes before the \ of \*
                backslash_count = 0
                j = i - 1
                while j >= 0 and left_part[j] == '\\':
                    backslash_count += 1
                    j -= 1
                
                # If even backslashes, it's a real asterisk
                if backslash_count % 2 == 0:
                    # Find end of asterisk group
                    k = i + 2
                    while k < len(left_part) - 1 and left_part[k:k+2] == '\\*':
                        k += 2
                    
                    # Check what follows
                    if k >= len(left_part) or left_part[k] != ' ':
                        found_match = True
                        break
                
                i += 2
            else:
                i += 1
        
        if found_match:
            return False
        else:
            unmatched_left = True
    
    # Check RIGHT side
    if group_end < len(line) and line[group_end] == ' ':
        unmatched_right = True
    else:
        # Look for \* on the right that's not preceded by space
        right_part = line[group_end:]
        found_match = False
        
        i = 0
        while i < len(right_part):
            if i < len(right_part) - 1 and right_part[i:i+2] == '\\*':
                # Check if not preceded by space
                if i == 0 or right_part[i - 1] != ' ':
                    found_match = True
                    break
                i += 2
            else:
                i += 1
        
        if found_match:
            return False
        else:
            unmatched_right = True
    
    return unmatched_left and unmatched_right