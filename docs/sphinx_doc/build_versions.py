#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import argparse
import yaml
from pathlib import Path
import translators as ts
from packaging import version as pv

# Repository structure and build configuration
MIN_TAG = os.environ.get("MIN_TAG", "v0.0.0")  # Minimum version tag to build
PACKAGE_DIR = os.environ.get("PACKAGE_DIR", "data_juicer")  # API directory

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = REPO_ROOT / "docs" / "sphinx_doc" / "build"  # Build output directory
EXTRA_DATA_REL = Path("tests/ops/data")
WORKTREES_DIR = (
    REPO_ROOT / ".worktrees"
)  # Temporary worktree directory for version builds
DOCS_REL = Path("docs/sphinx_doc")
REMOTE = "origin"  # Git remote name
DEFAULT_LANGS = ["en", "zh_CN"]  # Default supported documentation languages

# Build options
KEEP_WORKTREES = False  # Whether to keep worktrees after build (default: cleanup)
HAS_SUBMODULES = False  # Set True if repo uses submodules and needs initialization


def run(cmd, cwd=None, env=None, check=True):
    """Execute shell command with logging"""
    print(f"[RUN] {' '.join(map(str, cmd))}")
    subprocess.run(cmd, cwd=cwd, env=env, check=check)


def is_valid_tag(tag: str) -> bool:
    """Check if tag matches version pattern and meets minimum version requirement"""
    if not re.match(r"^v\d+\.\d+\.\d+$", tag):
        return False
    try:
        return pv.parse(tag) >= pv.parse(MIN_TAG)
    except Exception:
        return False


def get_tags():
    """Fetch and filter valid version tags from remote repository"""
    run(["git", "fetch", "--tags", "--force", REMOTE])
    out = subprocess.check_output(["git", "tag"], text=True).strip()
    tags = [t for t in out.splitlines() if t]
    return [t for t in tags if is_valid_tag(t)]

def load_extra_assets_config():
    config_path = os.path.join(os.path.dirname(__file__), "source/extra_assets.yaml")
    if not os.path.exists(config_path):
        return {"assets": []}

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_clean_worktree(path: Path):
    """Remove existing worktree if present to ensure clean state"""
    if path.exists():
        try:
            run(["git", "worktree", "remove", "--force", str(path)])
        except Exception:
            shutil.rmtree(path, ignore_errors=True)


def copy_docs_source_to(wt_root: Path):
    """Copy current docs source to worktree to unify templates and extensions"""
    src = REPO_ROOT / DOCS_REL
    dst = wt_root / DOCS_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    print(f"[COPY] {src} -> {dst}")
    shutil.copytree(
        src,
        dst,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".git", "build", ".pyc"),
    )


def maybe_init_submodules(wt_root: Path):
    """Initialize submodules in worktree if repository uses them"""
    if HAS_SUBMODULES:
        try:
            run(["git", "submodule", "update", "--init", "--recursive"], cwd=wt_root)
        except Exception as e:
            print(f"[WARN] submodule init failed: {e}")


def create_index_rst(target_dir: Path):
    index_rst = target_dir / "index.rst"
    # index_ZH_rst = target_dir / "index_ZH.rst"
    if not index_rst.exists():
        print(f"[CREATE] index_rst: {index_rst}")
        folder_name = target_dir.name.capitalize()
        content = f"""\
{folder_name}
{'=' * len(folder_name)}

.. toctree::
    :maxdepth: 1
    :glob:

    ./*
    ./**/*
"""
        index_rst.write_text(content, encoding="utf-8")

#     if not index_ZH_rst.exists():
#         print(f"[CREATE] index_ZH_rst: {index_ZH_rst}")
#         # folder_name = ts.translate_text(
#         #     target_dir.name, translator="alibaba", from_language="en", to_language="zh"
#         # )
#         folder_name = target_dir.name.capitalize()
#         content = f"""\
# {folder_name}
# {'=' * len(folder_name) * 2}
# .. toctree::
#     :maxdepth: 1
#     :glob:

