"""HTML processing tools for cleaning and restructuring messy HTML."""


from .lists import add_lists
from .utilities import (
    to_soup,
    add_style_tag,
    remove_empty_tags,
    remove_word_comments,
    merge_same_url_links
)


__all__ = [
    'clean_html',
    'simple_process',
    'convert_to_html',
    'add_lists',
    'clean_html_tables',
    'split_p_by_br',
    'process_meter',
    'to_soup',
    'add_style_tag',
    'remove_empty_tags',
    'remove_word_comments',
    'merge_same_url_links',
]
