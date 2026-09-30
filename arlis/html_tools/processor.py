# simple_process() - lightweight processing
# clean_html() - main processing pipeline

import re
from bs4 import NavigableString, Tag, Comment
from .utilities import (
    has_text, apply_text_transform, merge_same_tags,
    remove_unnecessary_br, remove_nbsp, remove_empty_tags,
    fix_relative_links, remove_unsafe_urls, clean_control_characters,
    remove_visual_redundancy,
    ALLOWED_TAGS, ALLOWED_ATTRIBUTES, REMOVE_COMPLETELY
)
from .structures import (
    fix_incorrect_structures, propagate_inline_to_leaves, convert_pseudo_headers
)



def simple_process(soup):
    """
    Lightweight HTML cleaning that focuses on removing unnecessary elements and attributes.
    This is designed to be idempotent with the full clean_html processing.
    """
    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    # Remove math fallback images
    for wrapper in soup.find_all(lambda tag: tag.name and tag.find('math') and tag.find('img')):
        for img in wrapper.find_all('img'):
            img.decompose()
    
    soup = apply_text_transform(soup)
    
    # Process all tags
    for tag in soup.find_all(True):
        if tag.parent is None:
            continue
        if tag.name in REMOVE_COMPLETELY:
            tag.decompose()
        elif tag.name in ALLOWED_TAGS:
            allowed = ALLOWED_ATTRIBUTES.get(tag.name, set())
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in allowed}
        else:
            tag.unwrap()
    
    soup = fix_incorrect_structures(soup)
    
    soup = fix_relative_links(soup)
    
    # Remove potentially dangerous URLs
    soup = remove_unsafe_urls(soup)
    
    # Remove empty tags
    remove_empty_tags(soup)

    # Fix any orphaned elements created by empty tag removal
    soup = fix_incorrect_structures(soup)

    # Clean control characters
    for text_node in soup.find_all(string=True):
        cleaned = clean_control_characters(text_node)
        if cleaned != text_node:
            text_node.replace_with(cleaned)
    
    return soup

