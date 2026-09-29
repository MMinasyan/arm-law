# to_soup(), has_text(), is_empty_element(), has_direct_nonempty_text()
# clean_control_characters(), remove_nbsp(), remove_word_comments()
# apply_text_transform(), merge_same_tags(), remove_unnecessary_br()
# remove_empty_tags(), remove_unsafe_urls(), fix_relative_links()
# add_style_tag()
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
from bs4.element import ResultSet
import unicodedata
import re
from urllib.parse import urljoin, urlparse


ALLOWED_TAGS = {
    'p', 'br', 'a', 'hr',
    'ul', 'ol', 'li',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
    'b', 'strong', 'i', 'em', 'u', 'sup', 'sub',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img',
    'math', 'mi', 'mo', 'mn', 'mtext', 'mrow', 'mfrac', 'msqrt', 'mroot', 'mstyle',
    'msub', 'msup', 'msubsup', 'semantics', 'annotation',
    'munder', 'mover', 'munderover', 'mmultiscripts',
    'mtable', 'mtr', 'mtd', 'maction',
    'figure', 'figcaption'
}

REMOVE_COMPLETELY = {'script', 'style', 'iframe', 'object', 'noscript'}

ALLOWED_ATTRIBUTES = {
    'td': {'colspan', 'rowspan'},
    'th': {'colspan', 'rowspan', 'scope'},
    'table': {'border'},
    'img': {'width', 'height', 'src'},
    'a': {'href'},
    'ol': {'start'}
}

CAN_BE_EMPTY = {'br', 'td', 'th', 'img', 'hr'}


def to_soup(soup=None, html=None):
    """Convert input to BeautifulSoup object."""
    if soup is None and html is None:
        raise ValueError("Either soup or html must be provided")
    
    if soup is None:
        return BeautifulSoup(html, 'html.parser')
    elif isinstance(soup, BeautifulSoup):
        return soup
    elif isinstance(soup, Tag):
        return BeautifulSoup(str(soup), 'html.parser')
    elif isinstance(soup, ResultSet):
        # This shouldn't happen
        raise TypeError(f"Expected Tag or BeautifulSoup, got ResultSet")
    else:
        # Try to convert whatever it is to BeautifulSoup
        return BeautifulSoup(str(soup), 'html.parser')

def has_text(input_str):
    """Check if string has meaningful text content."""
    stripped = input_str.strip()
    return stripped and any(c.isprintable() for c in stripped)

def is_empty_element(element):
    """Check if element is empty (except img tags)."""
    if element.name in ['img']:
        return False
    if element.find('img'):
        return False
    return not element.get_text(strip=True)

def has_direct_nonempty_text(element):
    """Check if element has direct text children."""
    for child in element.children:
        if isinstance(child, str) and child.strip():
            return True
    return False

def clean_control_characters(text_node):
    """Remove control characters except common whitespace."""
    if isinstance(text_node, NavigableString) and not isinstance(text_node, Comment):
        cleaned = ''.join(
            c for c in text_node 
            if unicodedata.category(c)[0] != 'C' or c in '\t\n\r '
        )
        return cleaned
    return text_node

