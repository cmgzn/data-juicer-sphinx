"""Data-Juicer Sphinx Theme - A modern documentation theme."""

import json
from pathlib import Path

__version__ = "1.0.0"


def get_html_theme_path():
    return str(Path(__file__).parent)


def _update_context(app, pagename, templatename, context, doctree):
    """Add nav_links to template context."""
    nav_links_raw = app.config.html_theme_options.get("nav_links", [])
    if isinstance(nav_links_raw, str):
        try:
            nav_links_raw = json.loads(nav_links_raw) if nav_links_raw else []
        except (json.JSONDecodeError, TypeError):
            nav_links_raw = []
    context["theme_nav_links"] = nav_links_raw


def setup(app):
    app.add_html_theme("data_juicer_theme", str(Path(__file__).parent))
    app.connect("html-page-context", _update_context)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
