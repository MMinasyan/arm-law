"""Vendored HTML processing engine for arlis documents."""
from .lists import add_lists
from .structures import clean_html_tables
from .processor import clean_html
from .utilities import (
    add_style_tag,
    merge_same_url_links,
    remove_empty_tags,
    to_soup,
)