def remove_nbsp(soup):
    """Remove nbsp correctly - if neighboring whitespace exists, delete; otherwise replace with space. Keep unchanged when uppercase spaced letters."""
    # Armenian 2-character letters (add all that exist)
    TWO_CHAR_LETTERS = {'ՈՒ', 'Ու'}  # Both Unicode representations, add more if needed
    
    for text_node in soup.find_all(string=True):
        if isinstance(text_node, NavigableString) and not isinstance(text_node, Comment):
            text = str(text_node)
            
            # Replace uppercase 2-character letters with placeholder 
            temp_text = text
            two_char_count = 0
            for letter in TWO_CHAR_LETTERS:
                two_char_count += temp_text.count(letter)
                temp_text = temp_text.replace(letter, '##')
            
            # 1. Count uppercase letters (2-char letters already counted, count rest)
            single_uppercase_count = sum(1 for c in temp_text if c.isupper())
            uppercase_count = two_char_count + single_uppercase_count
            
            # 2. Has NO lowercase letters (check modified text)
            only_letters = ''.join(c for c in temp_text if c.isalpha())
            has_lowercase = any(c.islower() for c in only_letters)
            
            # 3. All groups are single chars or known 2-char letters
            groups = text.replace('\xa0', ' ').split()
            all_spaced = all(
                len(g) == 1 or g in TWO_CHAR_LETTERS
                for g in groups
            )
            
            if uppercase_count >= 5 and not has_lowercase and all_spaced:
                # All conditions met - preserve nbsp
                continue
            
            # Original logic for all other cases
            text = re.sub(r'(?<=\s)\xa0+|\xa0+(?=\s)', '', text)
            text = re.sub(r'\xa0+', ' ', text)
            
            if text != str(text_node):
                text_node.replace_with(text)


def apply_text_transform(soup):
    """
    Apply text-transform CSS property to text content before removing styles.
    Should be called BEFORE stripping style attributes.
    """
    import re
    
    for tag in soup.find_all(True):
        if not tag.get('style'):
            continue
            
        style = tag.get('style', '').lower()
        
        # Extract text-transform value
        transform_match = re.search(r'text-transform\s*:\s*([^;]+)', style)
        if not transform_match:
            continue
            
        transform_value = transform_match.group(1).strip()
        
        # Apply transformation to all text nodes within this tag
        for text_node in tag.find_all(string=True):
            if isinstance(text_node, NavigableString) and not isinstance(text_node, Comment):
                original = str(text_node)
                
                if transform_value == 'uppercase':
                    transformed = original.upper()
                elif transform_value == 'lowercase':
                    transformed = original.lower()
                elif transform_value == 'capitalize':
                    # Capitalize first letter of each word
                    transformed = ' '.join(word.capitalize() for word in original.split())
                else:
                    continue  # 'none' or unknown value
                    
                if transformed != original:
                    text_node.replace_with(transformed)
    
    return soup

def merge_same_tags(soup):
    """Merge adjacent tags of the same type."""
    tags_to_merge = ['b', 'strong', 'i', 'em', 'u', 'sup', 'sub', 'br']
    for tag_name in tags_to_merge:
        for tag in soup.find_all(tag_name):
            while True:
                next_sib = tag.next_sibling
                intermediate = []
                # Skip whitespace and <br/> tags (br only when not merging br tags)
                while next_sib and (
                    (isinstance(next_sib, NavigableString) and next_sib.strip() == '') or
                    (tag_name != 'br' and isinstance(next_sib, Tag) and next_sib.name == 'br')
                ):
                    intermediate.append(next_sib)
                    next_sib = next_sib.next_sibling
                if next_sib and isinstance(next_sib, Tag) and next_sib.name == tag.name:
                    if tag_name == 'br':
                        # br is a void element - don't append content inside it
                        # Just remove intermediate whitespace and the duplicate br
                        for item in intermediate:
                            item.extract()
                    else:
                        for item in intermediate:
                            tag.append(item)
                        for child in list(next_sib.contents):
                            tag.append(child)
                    next_sib.extract()
                else:
                    break

