#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import argparse
import hashlib
import tempfile
import time
import yaml
from pathlib import Path
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
    """Refresh build support while retaining the version's documentation."""
    src = REPO_ROOT / DOCS_REL
    dst = wt_root / DOCS_REL
    dst.parent.mkdir(parents=True, exist_ok=True)

    def is_version_content(path, source):
        relative = path.relative_to(source)
        if relative.parts[0] in {"_static", "_templates", "extra", "locale"}:
            return False
        return path.suffix in {".rst", ".md"} or relative.as_posix() == "extra_assets.yaml"

    # These files belong to the tag, not to the checkout launching the build.
    # Keep its indices, authored pages and asset manifest before refreshing
    # conf.py, extensions, templates and shared static assets.
    version_source = dst / "source"
    preserved = {
        path.relative_to(dst): path.read_bytes()
        for path in version_source.rglob("*")
        if path.is_file() and is_version_content(path, version_source)
    }
    has_version_docs = any(path.suffix in {".rst", ".md"} for path in preserved)

    def ignore(directory, names):
        ignored = set(shutil.ignore_patterns(".git", "build", "__pycache__", "*.pyc")(directory, names))
        directory = Path(directory)
        if has_version_docs and directory.is_relative_to(src / "source"):
            ignored.update(
                name for name in names
                if (directory / name).is_file()
                and is_version_content(directory / name, src / "source")
            )
        return ignored

    if dst.exists():
        shutil.rmtree(dst)
    print(f"[COPY] {src} -> {dst}")
    shutil.copytree(src, dst, ignore=ignore)
    for relative, content in preserved.items():
        target = dst / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


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
            target = wt_root / DOCS_REL / "source" / md_file.relative_to(wt_root)
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
        target = wt_root / DOCS_REL / "source" / rst_file.relative_to(wt_root)
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
            # Also mirror assets into the source tree at their project-relative
            # path so Sphinx's image collector can resolve relative image
            # references (e.g. ![img](imgs/TEST.png)) in collected Markdown.
            shutil.copytree(
                wt_root / asset_rel_path,
                wt_root / DOCS_REL / "source" / asset_rel_path,
                dirs_exist_ok=True,
            )


