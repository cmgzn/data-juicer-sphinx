# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import re
import sys
import yaml

# ========== REPO CONFIG ==========
PROJECT = os.environ.get("PROJECT", "data-juicer")
REPO_OWNER = os.environ.get("REPO_OWNER", "datajuicer")
HTML_TITLE = os.environ.get(
    "HTML_TITLE", " ".join([v.capitalize() for v in PROJECT.split("-")])
)

CURRENT_VERSION = os.environ.get("DOCS_VERSION", "")
GIT_REF_FOR_LINKS = os.environ.get("GIT_REF_FOR_LINKS", "main")
AVAILABLE_VERSIONS = [
    v for v in os.environ.get("AVAILABLE_VERSIONS", "").split(",") if v
]
REPO_ROOT = os.environ.get("REPO_ROOT")

# -- Path setup --------------------------------------------------------------
current_dir = os.path.dirname(__file__)
if REPO_ROOT and os.path.isdir(REPO_ROOT):
    sys.path.insert(0, os.path.abspath(REPO_ROOT))
else:
    sys.path.insert(0, os.path.abspath("../../"))
sys.path.insert(0, current_dir)

from custom_myst import ReplaceVideoLinksTransform

# -- Project information -----------------------------------------------------
project = PROJECT
copyright = "2024, Data-Juicer Team"
author = "Data-Juicer Team"

# -- General configuration ---------------------------------------------------
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
language = "en"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "myst_parser",
    "sphinx_copybutton",
]

# -- Extension configuration ------------------------------------------------
myst_heading_anchors = 4
myst_enable_extensions = [
    "linkify",
    "tasklist",
]

autosectionlabel_prefix_document = True
autosummary_generate = True
autosummary_ignore_module_all = False
autodoc_member_order = "bysource"

# -- Templates and patterns -------------------------------------------------
templates_path = ["_templates"]
exclude_patterns = ["build"]

# -- Options for HTML output ------------------------------------------------
html_theme = "pydata_sphinx_theme"
html_title = HTML_TITLE

html_theme_options = {
    "logo": {
        "text": HTML_TITLE,
        "image_light": "_static/images/icon.png",
        "image_dark": "_static/images/icon.png",
    },
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["navbar-icon-links", "theme-switcher", "version-language-switcher"],
    "navbar_persistent": ["search-button"],
    "icon_links": [
        {
            "name": "GitHub",
            "url": f"https://github.com/{REPO_OWNER}/{PROJECT}",
            "icon": "fa-brands fa-github",
            "type": "fontawesome",
        },
    ],
    # navigation settings
    "show_toc_level": 0,
    "navigation_depth": 3,
    "show_nav_level": 1,
    "show_prev_next": True,
    # edit button
    "use_edit_page_button": False,
    # footer
    "footer_start": ["copyright"],
    "footer_end": ["sphinx-version", "theme-version"],
    # search
    "search_bar_text": "Search docs...",
    # other options
    "collapse_navigation": True,
    "navigation_with_keys": True,
}

html_sidebars = {
    "**": [
        "sidebar-nav-bs",
    ],
}

# Static files
html_css_files = [
    "custom.css",
]
html_static_path = ["_static"]
html_extra_path = ["extra"]
html_favicon = "_static/images/icon.png"

# -- Internationalization settings ------------------------------------------
language = "en"
locale_dirs = ["locale/"]
gettext_compact = False

supported_languages = {
    "en": "English",
    "zh_CN": "简体中文",
}


# ========== LOAD EXTERNAL LINKS CONFIG ==========
def load_external_links_config():
    config_path = os.path.join(os.path.dirname(__file__), "external_links.yaml")
    if not os.path.exists(config_path):
        return {"projects": {}, "link_order": []}

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_external_links(current_project, language, version):
    """
    Build a list of external links based on the configuration file, excluding the current project.

    Args:
        current_project: Name of the current project
        language: Current language
        version: Current version

    Returns:
        A list of external link configurations
    """
    config = load_external_links_config()
    projects = config.get("projects", {})
    link_order = config.get("link_order", [])
    url_template = config.get(
        "url_template",
        "https://{REPO_OWNER}.github.io/{project}/{language}/{version}/index.html",
    )

    external_links = []

    project_list = link_order if link_order else sorted(projects.keys())

    for project_name in project_list:
        if project_name == current_project:
            continue

        if project_name not in projects:
            continue

        project_info = projects[project_name]

        url = url_template.format(
            project=project_info.get("repo_name", project_name),
            language=language,
            version="main",  # Use "main" as default version
        )

        if language == "zh_CN":
            url = url.replace("index", "index_ZH")

        external_links.append(
            {
                "name": project_info.get("display_name", project_name),
                "url": url,
            }
        )

    return external_links


