from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("paste_env.py")
SPEC = importlib.util.spec_from_file_location("blind_paste_paste_env", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
paste_env = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = paste_env
SPEC.loader.exec_module(paste_env)


class BlindPasteTests(unittest.TestCase):
    def assert_safe_error(self, code: str, callback, *args) -> None:
        with self.assertRaises(paste_env.BlindPasteError) as caught:
            callback(*args)
        self.assertEqual(caught.exception.code, code)

    def init_repo(self, root: Path) -> None:
        subprocess.run(
            ["git", "init", "-q", str(root)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_target_must_be_absolute_env_file(self) -> None:
        self.assert_safe_error(
            "target-must-be-absolute",
            paste_env.resolve_target,
            ".env.local",
        )
        self.assert_safe_error(
            "env-target-required",
            paste_env.resolve_target,
            "/tmp/credential.txt",
        )
        self.assert_safe_error(
            "template-target-refused",
            paste_env.resolve_target,
            "/tmp/.env.example",
        )
        self.assertEqual(
            paste_env.resolve_target("/tmp/project/.env.local"),
            Path("/tmp/project/.env.local").resolve(strict=False),
        )

    def test_keys_are_validated_and_deduplicated(self) -> None:
        self.assertEqual(
            paste_env.validate_keys(["API_KEY", "SECOND_2", "API_KEY"]),
            ["API_KEY", "SECOND_2"],
        )
        self.assert_safe_error(
            "invalid-env-name",
            paste_env.validate_keys,
            ["API-KEY"],
        )

    def test_merge_preserves_unrelated_lines_and_quotes_when_needed(self) -> None:
        contents = "# local settings\nUNCHANGED=yes\nAPI_KEY=replace-me\n"
        merged = paste_env.merge_values(
            contents,
            {"API_KEY": "value with spaces", "HASHED": "abc#123"},
        )
        self.assertEqual(
            merged,
            "# local settings\nUNCHANGED=yes\n"
            "API_KEY=value with spaces\nHASHED='abc#123'\n",
        )

    def test_duplicate_assignment_is_refused(self) -> None:
        self.assert_safe_error(
            "duplicate-env-name",
            paste_env.merge_values,
            "API_KEY=one\nAPI_KEY=two\n",
            {"API_KEY": "three"},
        )

    def test_multiline_and_unrepresentable_values_are_refused(self) -> None:
        self.assert_safe_error(
            "value-must-be-single-line",
            paste_env.encode_dotenv_value,
            "first\nsecond",
        )
        self.assert_safe_error(
            "value-not-dotenv-compatible",
            paste_env.encode_dotenv_value,
            "both'quotes\"and\\nsequence#",
        )

    def test_collects_only_missing_values_and_sets_owner_only_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.init_repo(root)
            (root / ".gitignore").write_text(".env.local\n", encoding="utf-8")
            target = root / ".env.local"
            target.write_text("EXISTING=preserved\nMISSING=<value>\n", encoding="utf-8")
            os.chmod(target, 0o644)
            prompts: list[str] = []

            def prompt(key: str, _title: str) -> str:
                prompts.append(key)
                return "unit-test-value"

            result = paste_env.collect_and_store(
                target,
                ["EXISTING", "MISSING"],
                replace=False,
                title="test",
                prompt=prompt,
            )

            self.assertEqual(result, "saved")
            self.assertEqual(prompts, ["MISSING"])
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                "EXISTING=preserved\nMISSING=unit-test-value\n",
            )
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_populated_value_is_preserved_without_prompting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.init_repo(root)
            (root / ".gitignore").write_text(".env.local\n", encoding="utf-8")
            target = root / ".env.local"
            target.write_text("API_KEY=existing-value\n", encoding="utf-8")
            os.chmod(target, 0o644)

            result = paste_env.collect_and_store(
                target,
                ["API_KEY"],
                replace=False,
                title="test",
                prompt=lambda *_: self.fail("prompt should not open"),
            )

            self.assertEqual(result, "ready")
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                "API_KEY=existing-value\n",
            )
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_replace_requires_the_explicit_replace_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.init_repo(root)
            (root / ".gitignore").write_text(".env.local\n", encoding="utf-8")
            target = root / ".env.local"
            target.write_text("API_KEY=old-value\n", encoding="utf-8")

            result = paste_env.collect_and_store(
                target,
                ["API_KEY"],
                replace=True,
                title="test",
                prompt=lambda *_: "new-value",
            )

            self.assertEqual(result, "saved")
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                "API_KEY=new-value\n",
            )

    def test_tracked_target_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.init_repo(root)
            target = root / ".env.local"
            target.write_text("API_KEY=existing\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", ".env.local"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assert_safe_error(
                "tracked-target-refused",
                paste_env.ensure_untracked_or_external,
                target,
            )

    def test_unignored_repository_target_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.init_repo(root)
            self.assert_safe_error(
                "unignored-target-refused",
                paste_env.ensure_untracked_or_external,
                root / ".env.local",
            )

    def test_cli_requires_explicit_override_for_secondary_worktree_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            primary = fixture / "primary"
            secondary = fixture / "secondary"
            primary.mkdir()
            self.init_repo(primary)
            (primary / ".gitignore").write_text(".env.local\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(primary), "add", ".gitignore"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(primary),
                    "-c",
                    "user.name=Blind Paste Tests",
                    "-c",
                    "user.email=blind-paste-tests@example.invalid",
                    "commit",
                    "-q",
                    "-m",
                    "fixture",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(primary),
                    "worktree",
                    "add",
                    "-q",
                    "-b",
                    "secondary-fixture",
                    str(secondary),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            target = secondary / ".env.local"
            target.write_text("API_KEY=must-not-appear\n", encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()

            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = paste_env.main(
                    ["--target", str(target), "--key", "API_KEY"]
                )

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(
                stderr.getvalue(),
                "error:secondary-worktree-target-refused\n",
            )
            self.assertNotIn("must-not-appear", stderr.getvalue())

            override_stdout = io.StringIO()
            override_stderr = io.StringIO()
            with contextlib.redirect_stdout(override_stdout), contextlib.redirect_stderr(
                override_stderr
            ):
                override_exit_code = paste_env.main(
                    [
                        "--target",
                        str(target),
                        "--key",
                        "API_KEY",
                        "--allow-worktree-local",
                    ]
                )

            self.assertEqual(override_exit_code, 0)
            self.assertEqual(override_stdout.getvalue(), "ready\n")
            self.assertEqual(override_stderr.getvalue(), "")
            self.assertNotIn("must-not-appear", override_stdout.getvalue())

    def test_external_target_requires_a_managed_secret_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / ".env.local"
            with mock.patch.object(paste_env, "managed_secret_roots", return_value=[]):
                self.assert_safe_error(
                    "external-target-refused",
                    paste_env.ensure_untracked_or_external,
                    target,
                )

            with mock.patch.object(
                paste_env,
                "managed_secret_roots",
                return_value=[Path(temporary).resolve()],
            ):
                paste_env.ensure_untracked_or_external(target)

    def test_non_macos_never_falls_back_to_a_visible_prompt(self) -> None:
        with mock.patch.object(paste_env.sys, "platform", "linux"):
            self.assert_safe_error(
                "unsupported-platform",
                paste_env.native_hidden_prompt,
                "API_KEY",
                "test",
            )

    def test_cli_reports_status_without_printing_existing_value(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.init_repo(root)
            (root / ".gitignore").write_text(".env.local\n", encoding="utf-8")
            target = root / ".env.local"
            target.write_text("API_KEY=must-not-appear\n", encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()

            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = paste_env.main(
                    ["--target", str(target), "--key", "API_KEY"]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "ready\n")
            self.assertEqual(stderr.getvalue(), "")
            self.assertNotIn("must-not-appear", stdout.getvalue())

    def test_from_file_merges_and_unlinks_delivery_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.init_repo(root)
            (root / ".gitignore").write_text(".env.local\n", encoding="utf-8")
            target = root / ".env.local"
            src = root / "secret_delivery"
            src.write_text("top-secret-value\n", encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()

            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = paste_env.main(
                    ["--target", str(target), "--from-file", f"API_KEY={src}"]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "saved\n")
            self.assertEqual(stderr.getvalue(), "")
            self.assertNotIn("top-secret-value", stdout.getvalue())
            self.assertFalse(src.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "API_KEY=top-secret-value\n")
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_from_file_preserves_populated_value_without_replace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.init_repo(root)
            (root / ".gitignore").write_text(".env.local\n", encoding="utf-8")
            target = root / ".env.local"
            target.write_text("API_KEY=existing-value\n", encoding="utf-8")
            src = root / "secret_delivery"
            src.write_text("new-value\n", encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()

            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = paste_env.main(
                    ["--target", str(target), "--from-file", f"API_KEY={src}"]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "ready\n")
            self.assertFalse(src.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "API_KEY=existing-value\n")


if __name__ == "__main__":
    unittest.main()
