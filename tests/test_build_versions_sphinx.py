"""用临时 Git 仓库和轻量 autodoc 验证真实 Sphinx 缓存，不导入项目依赖。"""

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "docs/sphinx_doc/build_versions.py"
DOCS = Path("docs/sphinx_doc/source")


@unittest.skipUnless(importlib.util.find_spec("sphinx"), "需要安装 Sphinx 才运行真实构建测试")
class SphinxCacheTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sphinx-cache-smoke-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.cache = self.base / "cache"
        self.events = self.base / "source-reads.jsonl"
        self.commands = []
        self.builds = []
        self.logs = io.StringIO()
        spec = importlib.util.spec_from_file_location("sphinx_cache_builder", SCRIPT)
        self.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.builder)
        self.site = self.repo / "docs/sphinx_doc/build"
        self.out = self.site / "en/main"
        for mocked in (
            # 不继承凭据或用户 Git 配置；身份仅由每次 commit 的局部参数提供。
            patch.dict(os.environ, {
                "PATH": os.defpath,
                "HOME": str(self.base),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "LC_ALL": "C.UTF-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "NO_COLOR": "1",
                "SPHINX_CACHE_DIR": str(self.cache),
                "SPHINX_CACHE_CONTEXT": "real-sphinx-smoke",
                "SMOKE_READ_EVENTS": str(self.events),
            }, clear=True),
            patch.object(self.builder, "REPO_ROOT", self.repo),
            patch.object(self.builder, "SITE_DIR", self.site),
            patch.object(self.builder, "WORKTREES_DIR", self.repo / ".worktrees"),
            patch.object(self.builder, "PACKAGE_DIR", "smoke_api"),
            patch.object(self.builder, "run", side_effect=self.run_command),
        ):
            mocked.start()
            self.addCleanup(mocked.stop)
        self.git("init", "-b", "main")
        self.write(self.repo, DOCS / "conf.py", textwrap.dedent('''\
            import json
            import os
            import sys
            from pathlib import Path

            sys.path.insert(0, os.environ["REPO_ROOT"])
            project = "Cache smoke"
            extensions = ["sphinx.ext.autodoc"]
            html_theme = "alabaster"
            html_title = "versions-" + os.environ["AVAILABLE_VERSIONS"]
            root_doc = "index"
            exclude_patterns = []

            def record_source(app, docname, source):
                # 记录真正触发解析的文档；并行 worker 每次只追加一条短记录。
                with open(os.environ["SMOKE_READ_EVENTS"], "a", encoding="utf-8") as stream:
                    stream.write(json.dumps(docname) + "\\n")

            def setup(app):
                app.connect("source-read", record_source)
                return {"parallel_read_safe": True, "parallel_write_safe": True}
            '''))
        self.write(self.repo, DOCS / "extra_assets.yaml", "assets: []\n")
        self.write(self.repo, DOCS / "index.rst", self.index())
        self.write(self.repo, DOCS / "guide.rst", "Guide\n=====\n\nORIGINAL_GUIDE_MARKER\n")
        self.write(self.repo, DOCS / "obsolete.rst", "Obsolete\n========\n\nOBSOLETE_PAGE_MARKER\n")
        for number in range(5):
            self.write(self.repo, DOCS / f"stable{number}.rst", f"Stable {number}\n========\n\nUnchanged page.\n")
        self.write(self.repo, "smoke_api/__init__.py", '"""轻量测试包。"""\n')
        self.write(self.repo, "smoke_api/module.py", self.module("ORIGINAL_API_MARKER"))
        self.initial = self.commit(self.repo)
        # 构建模板保持稳定；通过独立 worktree 推进 main，模拟目标版本的变更。
        self.git("checkout", "--detach", self.initial)

    @staticmethod
    def write(root, name, content):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    @staticmethod
    def index(obsolete=True):
        entries = ["guide", *(f"stable{n}" for n in range(5)), "api/modules"]
        if obsolete:
            entries.append("obsolete")
        return "Home\n====\n\n.. toctree::\n   :maxdepth: 2\n\n" + "".join(f"   {name}\n" for name in entries)

    @staticmethod
    def module(marker):
        return f'def example():\n    """{marker}"""\n    return 1\n'

    def git(self, *args, cwd=None, check=True):
        result = subprocess.run(
            ["git", *args], cwd=cwd or self.repo, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        if check:
            self.assertEqual(result.returncode, 0, result.stdout)
        return result.stdout.strip()

    def commit(self, root):
        self.git("add", "--all", cwd=root)
        self.git("-c", "user.name=Cache Smoke", "-c", "user.email=cache-smoke@example.invalid",
                 "commit", "-m", "fixture", cwd=root)
        return self.git("rev-parse", "HEAD", cwd=root)

    def advance_main(self, changes, deleted=()):
        writer = self.base / "writer"
        self.git("worktree", "add", str(writer), "main")
        try:
            for name, content in changes.items():
                self.write(writer, name, content)
            for name in deleted:
                (writer / name).unlink()
            return self.commit(writer)
        finally:
            self.git("worktree", "remove", "--force", str(writer))

    def run_command(self, cmd, cwd=None, env=None, check=True):
        self.commands.append(list(cmd))
        actual = list(map(str, cmd))
        if cmd[0] in {"sphinx-build", "sphinx-apidoc"}:
            # 使用当前解释器的真实 Sphinx，避免误用 PATH 中其他环境的可执行文件。
            module = "sphinx.cmd.build" if cmd[0] == "sphinx-build" else "sphinx.ext.apidoc"
            actual = [sys.executable, "-m", module, *actual[1:]]
            if cmd[0] == "sphinx-build":
                actual.extend(["-W", "--keep-going"])
        result = subprocess.run(
            actual, cwd=cwd or self.repo, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        if cmd[0] == "sphinx-build":
            self.builds.append(result)
        if check and result.returncode:
            print(result.stdout)
            result.check_returncode()

    def build(self, versions=("main",)):
        self.events.unlink(missing_ok=True)
        self.commands.clear()
        before = len(self.builds)
        with patch("sys.stdout", self.logs):
            changed = self.builder.build_one("main", "main", list(versions), langs=["en"])
        reads = [json.loads(line) for line in self.events.read_text().splitlines()] if self.events.exists() else []
        self.assertEqual(len(self.builds) - before, int(changed), self.logs.getvalue())
        if changed:
            self.assertEqual(self.builds[-1].returncode, 0, self.builds[-1].stdout)
            self.assertNotIn("WARNING:", self.builds[-1].stdout)
            self.assertTrue(any(cmd[0] == "sphinx-apidoc" for cmd in self.commands))
        else:
            self.assertEqual(self.commands, [], "缓存命中不应调用 Sphinx、apidoc 或 worktree")
        self.assertEqual(len(reads), len(set(reads)), reads)
        self.assertFalse(list((self.repo / ".worktrees").iterdir()))
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)
        return changed, set(reads)

    def state(self):
        entry = self.cache / f"schema-{self.builder.CACHE_SCHEMA}" / self.builder.digest(["main", "en"])
        return json.loads((entry / self.builder.CACHE_RECORD).read_text()), entry

    def html(self, name):
        return (self.out / name).read_text(encoding="utf-8")

    def assert_reused(self):
        # HTML 配置变化时，Sphinx 会在加载成功提示之间插入配置差异日志。
        self.assertRegex(self.builds[-1].stdout, r"loading pickled environment\.\.\.(?:[^\n]*\n)?\s*done")
        self.assertNotIn("复用失败", self.logs.getvalue())

    def test_real_worktree_hit_incremental_sources_api_dependencies_and_deletion(self):
        changed, cold_reads = self.build()
        self.assertTrue(changed)
        self.assertEqual(len(cold_reads), 11)
        first, _ = self.state()
        self.assertIn("ORIGINAL_GUIDE_MARKER", self.html("guide.html"))
        self.assertIn("ORIGINAL_API_MARKER", self.html("api/smoke_api.module.html"))
        cached_html = self.builder.content_hashes(self.builder.file_snapshot(self.out))
        shutil.rmtree(self.out)
        self.assertEqual(self.build(), (False, set()))
        self.assertEqual(self.builder.content_hashes(self.builder.file_snapshot(self.out)), cached_html)
        self.assertEqual(self.state()[0], first)
        self.assertFalse(list(self.out.rglob(".buildinfo")))
        self.assertFalse(list(self.out.rglob(".doctrees")))

        guide = DOCS / "guide.rst"
        next_commit = self.advance_main({guide: "Guide\n=====\n\nUPDATED_GUIDE_MARKER\n"})
        self.assertNotEqual(next_commit, self.initial)
        self.assertEqual(self.build(), (True, {"guide"}))
        self.assert_reused()
        second, _ = self.state()
        self.assertEqual(second["compatibility"], first["compatibility"])
        self.assertNotEqual(second["fingerprint"], first["fingerprint"])
        for name, old in first["snapshot"].items():
            if name == guide.as_posix():
                self.assertNotEqual(second["snapshot"][name]["hash"], old["hash"])
                self.assertGreater(second["snapshot"][name]["mtime"], old["mtime"])
            else:
                self.assertEqual(second["snapshot"][name], old, name)
        self.assertIn("UPDATED_GUIDE_MARKER", self.html("guide.html"))
        self.assertNotIn("ORIGINAL_GUIDE_MARKER", self.html("guide.html"))
        self.assertEqual(self.build(), (False, set()))

        self.advance_main({"smoke_api/module.py": self.module("UPDATED_API_MARKER")})
        self.assertEqual(self.build(), (True, {"api/smoke_api.module"}))
        self.assert_reused()
        third, _ = self.state()
        rst = (DOCS / "api/smoke_api.module.rst").as_posix()
        self.assertEqual(third["snapshot"][rst], second["snapshot"][rst])
        self.assertGreater(third["snapshot"]["smoke_api/module.py"]["mtime"],
                           second["snapshot"]["smoke_api/module.py"]["mtime"])
        self.assertIn("UPDATED_API_MARKER", self.html("api/smoke_api.module.html"))
        self.assertNotIn("ORIGINAL_API_MARKER", self.html("api/smoke_api.module.html"))

        self.advance_main({DOCS / "index.rst": self.index(obsolete=False)}, deleted=[DOCS / "obsolete.rst"])
        self.assertEqual(self.build(), (True, {"index"}))
        self.assert_reused()
        state, entry = self.state()
        self.assertNotIn((DOCS / "obsolete.rst").as_posix(), state["snapshot"])
        for root in (self.out, entry / "html"):
            self.assertFalse((root / "obsolete.html").exists())
            self.assertFalse((root / "_sources/obsolete.rst.txt").exists())
            self.assertNotIn("obsolete", (root / "searchindex.js").read_text())
        self.assertNotIn("obsolete.html", self.html("index.html"))
        self.assertEqual(self.build(), (False, set()))
        self.assertFalse((self.out / "obsolete.html").exists())

    def test_version_list_round_trip_rewrites_html_without_reading_sources(self):
        self.assertTrue(self.build()[0])
        previous, _ = self.state()
        for versions in (("main", "testtag"), ("main",)):
            with self.subTest(versions=versions):
                self.assertEqual(self.build(versions), (True, set()))
                self.assert_reused()
                current, _ = self.state()
                self.assertEqual(current["compatibility"], previous["compatibility"])
                self.assertNotEqual(current["fingerprint"], previous["fingerprint"])
                self.assertEqual(current["snapshot"], previous["snapshot"])
                self.assertIn("versions-" + ",".join(versions), self.html("index.html"))
                if len(versions) == 1:
                    self.assertNotIn("testtag", self.html("index.html"))
                self.assertEqual(self.build(versions), (False, set()))
                previous = current

    def test_remote_only_main_uses_full_remote_ref_not_ambiguous_tag_or_head(self):
        remote_commit = self.advance_main({DOCS / "guide.rst": "Guide\n=====\n\nREMOTE_MAIN_MARKER\n"})
        self.git("update-ref", "refs/remotes/upstream/main", remote_commit)
        # 同名短 ref 的 tag 指向旧提交，精确远端 ref 必须绕过该歧义。
        self.git("tag", "upstream/main", self.initial)
        self.git("branch", "-D", "main")
        self.assertNotEqual(self.git("rev-parse", "HEAD"), remote_commit)
        result = subprocess.run(["git", "rev-parse", "--verify", "main^{commit}"], cwd=self.repo,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode, 0)
        with patch.object(self.builder, "REMOTE", "upstream"):
            self.assertTrue(self.build()[0])
            worktree = next(cmd for cmd in self.commands if cmd[:3] == ["git", "worktree", "add"])
            self.assertEqual(worktree[-1], remote_commit)
            self.assertIn("REMOTE_MAIN_MARKER", self.html("guide.html"))
            self.assertNotIn("ORIGINAL_GUIDE_MARKER", self.html("guide.html"))
            self.assertEqual(self.build(), (False, set()))
            # 显式的无效本地 ref 不得退回远端、同名 tag 或 HEAD。
            for ref in ("refs/heads/main", "refs/heads/upstream/main", "missing-branch"):
                with self.subTest(ref=ref), self.assertRaises(subprocess.CalledProcessError):
                    self.builder.build_one(ref, "invalid", ["invalid"], langs=["en"])
                self.assertFalse((self.site / "en/invalid").exists())
            self.git("update-ref", "-d", "refs/remotes/upstream/main")
            before = len(self.builds)
            with self.assertRaises(subprocess.CalledProcessError):
                self.build()
            self.assertEqual(len(self.builds), before)
            self.assertEqual(self.commands, [])


if __name__ == "__main__":
    unittest.main()
