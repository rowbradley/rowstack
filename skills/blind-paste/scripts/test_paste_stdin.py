from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import sys
import unittest
import unittest.mock
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("paste_stdin.py")
SPEC = importlib.util.spec_from_file_location("blind_paste_paste_stdin", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
paste_stdin = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = paste_stdin
SPEC.loader.exec_module(paste_stdin)


class PasteStdinTests(unittest.TestCase):
    def child_command(self, *, exit_code: int = 0, emit_prompt: bool = True) -> list[str]:
        source = (
            "import sys; "
            + ("sys.stdout.write('Paste code here >'); sys.stdout.flush(); " if emit_prompt else "")
            + "value=sys.stdin.readline().rstrip('\\n'); "
            + "sys.stdout.write(value); sys.stdout.flush(); "
            + f"sys.exit({exit_code} if value == 'fixture-secret' else 9)"
        )
        return [sys.executable, "-c", source]

    def test_handoff_suppresses_a_child_that_echoes_the_secret(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = paste_stdin.run_command_with_secret(
                self.child_command(),
                prompt_pattern=re.compile("Paste code here"),
                label="fixture code",
                title="test",
                prompt_timeout=2,
                completion_timeout=2,
                prompt=lambda *_: "fixture-secret",
            )

        self.assertEqual(status, "submitted")
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_child_failure_returns_only_a_safe_error_code(self) -> None:
        with self.assertRaises(paste_stdin.BlindPasteError) as caught:
            paste_stdin.run_command_with_secret(
                self.child_command(exit_code=7),
                prompt_pattern=re.compile("Paste code here"),
                label="fixture code",
                title="test",
                prompt_timeout=2,
                completion_timeout=2,
                prompt=lambda *_: "fixture-secret",
            )
        self.assertEqual(caught.exception.code, "child-failed")

    def test_prompt_timeout_never_collects_or_sends_a_secret(self) -> None:
        prompted = False

        def prompt(*_args: str) -> str:
            nonlocal prompted
            prompted = True
            return "fixture-secret"

        with self.assertRaises(paste_stdin.BlindPasteError) as caught:
            paste_stdin.run_command_with_secret(
                self.child_command(emit_prompt=False),
                prompt_pattern=re.compile("Paste code here"),
                label="fixture code",
                title="test",
                prompt_timeout=0.2,
                completion_timeout=1,
                prompt=prompt,
            )
        self.assertEqual(caught.exception.code, "prompt-timeout")
        self.assertFalse(prompted)

    def test_child_exit_before_prompt_never_collects_a_secret(self) -> None:
        prompted = False

        def prompt(*_args: str) -> str:
            nonlocal prompted
            prompted = True
            return "fixture-secret"

        with self.assertRaises(paste_stdin.BlindPasteError) as caught:
            paste_stdin.run_command_with_secret(
                [sys.executable, "-c", "raise SystemExit(0)"],
                prompt_pattern=re.compile("Paste code here"),
                label="fixture code",
                title="test",
                prompt_timeout=1,
                completion_timeout=1,
                prompt=prompt,
            )
        self.assertEqual(caught.exception.code, "prompt-not-seen")
        self.assertFalse(prompted)

    def test_multiline_value_is_refused(self) -> None:
        with self.assertRaises(paste_stdin.BlindPasteError) as caught:
            paste_stdin.run_command_with_secret(
                self.child_command(),
                prompt_pattern=re.compile("Paste code here"),
                label="fixture code",
                title="test",
                prompt_timeout=2,
                completion_timeout=2,
                prompt=lambda *_: "first\nsecond",
            )
        self.assertEqual(caught.exception.code, "value-must-be-single-line")

    def test_cli_status_never_contains_the_secret(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with unittest.mock.patch.object(
                paste_stdin,
                "run_command_with_secret",
                return_value="submitted",
            ):
                exit_code = paste_stdin.main(
                    [
                        "--label",
                        "fixture code",
                        "--prompt-pattern",
                        "Paste code here",
                        "--",
                        "fixture-command",
                    ]
                )
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "submitted\n")
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
