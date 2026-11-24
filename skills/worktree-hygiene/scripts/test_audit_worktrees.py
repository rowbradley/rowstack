#!/usr/bin/env python3
"""Behavioral tests for audit_worktrees.py using disposable repositories."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("audit_worktrees.py")


def run(
    *args: str, cwd: Path | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if check and result.returncode:
        raise AssertionError(
            f"command failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run("git", "-C", str(repo), *args, check=check)


def initialize(repo: Path) -> None:
    repo.mkdir(parents=True)
    run("git", "init", "-b", "main", str(repo))
    git(repo, "config", "user.name", "Fixture User")
    git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-m", "initial")


def audit(repo: Path, *options: str) -> dict:
    result = run("python3", str(SCRIPT), "--repository", str(repo), "--json", *options)
    return json.loads(result.stdout)


def by_path(report: dict, path: Path) -> dict:
    expected = str(path.resolve())
    return next(item for item in report["worktrees"] if item["path"] == expected)


class AuditWorktreesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="worktree hygiene ")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_clean_named_worktree_without_remote_and_with_spaces(self) -> None:
        repo = self.root / "repository with spaces"
        linked = self.root / "linked worktree with spaces"
        initialize(repo)
        git(repo, "worktree", "add", "-b", "feature/clean", str(linked), "main")

        report = audit(repo)
        item = by_path(report, linked)

        self.assertEqual(report["base_refs"], ["refs/heads/main"])
        self.assertEqual(item["branch"], "refs/heads/feature/clean")
        self.assertTrue(item["refs"]["branch_retained"])
        self.assertTrue(item["refs"]["branch_matches_head"])
        self.assertEqual(item["refs"]["reachable_from_bases"], ["refs/heads/main"])
        self.assertEqual(item["local_state"]["tracked_entries"], 0)

        git(repo, "worktree", "remove", str(linked))
        after = audit(repo)

        self.assertNotIn(
            str(linked.resolve()), [entry["path"] for entry in after["worktrees"]]
        )
        self.assertEqual(
            git(
                repo, "show-ref", "--verify", "--hash", "refs/heads/feature/clean"
            ).stdout.strip(),
            item["head"],
        )

    def test_counts_tracked_staged_untracked_and_ignored_state(self) -> None:
        repo = self.root / "dirty"
        initialize(repo)
        (repo / ".gitignore").write_text(".env.local\n*.db\n", encoding="utf-8")
        git(repo, "add", ".gitignore")
        git(repo, "commit", "-m", "ignore local state")
        (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        (repo / "staged.txt").write_text("staged\n", encoding="utf-8")
        git(repo, "add", "staged.txt")
        (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
        (repo / ".env.local").write_text("SECRET=fixture\n", encoding="utf-8")
        (repo / "state.db").write_text("fixture\n", encoding="utf-8")

        default_item = by_path(audit(repo), repo)
        item = by_path(audit(repo, "--show-ignored-paths"), repo)
        state = item["local_state"]

        self.assertEqual(state["staged"], 1)
        self.assertEqual(state["unstaged"], 1)
        self.assertEqual(state["untracked"], 1)
        self.assertEqual(state["ignored"], 2)
        self.assertNotIn("ignored_paths", default_item)
        self.assertEqual(item["ignored_paths"], [".env.local", "state.db"])
        self.assertNotIn("SECRET", json.dumps(item))

    def test_distinguishes_reachable_and_unique_detached_heads(self) -> None:
        repo = self.root / "detached"
        reachable = self.root / "reachable detached"
        unique = self.root / "unique detached"
        initialize(repo)
        git(repo, "worktree", "add", "--detach", str(reachable), "main")
        git(repo, "worktree", "add", "--detach", str(unique), "main")
        (unique / "unique.txt").write_text("unique\n", encoding="utf-8")
        git(unique, "add", "unique.txt")
        git(unique, "commit", "-m", "unique detached commit")

        report = audit(repo)
        reachable_item = by_path(report, reachable)
        unique_item = by_path(report, unique)

        self.assertEqual(
            reachable_item["refs"]["reachable_from_bases"], ["refs/heads/main"]
        )
        self.assertEqual(unique_item["refs"]["reachable_from_bases"], [])
        self.assertEqual(unique_item["refs"]["containing_ref_count"], 0)

    def test_reports_locked_prunable_missing_and_active_operation(self) -> None:
        repo = self.root / "registry"
        locked = self.root / "locked"
        stale = self.root / "stale"
        initialize(repo)
        git(repo, "worktree", "add", "-b", "locked-branch", str(locked), "main")
        git(repo, "worktree", "lock", "--reason", "fixture lock", str(locked))
        git(repo, "worktree", "add", "-b", "stale-branch", str(stale), "main")
        shutil.rmtree(stale)
        git_dir = Path(
            git(repo, "rev-parse", "--path-format=absolute", "--git-dir").stdout.strip()
        )
        (git_dir / "MERGE_HEAD").write_text(
            git(repo, "rev-parse", "HEAD").stdout, encoding="utf-8"
        )

        report = audit(repo)
        primary = by_path(report, repo)
        locked_item = by_path(report, locked)
        stale_item = by_path(report, stale)

        self.assertEqual(locked_item["locked"], "fixture lock")
        self.assertFalse(stale_item["path_exists"])
        self.assertTrue(stale_item["prunable"])
        self.assertIn("merge", primary["active_operations"])

    def test_reports_configured_submodule_and_untracked_nested_repository(self) -> None:
        repo = self.root / "outer"
        subsource = self.root / "subsource"
        initialize(repo)
        initialize(subsource)
        git(
            repo,
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            str(subsource),
            "vendor/sub",
        )
        git(repo, "commit", "-am", "add submodule")
        nested = repo / "scratch" / "nested"
        initialize(nested)

        item = by_path(audit(repo), repo)

        self.assertEqual(item["submodules"]["configured"], 1)
        self.assertEqual(item["submodules"]["initialized"], 1)
        self.assertEqual(item["nested_repositories"]["count"], 1)

    def test_text_output_states_that_it_does_not_authorize_removal(self) -> None:
        repo = self.root / "text"
        initialize(repo)

        result = run("python3", str(SCRIPT), "--repository", str(repo))

        self.assertIn("evidence only", result.stdout)
        self.assertIn("does not authorize removal", result.stdout)


if __name__ == "__main__":
    unittest.main()