def get_lang_link(language, pagename, lang_code, non_zh_pages=[], current_version=""):
    def norm_pagename(p):
        return os.path.normpath(p)

    norm_non_zh_pages = set(map(norm_pagename, non_zh_pages))
    target_page = pagename

    if "CN" in language and pagename.endswith("_ZH") and "CN" not in lang_code:
        target_page = pagename[:-3]
    if "CN" in lang_code and not pagename.endswith("_ZH"):
        if norm_pagename(pagename) not in norm_non_zh_pages:
            target_page += "_ZH"

    return f"{lang_code}/{current_version}/{target_page}.html"


html_context = {
    "supported_languages": supported_languages,
    "get_lang_link": get_lang_link,
    "current_version": CURRENT_VERSION,
    "available_versions": AVAILABLE_VERSIONS,
    "github_user": REPO_OWNER,
    "github_repo": PROJECT,
    "github_version": GIT_REF_FOR_LINKS,
    "doc_path": "docs",
}


# -- setup configuration ------------------------------------------------
def find_zh_exclusions(app, config):
    """Find Chinese translation files to exclude when building English documentation"""
    non_zh_pages = set()
    zh_exclusions = []

    for root, dirs, files in os.walk(app.srcdir):
        for file in files:
            if not file.endswith(("_ZH.md", "_ZH.rst")):
                base_name, ext = os.path.splitext(file)
                zh_file = f"{base_name}_ZH{ext}"
                zh_file_path = os.path.join(root, zh_file)
                rel_path = os.path.normpath(
                    os.path.relpath(os.path.join(root, file), app.srcdir)
                )

                if os.path.exists(zh_file_path):
                    zh_exclusions.append(rel_path)
                else:
                    non_zh_pages.add(
                        os.path.normpath(
                            os.path.relpath(os.path.join(root, base_name), app.srcdir)
                        )
                    )

    if config.language == "zh_CN":
        config.exclude_patterns.extend(zh_exclusions)
    else:
        config.exclude_patterns.extend(["*_ZH*", "**/*_ZH*"])

    app.config.html_context.setdefault("non_zh_pages", set()).update(non_zh_pages)


def rebuild_source_dir(app, config):
    """Rebuild source directory for documentation"""
    find_zh_exclusions(app, config)


def skip(app, what, name, obj, would_skip, options):
    """Control which members to skip in documentation"""
    if name == "__init__":
        return False
    return would_skip


def process_doc_links(app, docname, source):
    """Process and update documentation links"""
    repo_base = f"https://github.com/{REPO_OWNER}/{PROJECT}/blob/{GIT_REF_FOR_LINKS}/"

    def link_replacer(match):
        text, path = match.group(1), match.group(2)
        abs_path = os.path.normpath(
            os.path.join(os.path.dirname(docname), path)
        ).replace("docs_index/", "")
        return f"[{text}]({repo_base}{abs_path})"

    pattern = r"\[([^\]]+)\]\((?!http|#)([^)]*(?<!\.md)(?<!\.rst))\)"
    source[0] = re.sub(pattern, link_replacer, source[0])
    return source[0]


def process_tutorial(app, docname, source):
    """Process tutorial during reading"""
    overview_placeholder = ""
    if app.config.language == "zh_CN":
        overview_placeholder = "- [DJ概览](../../README_ZH.md)"
    else:
        overview_placeholder = "- [Overview of DJ](../../README.md)"
    source[0] = source[0].replace(overview_placeholder, "")
    pattern = r"(?i)\nen[A-Za-z\s]{0,12}\|\s*\[\u4e2d\u6587[\u4e00-\u9fa5\s]{0,12}\]\([^)]+\.md\)|\n\u4e2d\u6587[\u4e00-\u9fa5\s]{0,12}\|\s*\[en[A-Za-z\s]{0,12}\]\([^)]+\.md\)"
    source[0] = re.sub(pattern, "", source[0])
    return source[0]


def process_read(app, docname, source):
    """Process document during reading"""
    source[0] = process_tutorial(app, docname, source)
    source[0] = process_doc_links(app, docname, source)


def setup(app):
    """Setup Sphinx application hooks"""
    app.add_transform(ReplaceVideoLinksTransform)
    app.connect("config-inited", rebuild_source_dir)
    external_links = build_external_links(
        current_project=PROJECT, language=app.config.language, version=CURRENT_VERSION
    )
    app.config.html_theme_options.update({"external_links": external_links})
    app.config.root_doc = "index_ZH" if app.config.language == "zh_CN" else "index"

    app.connect("source-read", process_read)
    app.connect("autodoc-skip-member", skip)
