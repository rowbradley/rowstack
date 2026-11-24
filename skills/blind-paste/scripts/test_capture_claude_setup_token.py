from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("capture_claude_setup_token.py")
SPEC = importlib.util.spec_from_file_location("capture_claude_setup_token", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
capture = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = capture
SPEC.loader.exec_module(capture)


class CaptureClaudeSetupTokenTests(unittest.TestCase):
    token = "sk-ant-oat01-" + "A" * 95

    def child_command(self, output: str, *, prompt_for_code: bool = False) -> list[str]:
        if prompt_for_code:
            source = (
                "import sys; "
                "sys.stdout.write('Paste code here if prompted > '); "
                "sys.stdout.flush(); "
                "code=sys.stdin.readline().strip(); "
                f"sys.stdout.write({output!r} if code == 'fixture-code' else 'bad'); "
                "sys.stdout.flush()"
            )
        else:
            source = f"import sys; sys.stdout.write({output!r}); sys.stdout.flush()"
        return [sys.executable, "-c", source]

    def test_reconstructs_a_token_wrapped_after_79_characters(self) -> None:
        wrapped = self.token[:79] + "\r\n" + self.token[79:]
        self.assertEqual(capture.extract_token(wrapped), self.token)

    def test_rejects_the_first_wrapped_segment(self) -> None:
        self.assertIsNone(capture.extract_token(self.token[:79]))

    def test_ignores_terminal_control_sequences_inside_token(self) -> None:
        decorated = self.token[:79] + "\x1b[0m\r\n\x1b[32m" + self.token[79:]
        self.assertEqual(capture.extract_token(decorated), self.token)

    def test_captures_complete_token_without_printing_it(self) -> None:
        stored: list[str] = []
        stdout = io.StringIO()
        stderr = io.StringIO()
        wrapped = self.token[:79] + "\r\n" + self.token[79:]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = capture.capture_from_command(
                self.child_command(wrapped),
                save_token=stored.append,
                timeout=2,
            )

        self.assertEqual(status, "saved")
        self.assertEqual(stored, [self.token])
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_relays_manual_code_without_echoing_either_secret(self) -> None:
        stored: list[str] = []
        wrapped = self.token[:79] + "\n" + self.token[79:]
        status = capture.capture_from_command(
            self.child_command(wrapped, prompt_for_code=True),
            save_token=stored.append,
            timeout=2,
            prompt=lambda *_: "fixture-code",
        )
        self.assertEqual(status, "saved")
        self.assertEqual(stored, [self.token])

    def test_exit_without_complete_token_returns_safe_error(self) -> None:
        with self.assertRaises(capture.BlindPasteError) as caught:
            capture.capture_from_command(
                self.child_command(self.token[:79]),
                save_token=lambda _token: self.fail("unexpected token"),
                timeout=2,
            )
        self.assertEqual(caught.exception.code, "token-not-seen")


if __name__ == "__main__":
    unittest.main()