def build_one(
    ref: str,
    ref_label: str,
    available_versions: list[str],
    enable_api_doc: bool = True,
    langs: list[str] = None,
    use_worktree: bool = True,
):
    """Build documentation for a single version/branch.

    With use_worktree=False the current checkout (REPO_ROOT) is built in place
    (used by --current for PR previews): no worktree creation/cleanup and no
    template overlay, since the checkout already carries the current source.
    """
    if os.environ.get("SPHINX_CACHE_DIR"):
        return build_cached(ref, ref_label, available_versions, enable_api_doc, langs, use_worktree)

    if langs is None:
        langs = DEFAULT_LANGS

    if use_worktree:
        # Create and setup worktree for the specific git reference
        wt = WORKTREES_DIR / ref_label
        ensure_clean_worktree(wt)
        run(["git", "worktree", "add", "--force", str(wt), ref])
        maybe_init_submodules(wt)

        # Share current build support, retaining this version's documentation
        copy_docs_source_to(wt)
        copy_markdown_files(wt)
        wt_root = wt
    else:
        wt_root = REPO_ROOT
        copy_markdown_files(wt_root)

    src = wt_root / DOCS_REL / "source"
    if not src.exists():
        print(f"[SKIP] {ref_label}: {src} not found")
        if use_worktree and not KEEP_WORKTREES:
            run(["git", "worktree", "remove", "--force", str(wt_root)])
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
        env["REPO_ROOT"] = str(wt_root)  # Version-specific code root for autodoc imports

        # Generate the API rst files (only if enabled)
        if enable_api_doc:
            api_cmd = [
                "sphinx-apidoc",
                "-o",
                str(wt_root / DOCS_REL / "source" / "api"),
                str(wt_root / PACKAGE_DIR),
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
    if use_worktree and not KEEP_WORKTREES:
        run(["git", "worktree", "remove", "--force", str(wt_root)])
        try:
            run(["git", "worktree", "prune"])  # Clean up worktree references
        except Exception:
            pass


# 缓存仅保存本脚本生成的状态；站点复制只过滤这些专用记录。
CACHE_SCHEMA = "pages-v2-1"
CACHE_RECORD = ".sphinx-cache-state.json"
SITE_IGNORES = {".git", ".doctrees", ".buildinfo", CACHE_RECORD}
INPUT_IGNORES = SITE_IGNORES | {
    "build",
    "cache",
    ".cache",
    "__pycache__",
    ".worktrees",
    ".venv",
    ".pytest_cache",
}
RENDER_KEYS = {
    "PROJECT",
    "REPO_OWNER",
    "HTML_TITLE",
    "JUICER_API_URL",
    "AVAILABLE_VERSIONS",
    "GIT_REF_FOR_LINKS",
    "BASEURL",
    "BASE_URL",
    "HTML_BASEURL",
    "SOURCE_DATE_EPOCH",
    "LANG",
    "LC_ALL",
    "TZ",
    "PYTHONPATH",
    "PYTHONHASHSEED",
    "GITHUB_REPOSITORY",
    "GITHUB_REPOSITORY_OWNER",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def no_symlinks(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError(f"拒绝符号链接路径: {path}")
    return path


def file_snapshot(root, ignored=frozenset(), excluded=()):
    """只读取普通文件，记录完整内容及纳秒时间；绝不反序列化 doctree。"""
    root = no_symlinks(root)
    result = {}
    if not root.exists():
        return result
    if not root.is_dir():
        raise ValueError(f"不是目录: {root}")

    def fail(error):
        raise error

    for directory, dirs, files in os.walk(root, onerror=fail):
        dirs[:] = sorted(d for d in dirs if d not in ignored)
        for name in dirs + sorted(files):
            path = Path(directory) / name
            if name in ignored or path in excluded or (ignored == INPUT_IGNORES and name.endswith(".pyc")):
                if name in dirs:
                    dirs.remove(name)
                continue
            no_symlinks(path)
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError(f"不是普通文件: {path}")
            result[path.relative_to(root).as_posix()] = {
                "hash": hashlib.sha256(path.read_bytes()).hexdigest(),
                "mtime": path.stat().st_mtime_ns,
            }
    return result


def content_hashes(snapshot):
    return {name: item["hash"] for name, item in snapshot.items()}


def copy_safe(source, destination, ignored=frozenset()):
    no_symlinks(destination)
    for name in file_snapshot(source, ignored):
        target = destination / name
        no_symlinks(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)


def remove_directory(path):
    no_symlinks(path)
    if path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def output_path(lang, label):
    # ref 可含分支层级，但不能越过对应语言目录。
    for value in (lang, label):
        if not value or any(part in {"", ".", ".."} for part in value.split("/")) or "\\" in value:
            raise ValueError(f"不安全的语言或版本: {value!r}")
    if "/" in lang:
        raise ValueError(f"不安全的语言: {lang!r}")
    return no_symlinks(SITE_DIR / lang / label)


def cache_directory():
    raw = Path(os.environ["SPHINX_CACHE_DIR"])
    if not raw.is_absolute():
        raise ValueError("SPHINX_CACHE_DIR 必须为绝对目录")
    root = no_symlinks(raw).resolve()
    docs = (REPO_ROOT / DOCS_REL).resolve()
    if root.is_relative_to(docs) or docs.is_relative_to(root):
        raise ValueError("SPHINX_CACHE_DIR 必须独立于 docs/sphinx_doc")
    return root


def entry_page(lang):
    return "index_ZH.html" if lang == "zh_CN" else "index.html"


def cache_manifest(entry):
    return {name: content_hashes(file_snapshot(entry / name)) for name in ("html", "doctrees")}


def load_cache(entry, lang):
    try:
        no_symlinks(entry / CACHE_RECORD)
        state = json.loads((entry / CACHE_RECORD).read_text(encoding="utf-8"))
        if state["schema"] != CACHE_SCHEMA or state["manifest"] != cache_manifest(entry):
            return None
        if not {entry_page(lang), ".buildinfo"} <= state["manifest"]["html"].keys():
            return None
        if "environment.pickle" not in state["manifest"]["doctrees"]:
            return None
        for name, item in state["snapshot"].items():
            if Path(name).is_absolute() or ".." in Path(name).parts:
                return None
            if (
                not isinstance(item["mtime"], int)
                or not 0 <= item["mtime"] < 2**63
                or not re.fullmatch(r"[0-9a-f]{64}", item["hash"])
            ):
                return None
        if not all(isinstance(state[key], str) for key in ("fingerprint", "compatibility")):
            return None
        return state
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def write_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    no_symlinks(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(state, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def restore_mtimes(root, previous, excluded=()):
    snapshot = file_snapshot(root, INPUT_IGNORES, excluded)
    for name, item in snapshot.items():
        old = previous.get(name)
        if old:
            path = root / name
            # 内容变化即使保留了旧时间，也必须让 Sphinx 的依赖检查失效。
            stamp = (
                old["mtime"] if old["hash"] == item["hash"] else max(time.time_ns(), item["mtime"], old["mtime"] + 1)
            )
            os.utime(path, ns=(path.stat().st_atime_ns, stamp))
    return file_snapshot(root, INPUT_IGNORES, excluded)


def cache_keys(tree, wt, out, lang, env, enable_api_doc, root, use_worktree):
    excluded = (root, SITE_DIR, WORKTREES_DIR)
    support = {
        str(path): content_hashes(file_snapshot(REPO_ROOT / path, INPUT_IGNORES, excluded))
        for path in (DOCS_REL, Path("data_juicer_sphinx_theme"), Path("scripts"), Path("_templates"))
    }
    support["builder"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    render_env = {
        key: value
        for key, value in env.items()
        if (key in RENDER_KEYS or key.startswith(("DOCS_", "HTML_", "REPO_", "SPHINX_", "LC_")))
        and not key.startswith("SPHINX_CACHE_")
    }
    compatibility = digest(
        {
            "schema": CACHE_SCHEMA,
            "context": os.environ.get("SPHINX_CACHE_CONTEXT", ""),
            "support": support,
            # 版本选择器只影响 HTML；变化时仍可复用解析结果。
            "env": {key: value for key, value in render_env.items() if key != "AVAILABLE_VERSIONS"},
            "api": enable_api_doc,
            "package": PACKAGE_DIR,
            "lang": lang,
            "paths": [str(wt), str(out), str(root), str(Path.cwd())],
        }
    )
    inputs = tree if use_worktree else content_hashes(file_snapshot(REPO_ROOT, INPUT_IGNORES, excluded))
    return compatibility, digest([compatibility, tree, inputs, render_env])


def build_cached(ref, ref_label, available_versions, enable_api_doc=True, langs=None, use_worktree=True):
    """先校验命中，再按语言恢复兼容状态；冷构建失败直接向上传递。"""
    langs = DEFAULT_LANGS if langs is None else langs
    root = cache_directory()
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        # 保留 worktree 对仅有远端 main 的支持，不猜测其他 ref 或当前提交。
        if not use_worktree or ref != "main":
            raise
        commit = subprocess.check_output(
            ["git", "rev-parse", "--verify", f"refs/remotes/{REMOTE}/main^{{commit}}"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
    tree = subprocess.check_output(
        ["git", "rev-parse", f"{commit}^{{tree}}"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    wt = WORKTREES_DIR / digest(ref_label) if use_worktree else REPO_ROOT
    no_symlinks(wt)
    if use_worktree and (root.is_relative_to(wt) or wt.is_relative_to(root)):
        raise ValueError("缓存不能与临时 worktree 重叠")
    excluded = (root, SITE_DIR, WORKTREES_DIR)
    pending = []
    for lang in langs:
        out = output_path(lang, ref_label)
        env = os.environ.copy()
        env.update(
            DOCS_VERSION=ref_label,
            GIT_REF_FOR_LINKS=ref,
            AVAILABLE_VERSIONS=",".join(available_versions),
            REPO_ROOT=str(wt),
        )
        compatibility, fingerprint = cache_keys(tree, wt, out, lang, env, enable_api_doc, root, use_worktree)
        entry = root / f"schema-{CACHE_SCHEMA}" / digest([ref_label, lang])
        no_symlinks(entry)
        state = None if os.environ.get("SPHINX_CACHE_FORCE") == "1" else load_cache(entry, lang)
        if state and state["compatibility"] != compatibility:
            state = None
        print(f"[cache] {ref_label}/{lang} fingerprint={fingerprint}")
        if state and state["fingerprint"] == fingerprint:
            remove_directory(out)
            copy_safe(entry / "html", out, SITE_IGNORES)
            write_state(out / CACHE_RECORD, {"ref": ref_label, "lang": lang})
            print(f"[cache] hit/skip {ref_label}/{lang}")
            continue
        if state is None:
            remove_directory(entry)
        else:
            (entry / CACHE_RECORD).unlink()
        remove_directory(out)
        pending.append((lang, out, env, entry, state, compatibility, fingerprint))
    if not pending:
        return False

    try:
        if use_worktree:
            WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
            ensure_clean_worktree(wt)
            run(["git", "worktree", "add", "--force", "--detach", str(wt), commit])
            maybe_init_submodules(wt)
            file_snapshot(wt, INPUT_IGNORES, excluded)
            copy_docs_source_to(wt)
        copy_markdown_files(wt)
        src = wt / DOCS_REL / "source"
        if not src.is_dir():
            raise ValueError(f"缺少文档源目录: {src}")
        for lang, out, env, entry, state, compatibility, fingerprint in pending:
            if enable_api_doc:
                run(["sphinx-apidoc", "-o", str(src / "api"), str(wt / PACKAGE_DIR), "-t", "_templates", "-e"], env=env)
            # 各语言保留独立快照，不能用第一种语言的时间覆盖第二种语言的基线。
            restore_mtimes(wt, state["snapshot"] if state else {}, excluded)
            buildinfo = (entry / "html" / ".buildinfo").read_bytes() if state else None
            for attempt in range(2 if state else 1):
                remove_directory(out)
                out.mkdir(parents=True, exist_ok=True)
                if buildinfo is not None:
                    (out / ".buildinfo").write_bytes(buildinfo)
                doctrees = entry / "doctrees"
                doctrees.mkdir(parents=True, exist_ok=True)
                print(f"[cache] build {ref_label}/{lang} reuse={bool(state and attempt == 0)}")
                try:
                    # HTML 总是清空并重写；只让兼容的 doctree 参与增量读取。
                    run(
                        [
                            "sphinx-build",
                            "-b",
                            "html",
                            "-D",
                            f"language={lang}",
                            "-j",
                            "auto",
                            "-a",
                            "-d",
                            str(doctrees),
                            str(src),
                            str(out),
                        ],
                        env=env,
                    )
                    if not (out / entry_page(lang)).is_file():
                        raise ValueError(f"构建缺少入口: {out / entry_page(lang)}")
                    break
                except (subprocess.CalledProcessError, OSError, ValueError):
                    remove_directory(entry)
                    remove_directory(out)
                    if not state or attempt:
                        raise
                    print(f"[cache] {ref_label}/{lang} 复用失败，冷重试一次")
                    buildinfo = None
            remove_directory(entry / "html")
            copy_safe(out, entry / "html")
            snapshot = file_snapshot(wt, INPUT_IGNORES, excluded)
            manifest = cache_manifest(entry)
            if ".buildinfo" not in manifest["html"] or "environment.pickle" not in manifest["doctrees"]:
                raise ValueError(f"构建缺少缓存状态: {ref_label}/{lang}")
            if not use_worktree:
                # 原地构建会收集文档和生成 rst，持久化最终内容，避免下一次误判为变化。
                compatibility, fingerprint = cache_keys(tree, wt, out, lang, env, enable_api_doc, root, use_worktree)
            write_state(
                entry / CACHE_RECORD,
                {
                    "schema": CACHE_SCHEMA,
                    "compatibility": compatibility,
                    "fingerprint": fingerprint,
                    "snapshot": snapshot,
                    "manifest": manifest,
                },
            )
            (out / ".buildinfo").unlink(missing_ok=True)
            write_state(out / CACHE_RECORD, {"ref": ref_label, "lang": lang})
    finally:
        if use_worktree and not KEEP_WORKTREES and wt.exists():
            run(["git", "worktree", "remove", "--force", str(wt)])
    return True


def report_cache_changed(changed):
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write(f"cache_changed={str(bool(changed)).lower()}\n")


def assemble_site(previous, publish):
    """只组装文件：以最新历史快照为底，本次双语版本整个替换。"""
    previous, publish, current = (no_symlinks(Path(p)).resolve() for p in (previous, publish, SITE_DIR))
    for left, right in ((previous, publish), (current, publish), (previous, current)):
        if left.is_relative_to(right) or right.is_relative_to(left):
            raise ValueError("历史、本次构建及发布目录必须互相独立")
    if not previous.is_dir() or not current.is_dir():
        raise ValueError("历史快照及本次构建目录必须存在；首次发布请提供空历史目录")
    file_snapshot(previous, SITE_IGNORES)
    file_snapshot(current, SITE_IGNORES)
    refs = set()
    for lang in DEFAULT_LANGS:
        directory = current / lang
        if not directory.exists():
            continue
        for path, dirs, files in os.walk(directory):
            dirs[:] = [name for name in dirs if name not in SITE_IGNORES]
            if Path(path) == directory:
                continue
            # 允许分支层级；遇到版本输出即停止下钻，残缺输出也必须接受双语校验。
            if any(name not in SITE_IGNORES or name == CACHE_RECORD for name in files) or not dirs:
                refs.add(Path(path).relative_to(directory).as_posix())
                dirs.clear()
    for ref in refs:
        for lang in DEFAULT_LANGS:
            if not (current / lang / ref / entry_page(lang)).is_file():
                raise ValueError(f"本次输出缺少双语入口: {lang}/{ref}/{entry_page(lang)}")
    publish.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".sphinx-publish-", dir=publish.parent) as temporary:
        staging = Path(temporary) / "site"
        staging.mkdir()
        copy_safe(previous, staging, SITE_IGNORES)
        for ref in refs:
            for lang in DEFAULT_LANGS:
                remove_directory(staging / lang / ref)
        copy_safe(current, staging, SITE_IGNORES)
        versions = set()
        for lang in DEFAULT_LANGS:
            directory = staging / lang
            if directory.is_dir():
                versions.update(path.name for path in directory.iterdir() if path.is_dir())
        versions = {
            ref
            for ref in versions
            if (ref == "main" or (ref == ref.strip() and is_valid_tag(ref)))
            and all((staging / lang / ref / entry_page(lang)).is_file() for lang in DEFAULT_LANGS)
        }
        ordered = (["main"] if "main" in versions else []) + sorted(versions - {"main"}, key=pv.parse, reverse=True)
        (staging / "versions.json").write_text(json.dumps({"versions": ordered}, indent=2), encoding="utf-8")
        remove_directory(publish)
        os.replace(staging, publish)
    print(f"[SITE] {publish}: {ordered}")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Build multi-version documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s                                          # Default: build main branch, API docs enabled
  %(prog)s -A                                       # Disable API documentation generation
  %(prog)s --tags                                   # Build all valid tags plus branches
  %(prog)s --tags v1.5.0 v1.6.0                    # Build only specified tags (skip if not exist)
  %(prog)s --branches --tags v1.5.0                # Tag-only build ('--branches' without values)
  %(prog)s --branches main dev                      # Build specified branches with all tags
  %(prog)s --branches main dev --languages en zh    # Build with English and Chinese docs
  %(prog)s -l en zh -A                              # Short form: build en/zh docs without API
  %(prog)s --current preview -A                     # Build the current checkout (PR preview)
  %(prog)s --emit-versions-json                     # Write build/versions.json and exit
        """,
    )

    parser.add_argument(
        "--assemble-site",
        nargs=2,
        metavar=("PREVIOUS_DIR", "PUBLISH_DIR"),
        help="仅合并历史快照和本次 build，不运行 Sphinx 或获取 Git refs",
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
        nargs="*",
        default=None,
        metavar="BRANCH",
        help="Specify branch list to build (default: ['main']). "
        "Use '--branches' without values to build no branches (tag-only builds).",
    )

    parser.add_argument(
        "--current",
        nargs="?",
        const="current",
        default=None,
        metavar="LABEL",
        help="Build the current checkout in place (no git worktree), output to "
        "build/<lang>/<LABEL>/. Intended for PR previews. Optional LABEL "
        "defaults to 'current'.",
    )

    parser.add_argument(
        "--emit-versions-json",
        action="store_true",
        help="Write the full version list (main + valid tags) to build/versions.json "
        "for the runtime version switcher, then exit without building.",
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

    if args.assemble_site:
        assemble_site(*args.assemble_site)
        return

    if args.emit_versions_json:
        emit_versions_json()
        return

    if args.current is not None:
        # Build the current checkout in place (PR preview mode, no worktree)
        ref = os.environ.get("GITHUB_SHA")
        if not ref:
            ref = (
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], text=True
                ).strip()
            )
        print(f"[BUILD] Building current checkout as '{args.current}' (ref {ref})")
        changed = build_one(
            ref,
            args.current,
            [args.current],
            not args.no_api_doc,
            args.languages,
            use_worktree=False,
        )
        report_cache_changed(changed)
        return

    print(
        f"[CONFIG] API documentation generation: {'Disabled' if args.no_api_doc else 'Enabled'}"
    )
    branches = args.branches if args.branches is not None else ["main"]
    print(f"[CONFIG] Build branches: {branches}")
    print(f"[CONFIG] Languages: {args.languages}")

    WORKTREES_DIR.mkdir(exist_ok=True)

    # Get version list
    versions = list(branches)  # Start with branches specified from command line
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
    changed = False

    # Build all specified branches
    for branch in branches:
        print(f"[BUILD] Building branch: {branch}")
        changed |= bool(build_one(branch, branch, versions, enable_api_doc, args.languages))

    # Build all tags (if any)
    for tag in tags_to_build:
        print(f"[BUILD] Building tag: {tag}")
        changed |= bool(build_one(tag, tag, versions, enable_api_doc, args.languages))

    report_cache_changed(changed)


def emit_versions_json():
    """Write the full version list to build/versions.json for the runtime
    version switcher: branches (default ['main']) first, then all valid tags
    sorted by version descending."""
    tags = get_tags()
    tags.sort(key=pv.parse, reverse=True)
    versions = ["main"] + tags
    out = SITE_DIR / "versions.json"
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"versions": versions}, indent=2), encoding="utf-8")
    print(f"[WRITE] {out}: {versions}")


if __name__ == "__main__":
    main()