def remove_unnecessary_br(soup):
    """Remove br tags that are adjacent to block elements."""
    tags_to_check = ['p', 'ul', 'ol', 'th', 'td', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    inline_tags = {'strong', 'b', 'em', 'i', 'u', 'a', 'sup', 'sub'}

    def find_leading_br(element):
        """Find leading br, looking inside inline tags."""
        first = next((c for c in element.children
                      if not (isinstance(c, NavigableString) and not c.strip())), None)
        if first and isinstance(first, Tag) and first.name == 'br':
            return first
        if first and isinstance(first, Tag) and first.name in inline_tags:
            return find_leading_br(first)
        return None

    def find_trailing_br(element):
        """Find trailing br, looking inside inline tags."""
        last = next((c for c in reversed(list(element.children))
                     if not (isinstance(c, NavigableString) and not c.strip())), None)
        if last and isinstance(last, Tag) and last.name == 'br':
            return last
        if last and isinstance(last, Tag) and last.name in inline_tags:
            return find_trailing_br(last)
        return None

    for tag in soup.find_all(tags_to_check):
        # Remove leading <br/> tags inside (including inside inline tags)
        while True:
            leading_br = find_leading_br(tag)
            if leading_br:
                leading_br.decompose()
            else:
                break

        # Remove trailing <br/> tags inside (including inside inline tags)
        while True:
            trailing_br = find_trailing_br(tag)
            if trailing_br:
                trailing_br.decompose()
            else:
                break
        
        # Remove preceding <br/> tags outside
        while True:
            prev_non_ws = next((sib for sib in tag.previous_siblings 
                              if not (isinstance(sib, NavigableString) and not sib.strip())), None)
            if prev_non_ws and prev_non_ws.name == 'br':
                prev_non_ws.decompose()
            else:
                break
        
        # Remove following <br/> tags outside
        while True:
            next_non_ws = next((sib for sib in tag.next_siblings 
                              if not (isinstance(sib, NavigableString) and not sib.strip())), None)
            if next_non_ws and next_non_ws.name == 'br':
                next_non_ws.decompose()
            else:
                break

def remove_empty_tags(soup):
    """Remove tags with no content (except those allowed to be empty)."""
    for tag in soup.find_all(list(ALLOWED_TAGS)):
        if tag.name == 'img' or tag.name in CAN_BE_EMPTY:
            continue
        if not has_text(tag.get_text(strip=True)):
            if len(tag.contents) == 0:
                tag.decompose()
            else:
                tag.unwrap()
    
def remove_unsafe_urls(soup):
    """Remove potentially dangerous URLs from preserved attributes."""
    for a in soup.find_all('a', href=True):
        href = a['href'].strip().lower()
        if href.startswith(('javascript:', 'vbscript:', 'data:text/html')):
            del a['href']
    return soup

def fix_relative_links(soup, base_url):
    """Convert relative URLs to absolute using proper URL parsing."""
    if not base_url:
        return soup
        
    # Handle href attributes (links)
    for tag in soup.find_all('a', href=True):
        href = tag['href'].strip()
        # Skip special schemes and fragments
        if not href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
            parsed = urlparse(href)
            if not parsed.scheme:  # Relative URL
                if href.startswith('//'):
                    tag['href'] = 'https:' + href
                else:
                    tag['href'] = urljoin(base_url, href)
    
    # Handle src attributes (images)
    for tag in soup.find_all('img', src=True):
        src = tag['src'].strip()
        if not src.startswith('data:'):  # Skip data URIs
            parsed = urlparse(src)
            if not parsed.scheme:  # Relative URL
                if src.startswith('//'):
                    tag['src'] = 'https:' + src
                else:
                    tag['src'] = urljoin(base_url, src)
    
    return soup

def add_style_tag(soup):
    """Add CSS styling for lists and tables."""
    style_tag = soup.new_tag('style')
    style_tag.string = """
    ol {
        list-style: none;
    }
    li {
        margin-top: 1em;
    }
    table {
        border-collapse: collapse;
        margin: 1em;
    }
    table:not([border]) {
        border: 1px solid black;
    }
    td, th { padding: 10px; }
"""
    if soup.html is None:
        html = soup.new_tag('html')
        for content in soup.contents[:]:
            html.append(content.extract())
        soup.append(html)
    else:
        html = soup.html
        
    head = html.head
    if head is None:
        head = soup.new_tag('head')
        html.insert(0, head)
    head.append(style_tag)

    if html.body is None:
        body = soup.new_tag('body')
        head.insert_after(body)
        for c in list(html.contents):
            if c.name and c not in (head, body):
                body.append(c.extract())

def remove_visual_redundancy(soup):
    """Remove redundant nested tags from the same visual group and unnecessary tags in headers."""
    visual_groups = [
        ('strong', 'b'),  # semantic, non-semantic
        ('em', 'i')
    ]
    
    changed = True
    while changed:
        changed = False
        
        for semantic, non_semantic in visual_groups:
            all_tags = soup.find_all([semantic, non_semantic])
            
            for outer in all_tags:
                if outer.parent is None:
                    continue
                
                # Find first nested tag from same group
                inner = outer.find([semantic, non_semantic])
                if not inner:
                    continue
                
                # Rule 1: Same type nested - unwrap inner
                if outer.name == inner.name:
                    inner.unwrap()
                    changed = True
                    break
                
                # Rule 2: Semantic inside non-semantic, all text covered
                if outer.name == non_semantic and inner.name == semantic:
                    all_inside = True
                    for child in outer.children:
                        if isinstance(child, NavigableString) and child.strip():
                            all_inside = False
                            break
                        if isinstance(child, Tag) and child != inner and child.get_text(strip=True):
                            all_inside = False
                            break
                    
                    if all_inside:
                        outer.unwrap()
                        changed = True
                        break
                
                # Rule 3: All other cases - unwrap inner
                inner.unwrap()
                changed = True
                break
            
            if changed:
                break
    
    # Remove bold tags inside headers (headers are already bold)
    for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        for bold_tag in header.find_all(['strong', 'b']):
            bold_tag.unwrap()

    return soup

def merge_same_url_links(soup):
    """Merge adjacent <a> tags with the same URL."""
    inline_tags = ['strong', 'b', 'em', 'i', 'u', 'sup', 'sub']

    for a_tag in soup.find_all('a', href=True):
        while True:
            # Collect whitespace and <br> between current and next potential match
            intervening = []
            sibling = a_tag.next_sibling

            while sibling:
                if isinstance(sibling, NavigableString):
                    if not sibling.strip():  # whitespace only
                        intervening.append(sibling)
                        sibling = sibling.next_sibling
                        continue
                    break
                if isinstance(sibling, Tag) and sibling.name == 'br':
                    intervening.append(sibling)
                    sibling = sibling.next_sibling
                    continue
                break

            if not sibling or not isinstance(sibling, Tag):
                break

            # Check for direct <a> sibling or wrapped <a>
            if sibling.name == 'a' and sibling.get('href') == a_tag.get('href'):
                # Direct sibling - move intervening and content
                for elem in intervening:
                    a_tag.append(elem.extract())
                for child in list(sibling.children):
                    a_tag.append(child.extract())
                sibling.extract()
                continue
            elif sibling.name in inline_tags:
                # Check if inline tag wraps only an <a> with same href
                inner_a = sibling.find('a', href=True, recursive=False)
                if inner_a and inner_a.get('href') == a_tag.get('href'):
                    # Verify no other content in wrapper
                    has_other = any(
                        child != inner_a and not (isinstance(child, NavigableString) and not child.strip())
                        for child in sibling.children
                    )
                    if not has_other:
                        # Find if a_tag has a matching wrapper as last non-br tag
                        existing_wrapper = None
                        for child in reversed(list(a_tag.children)):
                            if isinstance(child, Tag):
                                if child.name == 'br':
                                    continue
                                if child.name == sibling.name:
                                    existing_wrapper = child
                                break

                        if existing_wrapper:
                            # Consolidate: add intervening and content to existing wrapper
                            for elem in intervening:
                                existing_wrapper.append(elem.extract())
                            for child in list(inner_a.children):
                                existing_wrapper.append(child.extract())
                            sibling.extract()
                        else:
                            # No matching wrapper: add intervening and new wrapper
                            for elem in intervening:
                                a_tag.append(elem.extract())
                            for child in list(inner_a.children):
                                sibling.append(child.extract())
                            inner_a.unwrap()
                            a_tag.append(sibling.extract())
                        continue
            break

    return soup