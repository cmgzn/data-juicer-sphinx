"""使用小文件和命令替身验证缓存动作，不依赖 Sphinx 或项目运行时。"""

import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "docs/sphinx_doc/build_versions.py"


class CacheTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.repo = self.base / "template"
        self.target = self.base / "target"
        self.cache = self.base / "cache"
        self.site = self.repo / "docs/sphinx_doc/build"
        self.output = self.base / "github-output"
        spec = importlib.util.spec_from_file_location("cache_builder", SCRIPT)
        self.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.builder)
        self.commands = []
        self.builds = []
        self.failures = 0
        self.commit = "a" * 40
        self.logs = io.StringIO()
        self.write(self.repo, "docs/sphinx_doc/source/conf.py", "template configuration")
        self.write(self.repo, "docs/sphinx_doc/source/index.rst", "template index")
        self.write(self.repo, "docs/sphinx_doc/_templates/module.rst_t", "api template")
        self.write(self.target, "docs/sphinx_doc/source/index.rst", "historical index")
        self.write(self.target, "docs/sphinx_doc/source/index_ZH.rst", "历史首页")
        self.write(self.target, "docs/sphinx_doc/source/old.rst", "old page")
        self.write(self.target, "data_juicer/module.py", '"""API documentation"""')
        self.write(self.target, "helper.py", "dependency = 1")
        self.write(self.target, "guides/guide.md", "collected document")
        for mocked in (
            patch("sys.stdout", self.logs),
            patch.dict(
                os.environ,
                {
                    "SPHINX_CACHE_DIR": str(self.cache),
                    "SPHINX_CACHE_CONTEXT": "context-v1",
                    "GITHUB_OUTPUT": str(self.output),
                },
                clear=True,
            ),
            patch.object(self.builder, "REPO_ROOT", self.repo),
            patch.object(self.builder, "SITE_DIR", self.site),
            patch.object(self.builder, "WORKTREES_DIR", self.repo / ".worktrees"),
            patch.object(self.builder, "run", side_effect=self.run_command),
            patch.object(self.builder.subprocess, "check_output", side_effect=self.git_output),
            patch.object(self.builder, "load_extra_assets_config", return_value={"assets": []}),
        ):
            mocked.start()
            self.addCleanup(mocked.stop)

    def write(self, root, name, content):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def git_output(self, cmd, **kwargs):
        self.commands.append(cmd)
        if cmd == ["git", "tag"]:
            return "v1.0.0\nv2.0.0\nv99.0.0\nbad-tag\n"
        if cmd[-1].endswith("^{tree}"):
            files = [
                (str(p.relative_to(self.target)), p.read_bytes().hex())
                for p in sorted(self.target.rglob("*"))
                if p.is_file()
            ]
            return hashlib.sha256(repr(files).encode()).hexdigest()
        return self.commit

    def run_command(self, cmd, cwd=None, env=None, check=True):
        self.commands.append(cmd)
        if cmd[:3] == ["git", "worktree", "add"]:
            shutil.copytree(self.target, Path(cmd[-2]), symlinks=True)
        elif cmd[:3] == ["git", "worktree", "remove"]:
            shutil.rmtree(cmd[-1])
        elif cmd[0] == "sphinx-apidoc":
            package = Path(cmd[3])
            content = "\n".join(p.read_text() for p in sorted(package.rglob("*.py")))
            self.write(Path(cmd[2]), "module.rst", content)
        elif cmd[0] == "sphinx-build":
            source, out = map(Path, cmd[-2:])
            doctrees = Path(cmd[cmd.index("-d") + 1]) if "-d" in cmd else out / ".doctrees"
            snapshot = self.builder.file_snapshot(Path(env["REPO_ROOT"]), self.builder.INPUT_IGNORES)
            self.builds.append(
                {
                    "env": env,
                    "snapshot": snapshot,
                    "reuse": (doctrees / "environment.pickle").exists(),
                    "cmd": cmd,
                    "source": source,
                }
            )
            if self.failures:
                self.failures -= 1
                self.write(doctrees, "partial", "failed state")
                self.write(out, "partial.html", "failed output")
                raise subprocess.CalledProcessError(1, cmd)
            for path in source.rglob("*"):
                if path.suffix in {".rst", ".md"}:
                    self.write(out, str(path.relative_to(source).with_suffix(".html")), path.read_text())
            self.write(out, ".buildinfo", "build configuration")
            self.write(doctrees, "environment.pickle", "opaque doctree, never unpickled by script")
            self.write(doctrees, "index.doctree", "opaque tree")

    def build(self, **kwargs):
        return self.builder.build_one("main", "main", ["main"], **kwargs)

    def states(self):
        return sorted(self.cache.glob(f"schema-*/*/{self.builder.CACHE_RECORD}"))

    def cli(self, *args):
        with patch.object(sys, "argv", [str(SCRIPT), *args]):
            self.builder.main()

    def test_cold_then_hot_skips_every_build_command_and_pins_commit(self):
        self.cli()
        self.assertEqual(len(self.builds), 2)
        self.assertTrue(all("-d" in b["cmd"] and "-a" in b["cmd"] for b in self.builds))
        worktree_cmd = next(c for c in self.commands if c[:3] == ["git", "worktree", "add"])
        self.assertEqual(worktree_cmd[-1], self.commit)
        self.assertIn("--detach", worktree_cmd)
        self.assertEqual((self.site / "en/main/index.html").read_text(), "historical index")
        self.assertEqual(self.output.read_text(), "cache_changed=true\n")
        shutil.rmtree(self.site)
        self.commands.clear()
        self.cli()
        self.assertEqual(len(self.builds), 2)
        self.assertFalse(any(c[0].startswith("sphinx") or c[:2] == ["git", "worktree"] for c in self.commands))
        self.assertEqual((self.site / "en/main/api/module.html").read_text(), '"""API documentation"""')
        self.assertEqual(self.output.read_text(), "cache_changed=true\ncache_changed=false\n")
        self.assertFalse(list(self.site.rglob(".buildinfo")))
        self.assertFalse(list(self.site.rglob(".doctrees")))
        self.assertIn("[cache] hit/skip main/en", self.logs.getvalue())
        self.assertIn("[cache] build main/zh_CN", self.logs.getvalue())
        self.assertIn("fingerprint=", self.logs.getvalue())

    def test_noenv_keeps_upstream_api_switch_and_current_path(self):
        os.environ.pop("SPHINX_CACHE_DIR")
        self.build(enable_api_doc=False)
        self.assertFalse(any(c[0] == "sphinx-apidoc" for c in self.commands))
        self.assertTrue(all("-d" not in b["cmd"] for b in self.builds))
        self.assertTrue((self.site / "en/main/.doctrees/environment.pickle").exists())
        self.assertFalse(self.cache.exists())
        self.commands.clear()
        self.builder.build_one("main", "preview", ["preview"], langs=["en"], use_worktree=False)
        self.assertTrue(any(c[0] == "sphinx-apidoc" for c in self.commands))
        self.assertFalse(any(c[:2] == ["git", "worktree"] for c in self.commands))
        self.assertEqual(self.builds[-1]["env"]["DOCS_VERSION"], "preview")
        self.assertEqual((self.site / "en/preview/index.html").read_text(), "template index")

    def test_source_api_and_dependency_changes_invalidate_but_reuse_doctrees(self):
        self.build()
        for path, content in (
            ("data_juicer/module.py", '"""changed API"""'),
            ("helper.py", "dependency = 2"),
            ("guides/guide.md", "changed guide"),
        ):
            with self.subTest(path=path):
                self.write(self.target, path, content)
                self.assertTrue(self.build())
                self.assertTrue(all(b["reuse"] for b in self.builds[-2:]))
        self.assertEqual((self.site / "en/main/api/module.html").read_text(), '"""changed API"""')
        self.assertEqual((self.site / "en/main/guides/guide.html").read_text(), "changed guide")

    def test_template_context_rendering_and_api_mode_force_cold(self):
        self.build()
        for key, value in (
            ("SPHINX_CACHE_CONTEXT", "context-v2"),
            ("REPO_OWNER", "another-owner"),
            ("HTML_BASEURL", "https://example.org/docs/"),
            ("PROJECT", "other-project"),
        ):
            with self.subTest(key=key):
                os.environ[key] = value
                self.assertTrue(self.build())
                self.assertFalse(any(b["reuse"] for b in self.builds[-2:]))
        for name in (
            "docs/sphinx_doc/source/conf.py",
            "docs/sphinx_doc/_templates/module.rst_t",
            "data_juicer_sphinx_theme/layout.html",
            "scripts/helper.py",
        ):
            with self.subTest(name=name):
                self.write(self.repo, name, "changed template")
                self.assertTrue(self.build())
                self.assertFalse(any(b["reuse"] for b in self.builds[-2:]))
        self.assertTrue(self.builder.build_one("main", "main", ["main", "v1.0.0"]))
        self.assertTrue(all(b["reuse"] for b in self.builds[-2:]))
        self.commands.clear()
        self.assertTrue(self.builder.build_one("main", "main", ["main", "v1.0.0"], enable_api_doc=False))
        self.assertFalse(any(c[0] == "sphinx-apidoc" for c in self.commands))
        self.assertFalse((self.site / "en/main/api/module.html").exists())

    def check_version_list_change(self, before, after):
        self.assertTrue(self.builder.build_one("main", "main", before))
        previous = {path: json.loads(path.read_text()) for path in self.states()}
        self.commands.clear()
        self.assertTrue(self.builder.build_one("main", "main", after))
        self.assertEqual(len(self.builds), 4)
        self.assertTrue(all(b["reuse"] and "-a" in b["cmd"] for b in self.builds[-2:]))
        self.assertEqual([b["env"]["AVAILABLE_VERSIONS"] for b in self.builds[-2:]], [",".join(after)] * 2)
        for path, old in previous.items():
            state = json.loads(path.read_text())
            self.assertEqual(state["compatibility"], old["compatibility"])
            self.assertNotEqual(state["fingerprint"], old["fingerprint"])
            self.assertEqual(state["snapshot"], old["snapshot"])
        self.commands.clear()
        self.assertFalse(self.builder.build_one("main", "main", after))
        self.assertFalse(any(c[0].startswith("sphinx") or c[:2] == ["git", "worktree"] for c in self.commands))

    def test_adding_available_version_rewrites_html_but_reuses_doctrees(self):
        self.check_version_list_change(["main"], ["main", "testtag"])

    def test_removing_available_version_rewrites_html_but_reuses_doctrees(self):
        self.check_version_list_change(["main", "testtag"], ["main"])

    def test_remote_only_main_resolves_exact_configured_remote_commit(self):
        remote_commit = "b" * 40
        resolutions = []

        def resolve(cmd, **kwargs):
            if cmd[:3] == ["git", "rev-parse", "--verify"]:
                resolutions.append((cmd[-1], kwargs.get("cwd")))
                if cmd[-1] == "main^{commit}":
                    raise subprocess.CalledProcessError(128, cmd)
                if cmd[-1] == "refs/remotes/upstream/main^{commit}":
                    return remote_commit
                self.fail(f"不应解析其他 ref: {cmd}")
            return self.git_output(cmd, **kwargs)

        with (
            patch.object(self.builder, "REMOTE", "upstream"),
            patch.object(self.builder.subprocess, "check_output", side_effect=resolve),
        ):
            self.assertTrue(self.build(langs=["en"]))
            worktree = next(c for c in self.commands if c[:3] == ["git", "worktree", "add"])
            self.assertEqual(worktree[-1], remote_commit)
            self.assertIn(["git", "rev-parse", f"{remote_commit}^{{tree}}"], self.commands)
            self.assertEqual(self.builds[-1]["env"]["GIT_REF_FOR_LINKS"], "main")
            self.assertFalse(self.build(langs=["en"]))
        self.assertEqual(resolutions, [
            ("main^{commit}", self.repo),
            ("refs/remotes/upstream/main^{commit}", self.repo),
        ] * 2)

    def test_local_main_does_not_attempt_remote_fallback(self):
        self.build(langs=["en"])
        self.assertEqual(
            [c[-1] for c in self.commands if c[:3] == ["git", "rev-parse", "--verify"]],
            ["main^{commit}"],
        )

    def test_missing_main_and_remote_do_not_fall_back_to_tag_or_head(self):
        attempted = []

        def resolve(cmd, **kwargs):
            attempted.append(cmd[-1])
            if cmd[-1] in {"main^{commit}", "refs/remotes/origin/main^{commit}"}:
                raise subprocess.CalledProcessError(128, cmd)
            self.fail(f"不能用 tag 或 HEAD 掩盖解析失败: {cmd}")

        with patch.object(self.builder.subprocess, "check_output", side_effect=resolve):
            with self.assertRaises(subprocess.CalledProcessError):
                self.build(langs=["en"])
        self.assertEqual(attempted, ["main^{commit}", "refs/remotes/origin/main^{commit}"])
        self.assertEqual(self.builds, [])
        self.assertFalse(self.cache.exists())

    def test_invalid_refs_and_current_checkout_never_use_main_fallback(self):
        for ref, use_worktree in (
            ("refs/heads/main", True),
            ("origin/main", True),
            ("missing-branch", True),
            ("v99.0.0", True),
            ("HEAD", True),
            ("main", False),
        ):
            with self.subTest(ref=ref, use_worktree=use_worktree):
                cmd = ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"]
                with patch.object(
                    self.builder.subprocess, "check_output", side_effect=subprocess.CalledProcessError(128, cmd)
                ) as resolve:
                    with self.assertRaises(subprocess.CalledProcessError):
                        self.builder.build_one(ref, "preview", ["preview"], langs=["en"], use_worktree=use_worktree)
                resolve.assert_called_once_with(cmd, cwd=self.repo, text=True)
        self.assertEqual(self.builds, [])
        self.assertFalse(self.cache.exists())

    def test_ignored_build_and_pycache_files_do_not_invalidate(self):
        self.build()
        for name in ("build/noise.html", "cache/noise", "source/__pycache__/conf.pyc"):
            self.write(self.repo / "docs/sphinx_doc", name, "noise")
        self.assertFalse(self.build())

    def test_mtimes_are_content_based_and_deleted_files_stay_deleted(self):
        same = self.write(self.base, "snapshot/same.py", "same")
        changed = self.write(self.base, "snapshot/changed.py", "before")
        removed = self.write(self.base, "snapshot/removed.py", "removed")
        root = self.base / "snapshot"
        for path in (same, changed, removed):
            os.utime(path, ns=(1000000000, 1000000000))
        snapshot = self.builder.file_snapshot(root, self.builder.INPUT_IGNORES)
        changed.write_text("after")
        removed.unlink()
        for path in (same, changed):
            os.utime(path, ns=(2000000000, 2000000000))
        self.builder.restore_mtimes(root, snapshot)
        self.assertEqual(same.stat().st_mtime_ns, 1000000000)
        self.assertGreaterEqual(changed.stat().st_mtime_ns, 2000000000)
        self.assertNotEqual(changed.stat().st_mtime_ns, snapshot["changed.py"]["mtime"])
        self.assertFalse(removed.exists())
        changed.write_text("changed again")
        os.utime(changed, ns=(1000000000, 1000000000))
        self.builder.restore_mtimes(root, snapshot)
        self.assertGreater(changed.stat().st_mtime_ns, 1000000000)

    def test_language_snapshots_are_not_overwritten_and_deleted_html_is_removed(self):
        self.build()
        expected = {}
        for number, path in enumerate(self.states(), start=1):
            state = json.loads(path.read_text())
            stamp = number * 1000000000
            state["snapshot"]["helper.py"]["mtime"] = stamp
            path.write_text(json.dumps(state))
            expected[path.parent.name] = stamp
        (self.target / "docs/sphinx_doc/source/old.rst").unlink()
        self.build()
        for build in self.builds[-2:]:
            lang = build["cmd"][build["cmd"].index("-D") + 1].split("=")[1]
            key = self.builder.digest(["main", lang])
            self.assertEqual(build["snapshot"]["helper.py"]["mtime"], expected[key])
            self.assertFalse((self.site / lang / "main/old.html").exists())
        for path in self.states():
            self.assertEqual(json.loads(path.read_text())["snapshot"]["helper.py"]["mtime"], expected[path.parent.name])

    def test_missing_corrupt_or_extra_cache_files_force_cold(self):
        self.build()
        for damage in ("missing", "html", "buildinfo", "doctree", "extra", "json", "schema", "snapshot"):
            with self.subTest(damage=damage):
                entry = self.states()[0].parent
                if damage == "missing":
                    (entry / "html/index.html").unlink()
                elif damage == "html":
                    (entry / "html/index.html").write_text("corrupt")
                elif damage == "buildinfo":
                    (entry / "html/.buildinfo").write_text("corrupt")
                elif damage == "doctree":
                    (entry / "doctrees/index.doctree").write_text("corrupt")
                elif damage == "extra":
                    (entry / "html/unknown.html").write_text("extra")
                elif damage == "json":
                    (entry / self.builder.CACHE_RECORD).write_text("not json")
                else:
                    state = json.loads((entry / self.builder.CACHE_RECORD).read_text())
                    state[damage] = -1 if damage == "schema" else []
                    (entry / self.builder.CACHE_RECORD).write_text(json.dumps(state))
                before = len(self.builds)
                self.assertTrue(self.build())
                self.assertEqual(len(self.builds), before + 1)
                self.assertFalse(self.builds[-1]["reuse"])

    def test_full_clears_only_selected_entries_and_never_skips(self):
        self.builder.build_one("v1.0.0", "v1.0.0", ["v1.0.0"])
        historical = {str(p): p.read_bytes() for p in self.cache.rglob("*") if p.is_file()}
        self.build()
        os.environ["SPHINX_CACHE_FORCE"] = "1"
        self.assertTrue(self.build())
        self.assertFalse(any(b["reuse"] for b in self.builds[-2:]))
        for name, content in historical.items():
            self.assertEqual(Path(name).read_bytes(), content)

    def test_reuse_failure_retries_once_cold_and_cold_failure_has_no_success_state(self):
        self.build(langs=["en"])
        self.write(self.target, "helper.py", "changed = 1")
        self.failures = 1
        self.assertTrue(self.build(langs=["en"]))
        self.assertEqual([b["reuse"] for b in self.builds[-2:]], [True, False])
        self.assertFalse(list(self.cache.rglob("partial")))
        self.write(self.target, "helper.py", "changed = 2")
        self.failures = 2
        before = len(self.builds)
        with self.assertRaises(subprocess.CalledProcessError):
            self.cli("-l", "en")
        self.assertEqual(len(self.builds), before + 2)
        self.assertEqual(self.states(), [])
        self.assertFalse(self.output.exists())
        self.assertFalse((self.site / "en/main").exists())
        self.failures = 1
        before = len(self.builds)
        with self.assertRaises(subprocess.CalledProcessError):
            self.build(langs=["en"])
        self.assertEqual(len(self.builds), before + 1)
        self.assertEqual(self.states(), [])

    def test_tag_selection_does_not_build_other_tags_or_main(self):
        self.cli("--branches", "--tags", "v2.0.0", "not-a-tag", "-A")
        self.assertEqual([b["env"]["DOCS_VERSION"] for b in self.builds], ["v2.0.0", "v2.0.0"])
        self.assertFalse((self.site / "en/main").exists())
        self.assertFalse((self.site / "en/v1.0.0").exists())
        self.assertEqual(self.output.read_text(), "cache_changed=true\n")

    def test_path_changes_force_cold_and_traversal_is_rejected(self):
        self.build()
        with patch.object(self.builder, "SITE_DIR", self.base / "new-site"):
            self.assertTrue(self.build())
            self.assertFalse(any(b["reuse"] for b in self.builds[-2:]))
        for label in ("../outside", "/absolute", "a/../../b"):
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.builder.build_one("main", label, [label])
        for directory in ("relative", str(self.repo / "docs/sphinx_doc/cache")):
            with patch.dict(os.environ, {"SPHINX_CACHE_DIR": directory}), self.assertRaises(ValueError):
                self.build()

    def test_current_caches_generated_sources_and_detects_uncommitted_python_edits(self):
        self.write(self.repo, "data_juicer/module.py", '"""current API"""')
        self.write(self.repo, "guides/local.md", "local guide")
        self.cli("--current", "preview", "-l", "en")
        self.commands.clear()
        self.cli("--current", "preview", "-l", "en")
        self.assertEqual(len(self.builds), 1)
        self.assertFalse(any(c[:2] == ["git", "worktree"] or c[0].startswith("sphinx") for c in self.commands))
        self.assertEqual((self.site / "en/preview/guides/local.html").read_text(), "local guide")
        self.write(self.repo, "data_juicer/module.py", '"""edited current API"""')
        self.cli("--current", "preview", "-l", "en")
        self.assertEqual(len(self.builds), 2)
        self.assertEqual((self.site / "en/preview/api/module.html").read_text(), '"""edited current API"""')

    def test_file_instead_of_cache_entry_is_cold_and_mtime_only_change_is_hot(self):
        self.build(langs=["en"])
        entry = self.states()[0].parent
        shutil.rmtree(entry)
        entry.write_text("damaged entry")
        self.assertTrue(self.build(langs=["en"]))
        self.assertFalse(self.builds[-1]["reuse"])
        path = self.repo / "docs/sphinx_doc/source/conf.py"
        path.touch()
        self.assertFalse(self.build(langs=["en"]))

    def test_metadata_atomic_write_failure_cannot_mark_success(self):
        with patch.object(self.builder.os, "replace", side_effect=OSError("atomic write failed")):
            with self.assertRaises(OSError):
                self.cli("-l", "en")
        self.assertFalse(self.output.exists())
        self.assertEqual(self.states(), [])
        self.assertFalse(list(self.cache.rglob("tmp*")))

    def test_apidoc_failure_invalidates_old_state_without_cold_sphinx_retry(self):
        self.build(langs=["en"])
        self.write(self.target, "helper.py", "changed dependency")
        original = self.run_command

        def fail_apidoc(cmd, **kwargs):
            if cmd[0] == "sphinx-apidoc":
                raise subprocess.CalledProcessError(1, cmd)
            return original(cmd, **kwargs)

        before = len(self.builds)
        with (
            patch.object(self.builder, "run", side_effect=fail_apidoc),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            self.cli("-l", "en")
        self.assertEqual(self.states(), [])
        self.assertEqual(len(self.builds), before)
        self.assertFalse(self.output.exists())
        self.assertFalse((self.site / "en/main").exists())

    def test_cache_symlink_is_discarded_without_reading_or_touching_its_target(self):
        self.build(langs=["en"])
        outside = self.write(self.base, "outside/secret", "untouched")
        html = self.states()[0].parent / "html/index.html"
        html.unlink()
        html.symlink_to(outside)
        self.assertTrue(self.build(langs=["en"]))
        self.assertFalse(self.builds[-1]["reuse"])
        self.assertEqual(outside.read_text(), "untouched")
        self.assertFalse(html.is_symlink())

    def test_worktree_symlink_is_rejected_before_overlay_and_sphinx(self):
        outside = self.write(self.base, "outside/secret.md", "untouched")
        (self.target / "docs/sphinx_doc/source/escape.md").symlink_to(outside)
        with self.assertRaises(ValueError):
            self.build(langs=["en"])
        self.assertEqual(self.builds, [])
        self.assertEqual(self.states(), [])
        self.assertEqual(outside.read_text(), "untouched")

    def site_version(self, root, ref, content="site", languages=("en", "zh_CN")):
        for lang in languages:
            self.write(root, f"{lang}/{ref}/{self.builder.entry_page(lang)}", f"{content}-{lang}")

    def test_site_replaces_whole_versions_and_preserves_latest_history_and_assets(self):
        previous, publish = self.base / "previous", self.base / "publish"
        self.site_version(previous, "main", "latest main, not cached main")
        self.site_version(previous, "v1.0.0", "old selected tag")
        self.site_version(previous, "v2.0.0", "latest history")
        self.site_version(previous, "v3.0.0", languages=("en",))
        self.site_version(previous, "not-a-tag")
        self.site_version(previous, "v0.1.0")
        self.write(previous, "en/v1.0.0/deleted.html", "must disappear")
        self.write(previous, "versions.json", '{"versions": ["main", "v99.0.0"]}')
        for name in ("manifest.json", "assets/manifest.json", "asset-manifest.json", "assets/logo.svg", ".nojekyll"):
            self.write(previous, name, f"retain {name}")
        preserved = {
            p.relative_to(previous): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in previous.rglob("*")
            if p.is_file() and "v1.0.0" not in p.parts and p.name != "versions.json"
        }
        self.site_version(self.site, "v1.0.0", "rebuilt")
        self.write(self.site, "index.html", "new redirect")
        self.write(self.site, "404.html", "new 404")
        self.write(publish, "orphan.html", "stale publish directory")
        self.commands.clear()
        with patch.object(self.builder, "MIN_TAG", "v1.0.0"):
            self.cli("--assemble-site", str(previous), str(publish))
        self.assertEqual(self.commands, [])
        self.assertFalse(self.output.exists())
        for relative, expected in preserved.items():
            self.assertEqual(hashlib.sha256((publish / relative).read_bytes()).hexdigest(), expected)
        self.assertFalse((publish / "en/v1.0.0/deleted.html").exists())
        self.assertFalse((publish / "orphan.html").exists())
        self.assertEqual((publish / "en/v1.0.0/index.html").read_text(), "rebuilt-en")
        self.assertEqual((publish / "index.html").read_text(), "new redirect")
        self.assertEqual((publish / "404.html").read_text(), "new 404")
        self.assertEqual(json.loads((publish / "versions.json").read_text())["versions"], ["main", "v2.0.0", "v1.0.0"])
        self.assertTrue((previous / "en/v1.0.0/deleted.html").exists())

    def test_assembly_strips_only_build_records_and_never_loads_pickle(self):
        previous, publish = self.base / "previous", self.base / "publish"
        self.site_version(previous, "main")
        self.site_version(self.site, "v1.0.0")
        for root in (previous, self.site):
            for name in (
                ".git/config",
                "en/main/.doctrees/environment.pickle",
                "en/main/.doctrees/.sphinx-cache-state.json",
                "zh_CN/main/.buildinfo",
                "en/main/.sphinx-cache-state.json",
            ):
                if root == self.site:
                    name = name.replace("main", "v1.0.0")
                self.write(root, name, "invalid JSON and pickle must not be read")
        with (
            patch("pickle.load", side_effect=AssertionError("不允许加载 pickle")),
            patch("pickle.loads", side_effect=AssertionError("不允许加载 pickle")),
        ):
            self.builder.assemble_site(previous, publish)
        for path in publish.rglob("*"):
            self.assertNotIn(path.name, self.builder.SITE_IGNORES)
        self.assertEqual(json.loads((publish / "versions.json").read_text())["versions"], ["main", "v1.0.0"])

    def test_bad_new_output_cannot_mix_with_old_language_or_replace_publish(self):
        previous, publish = self.base / "previous", self.base / "publish"
        self.site_version(previous, "main", "old")
        self.site_version(self.site, "main", "new", languages=("en",))
        self.write(publish, "sentinel", "untouched")
        with self.assertRaisesRegex(ValueError, "双语入口"):
            self.builder.assemble_site(previous, publish)
        self.assertEqual((publish / "sentinel").read_text(), "untouched")
        self.write(self.site, "zh_CN/main/index.html", "wrong language entry")
        with self.assertRaisesRegex(ValueError, "双语入口"):
            self.builder.assemble_site(previous, publish)
        self.assertEqual(self.commands, [])

    def test_empty_previous_for_full_does_not_keep_orphans_or_ghost_main(self):
        previous, publish = self.base / "empty", self.base / "publish"
        previous.mkdir()
        self.site_version(publish, "v0.1.0")
        self.site_version(self.site, "v2.0.0")
        self.builder.assemble_site(previous, publish)
        self.assertFalse((publish / "en/v0.1.0").exists())
        self.assertEqual(json.loads((publish / "versions.json").read_text())["versions"], ["v2.0.0"])

    def test_site_rejects_file_directory_and_parent_symlinks_and_overlap(self):
        previous, publish = self.base / "previous", self.base / "publish"
        self.site_version(previous, "main")
        self.site_version(self.site, "main")
        secret = self.write(self.base, "outside/secret", "outside")
        for source in (previous, self.site):
            for target in (secret, secret.parent):
                link = source / "escape"
                link.symlink_to(target)
                with self.assertRaises(ValueError):
                    self.builder.assemble_site(previous, publish)
                link.unlink()
        link = self.base / "linked-parent"
        link.symlink_to(previous)
        with self.assertRaises(ValueError):
            self.builder.assemble_site(link, publish)
        for destination in (previous, self.site, previous / "nested", self.base):
            with self.assertRaises(ValueError):
                self.builder.assemble_site(previous, destination)
        self.assertEqual(secret.read_text(), "outside")

    def test_nested_branch_cache_is_isolated_and_assembly_replaces_only_that_ref(self):
        previous, publish = self.base / "previous", self.base / "publish"
        self.site_version(previous, "feature/sibling", "keep")
        self.site_version(previous, "feature/docs", "old")
        self.write(previous, "en/feature/docs/deleted.html", "old page")
        self.builder.build_one("feature/docs", "feature/docs", ["feature/docs"], enable_api_doc=False)
        for marker in self.site.rglob(self.builder.CACHE_RECORD):
            marker.unlink()
        self.builder.assemble_site(previous, publish)
        self.assertEqual((publish / "en/feature/sibling/index.html").read_text(), "keep-en")
        self.assertFalse((publish / "en/feature/docs/deleted.html").exists())
        self.assertEqual((publish / "en/feature/docs/index.html").read_text(), "historical index")
        self.assertEqual(len(self.states()), 2)
        self.assertFalse((self.cache / "feature").exists())


if __name__ == "__main__":
    unittest.main()