def clean_html(soup):
    # Apply simple processing first
    soup = simple_process(soup)
    
    # Define additional tags for complex processing
    structural_tags = {'p', 'ul', 'ol', 'table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img'}
    inline_tags = {'a', 'b', 'strong', 'i', 'em', 'u', 'sup', 'sub'}
    
    # Handle inline tags containing structural tags
    # Sort by depth (deepest first) to process inner tags before outer
    inline_tags_list = list(soup.find_all(inline_tags))
    inline_tags_list.sort(key=lambda tag: len(list(tag.parents)), reverse=True)

    for tag in inline_tags_list:
        # Skip if already processed and unwrapped
        if tag.parent is None:
            continue
        
        # Check if contains structural tags at any depth
        if any(tag.find_all(structural_tags, recursive=True)):
            children = [child for child in tag.children if isinstance(child, Tag)]
            new_contents = []
            non_structurals = []
            
            for child in list(tag.contents):
                if isinstance(child, Tag) and child.name in structural_tags:
                    if non_structurals:
                        inline_copy = soup.new_tag(tag.name, attrs=tag.attrs)
                        for item in non_structurals:
                            inline_copy.append(item)
                        if has_text(inline_copy.get_text(strip=True)):
                            new_contents.append(inline_copy)
                        else:
                            for item in list(inline_copy.contents):
                                new_contents.append(item)
                    non_structurals = []
                    
                    # Just propagate the current tag, not ancestors
                    propagate_inline_to_leaves(child, tag.name, tag.attrs, soup, structural_tags)
                    new_contents.append(child)
                else:
                    if isinstance(child, NavigableString) and not child.strip():
                        continue
                    non_structurals.append(child)
                    
            if non_structurals:
                inline_copy = soup.new_tag(tag.name, attrs=tag.attrs)
                for item in non_structurals:
                    inline_copy.append(item)
                if has_text(inline_copy.get_text(strip=True)):
                    new_contents.append(inline_copy)
                else:
                    for item in list(inline_copy.contents):
                        new_contents.append(item)
                        
            tag.clear()
            for item in new_contents:
                tag.append(item)
            tag.unwrap()
    
    # Remove visual redundancy in same-group nested tags
    soup = remove_visual_redundancy(soup)

    # Unwrap tags inside structural_tags
    tags = list(soup.find_all(list(ALLOWED_TAGS)))
    for tag in tags:
        children = [child for child in tag.children if isinstance(child, Tag)]
        has_direct_text = any(isinstance(child, NavigableString) and child.strip() for child in tag.contents)
        
        if not children:
            continue

        if all(child.name == tag.name for child in children) and not has_direct_text:
            tag.unwrap()
            continue

        if tag.name == 'table' and not has_direct_text:
            cells = tag.find_all(['td', 'th'], recursive=True)
            if cells and all(
                len([c for c in cell.children if isinstance(c, Tag)]) == 1 and
                next((c for c in cell.children if isinstance(c, Tag)), None).name == 'table'
                for cell in cells
            ):
                tag.unwrap()
                continue

        if tag.name == 'p':
            if not has_direct_text and all(child.name in structural_tags or child.name == 'br' for child in children):
                tag.unwrap()
                continue
            elif any(child.name in structural_tags for child in children):
                new_contents = []
                non_structurals = []
                for child in list(tag.contents):
                    if isinstance(child, Tag) and child.name in structural_tags:
                        if non_structurals:
                            p_tag = soup.new_tag('p')
                            for item in non_structurals:
                                p_tag.append(item)
                            if has_text(p_tag.get_text(strip=True)):
                                new_contents.append(p_tag)
                            else:
                                for item in list(p_tag.contents):
                                    new_contents.append(item)
                        non_structurals = []
                        new_contents.append(child)
                    else:
                        if isinstance(child, NavigableString) and not child.strip():
                            continue
                        non_structurals.append(child)
                if non_structurals:
                    p_tag = soup.new_tag('p')
                    for item in non_structurals:
                        p_tag.append(item)
                    if has_text(p_tag.get_text(strip=True)):
                        new_contents.append(p_tag)
                    else:
                        for item in list(p_tag.contents):
                            new_contents.append(item)
                tag.clear()
                for item in new_contents:
                    tag.append(item)
                tag.unwrap()
                continue

    # Wrap loose text nodes in <p> tags
    i = 0
    while i < len(soup.contents):
        if isinstance(soup.contents[i], NavigableString):
            text_nodes = []
            text_pieces = []
            j = i
            while j < len(soup.contents) and isinstance(soup.contents[j], NavigableString):
                text_nodes.append(soup.contents[j])
                text_pieces.append(str(soup.contents[j]))
                j += 1
            combined_text = ''.join(text_pieces).strip()
            if combined_text:
                p_tag = soup.new_tag('p')
                p_tag.string = combined_text
                for node in reversed(text_nodes):
                    node.extract()
                soup.insert(i, p_tag)
                i += 1
            else:
                for node in reversed(text_nodes):
                    node.extract()
        else:
            i += 1
    
    inline_tags = {'a', 'b', 'strong', 'i', 'em', 'u', 'sup', 'sub', 'br'}

    container = soup.body if soup.body else soup
    for child in list(container.children):
        if isinstance(child, Tag) and child.name in inline_tags:
            p_tag = soup.new_tag('p')
            child.wrap(p_tag)
    
    soup = convert_pseudo_headers(soup)

    # Merge same tags
    for _ in range(3):
        merge_same_tags(soup)

    # Clean text nodes (whitespace normalization)
    for text_node in soup.find_all(string=True):
        cleaned_text = re.sub(r'\s*\n+\s*(?=[,\.:;։՛`՞՝)\]\}])', '', text_node)
        cleaned_text = re.sub(r'\s*\n+\s*', ' ', cleaned_text)
        text_node.replace_with(cleaned_text)
    
    # Unwrap <p> tags inside 'li', 'td', or 'th'
    for parent in soup.find_all(['li', 'td', 'th']):
        children = list(parent.children)
        p_tags = [child for child in children if child.name == 'p']
        other_tags = [child for child in children if child.name not in [None, 'p', 'br']]
        meaningful_strings = any(isinstance(child, NavigableString) and child.strip() != '' for child in children)
        
        if not other_tags and not meaningful_strings:
            if len(p_tags) == 1:
                p_tags[0].unwrap()
            elif len(p_tags) > 1:
                total_br = len(parent.select('p br'))
                if total_br >= 2:
                    continue

                contents = [list(p.children) for p in p_tags]
                parent.clear()
                for i, content_list in enumerate(contents):
                    for element in content_list:
                        parent.append(element)
                    if i < len(contents) - 1:
                        parent.append(soup.new_tag('br'))

    # Remove unnecessary br tags
    remove_unnecessary_br(soup)

    remove_nbsp(soup)
    # Remove empty tags again
    remove_empty_tags(soup)

    # Merge same tags again (needed after p-unwrapping in td/th/li creates separate tags)
    for _ in range(3):
        merge_same_tags(soup)

    return soup