#     ./*
#     ./**/*
# """
#         index_ZH_rst.write_text(content, encoding="utf-8")


def copy_markdown_files(wt_root: Path):
    print(f"[TRACE] wt_root: {wt_root}")
    exclude_paths = ["outputs", "sphinx_doc", ".github"]
    for md_file in wt_root.rglob("*.md"):
        if any(path in str(md_file) for path in exclude_paths):
            continue
        if md_file.parent == wt_root and md_file.name.lower() in [
            "readme.md",
            "readme_zh.md",
        ]:
            target = wt_root / DOCS_REL / "source" / md_file.name
        else:
            target = (
                wt_root
                / DOCS_REL
                / "source"
                / md_file.relative_to(wt_root)
            )
        target_dir = target.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        if not target.exists():
            print(f"[COPY] {md_file} -> {target}")
            shutil.copy2(md_file, target)

        # Create index.rst for operators (data-juicer)
        if "/operators/" in str(md_file):
            create_index_rst(target_dir)

    docs_path = wt_root / Path("docs")
    for rst_file in docs_path.rglob("*.rst"):
        if any(path in str(rst_file) for path in exclude_paths):
            continue
        target = (
            wt_root / DOCS_REL / "source" / rst_file.relative_to(wt_root)
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            print(f"[COPY] {rst_file} -> {target}")
            shutil.copy2(rst_file, target)

    assets_list = load_extra_assets_config()["assets"]
    
    for asset_rel_path in assets_list:
        if (wt_root / asset_rel_path).exists():
            shutil.copytree(
                wt_root / asset_rel_path,
                wt_root / DOCS_REL / "source" / "extra" / asset_rel_path,
                dirs_exist_ok=True,
            )

def build_one(
    ref: str,
    ref_label: str,
    available_versions: list[str],
    enable_api_doc: bool = True,
    langs: list[str] = None,
):
    """Build documentation for a single version/branch"""
    if langs is None:
        langs = DEFAULT_LANGS

    # Create and setup worktree for the specific git reference
    wt = WORKTREES_DIR / ref_label
    ensure_clean_worktree(wt)
    run(["git", "worktree", "add", "--force", str(wt), ref])
    maybe_init_submodules(wt)

    # Override docs/sphinx_doc with current repo version for unified templates
    copy_docs_source_to(wt)
    copy_markdown_files(wt)

    src = wt / DOCS_REL / "source"
    if not src.exists():
        print(f"[SKIP] {ref_label}: {src} not found")
        if not KEEP_WORKTREES:
            run(["git", "worktree", "remove", "--force", str(wt)])
        return

    # Build documentation for each supported language
    for lang in langs:
        out_dir = SITE_DIR / lang / ref_label
        out_dir.mkdir(parents=True, exist_ok=True)

        # Setup environment variables for Sphinx build
        env = os.environ.copy()
        env["DOCS_VERSION"] = (
            ref_label  # Documentation version label (e.g., latest, v1.5.0)
        )
        env["GIT_REF_FOR_LINKS"] = ref  # Git reference for GitHub links
        env["AVAILABLE_VERSIONS"] = ",".join(
            available_versions
        )  # All available versions for switcher
        env["REPO_ROOT"] = str(wt)  # Version-specific code root for autodoc imports

        # Generate the API rst files (only if enabled)
        if enable_api_doc:
            api_cmd = [
                "sphinx-apidoc",
                "-o",
                str(wt / DOCS_REL / "source" / "api"),
                str(wt / PACKAGE_DIR),
                "-t",
                "_templates",
                "-e",
            ]
            run(api_cmd, env=env)

        # Execute Sphinx build command
        cmd = [
            "sphinx-build",
            "-b",
            "html",  # HTML builder
            "-D",
            f"language={lang}",  # Set language for this build
            "-j",
            "auto",
            str(src),  # Source directory
            str(out_dir),  # Output directory
        ]
        run(cmd, env=env)

    # Cleanup worktree after successful build
    if not KEEP_WORKTREES:
        run(["git", "worktree", "remove", "--force", str(wt)])
        try:
            run(["git", "worktree", "prune"])  # Clean up worktree references
        except Exception:
            pass


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Build multi-version documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s                                          # Default: build main branch, API docs enabled
  %(prog)s -A                                       # Disable API documentation generation
  %(prog)s --tags                                   # Build all valid tags
  %(prog)s --tags v1.5.0 v1.6.0                    # Build only specified tags (skip if not exist)
  %(prog)s --branches main dev                      # Build specified branches with all tags
  %(prog)s --branches main dev --languages en zh    # Build with English and Chinese docs
  %(prog)s -l en zh -A                              # Short form: build en/zh docs without API
        """,
    )

    parser.add_argument(
        "--no-api-doc",
        "-A",
        action="store_true",
        help="Disable API documentation generation (default: API docs enabled)",
    )

    parser.add_argument(
        "--tags",
        nargs="*",  # 0 or more arguments
        default=None,
        metavar="TAG",
        help="Specify tag list to build. Use '--tags' without arguments to build all valid tags, "
        "or '--tags v1.5.0 v1.6.0' to build specific tags. "
        "If not specified, no tags will be built (branches only). "
        "Non-existent tags will be skipped.",
    )

    parser.add_argument(
        "--branches",
        nargs="+",
        default=["main"],
        metavar="BRANCH",
        help="Specify branch list to build (default: ['main'])",
    )

    parser.add_argument(
        "--languages",
        "-l",
        nargs="+",
        default=DEFAULT_LANGS,
        metavar="LANG",
        help=f"Specify language list for documentation (default: {DEFAULT_LANGS}). "
        "Example: --languages en zh",
    )

    return parser.parse_args()


def main():
    """Main entry point: build documentation for all versions"""
    args = parse_args()

    print(
        f"[CONFIG] API documentation generation: {'Disabled' if args.no_api_doc else 'Enabled'}"
    )
    print(f"[CONFIG] Build branches: {args.branches}")
    print(f"[CONFIG] Languages: {args.languages}")

    WORKTREES_DIR.mkdir(exist_ok=True)

    # Get version list
    versions = list(args.branches)  # Start with branches specified from command line
    tags_to_build = []

    # Handle tags parameter
    if args.tags is not None:  # --tags was specified
        all_tags = get_tags()
        all_tags.sort(key=pv.parse, reverse=True)

        if len(args.tags) == 0:  # --tags without arguments: build all valid tags
            tags_to_build = all_tags
            print(f"[INFO] Building all {len(tags_to_build)} valid tags")
        else:  # --tags with specific tags: build only those that exist
            available_tags_set = set(all_tags)
            for tag in args.tags:
                if tag in available_tags_set:
                    tags_to_build.append(tag)
                else:
                    print(f"[WARN] Tag '{tag}' not found or invalid, skipping")

            if tags_to_build:
                # Sort the specified tags by version
                tags_to_build.sort(key=pv.parse, reverse=True)
                print(
                    f"[INFO] Building {len(tags_to_build)} specified tags: {tags_to_build}"
                )
            else:
                print(f"[INFO] No valid tags to build")

        versions.extend(tags_to_build)
    else:
        print(f"[INFO] No tags specified, building branches only")

    print(f"[INFO] Total {len(versions)} versions to build: {versions}")

    enable_api_doc = not args.no_api_doc

    # Build all specified branches
    for branch in args.branches:
        print(f"[BUILD] Building branch: {branch}")
        build_one(branch, branch, versions, enable_api_doc, args.languages)

    # Build all tags (if any)
    for tag in tags_to_build:
        print(f"[BUILD] Building tag: {tag}")
        build_one(tag, tag, versions, enable_api_doc, args.languages)


if __name__ == "__main__":
    main()
