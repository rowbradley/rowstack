#!/usr/bin/env python3
"""Capture a complete Claude setup-token without displaying it."""

from __future__ import annotations

import argparse
import fcntl
import os
import pty
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import termios
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from paste_env import (
    BlindPasteError,
    Cancelled,
    ensure_untracked_or_external,
    find_assignment,
    merge_values,
    native_hidden_prompt,
    resolve_target,
    value_is_missing,
    write_atomically,
)


ENV_NAME = "CLAUDE_CODE_OAUTH_TOKEN"
TOKEN_PREFIX = "sk-ant-oat01-"
TOKEN_LENGTH = 108
TOKEN_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
)
CODE_PROMPT_PATTERN = re.compile(r"Paste code here if prompted\s*>\s*$", re.MULTILINE)
ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
READ_SIZE = 4096
OUTPUT_WINDOW = 65_536
PTY_COLUMNS = 4096


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a complete Claude setup-token into an ignored env file.",
    )
    parser.add_argument("--target", required=True, help="Absolute dotenv target path")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace a populated token after explicit rotation authorization",
    )
    parser.add_argument("--timeout", type=float, default=600.0)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def extract_token(output: str) -> str | None:
    clean = ANSI_ESCAPE.sub("", output)
    start = clean.rfind(TOKEN_PREFIX)
    if start < 0:
        return None

    token_chars: list[str] = []
    for char in clean[start:]:
        if char in TOKEN_CHARACTERS:
            token_chars.append(char)
            if len(token_chars) == TOKEN_LENGTH:
                token = "".join(token_chars)
                return token if token.startswith(TOKEN_PREFIX) else None
            continue
        if char.isspace():
            continue
        return None
    return None


def configure_pty(slave_fd: int) -> None:
    attributes = termios.tcgetattr(slave_fd)
    attributes[3] &= ~(termios.ECHO | termios.ECHONL)
    termios.tcsetattr(slave_fd, termios.TCSANOW, attributes)
    fcntl.ioctl(
        slave_fd,
        termios.TIOCSWINSZ,
        struct.pack("HHHH", 24, PTY_COLUMNS, 0, 0),
    )


def terminate_child(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=2)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass


def read_available(master_fd: int, timeout: float) -> bytes:
    readable, _, _ = select.select([master_fd], [], [], timeout)
    if not readable:
        return b""
    try:
        return os.read(master_fd, READ_SIZE)
    except OSError:
        return b""


def write_all(file_descriptor: int, payload: bytes) -> None:
    written = 0
    while written < len(payload):
        written += os.write(file_descriptor, payload[written:])


def capture_from_command(
    command: Sequence[str],
    *,
    save_token: Callable[[str], None],
    timeout: float,
    prompt: Callable[[str, str], str] = native_hidden_prompt,
) -> str:
    master_fd, slave_fd = pty.openpty()
    process: subprocess.Popen[bytes] | None = None
    submitted_code = False
    observed = ""
    try:
        configure_pty(slave_fd)
        try:
            process = subprocess.Popen(
                list(command),
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            raise BlindPasteError("command-not-found") from exc
        finally:
            os.close(slave_fd)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            chunk = read_available(master_fd, min(0.1, deadline - time.monotonic()))
            if chunk:
                observed = (observed + chunk.decode("utf-8", errors="replace"))[
                    -OUTPUT_WINDOW:
                ]
                token = extract_token(observed)
                if token is not None:
                    save_token(token)
                    token = ""
                    observed = ""
                    return "saved"
                if not submitted_code and CODE_PROMPT_PATTERN.search(observed):
                    code = prompt("Claude authorization code", "Secure Claude setup")
                    if not code or "\x00" in code or "\n" in code or "\r" in code:
                        raise BlindPasteError("value-must-be-single-line")
                    write_all(master_fd, code.encode("utf-8") + b"\n")
                    code = ""
                    submitted_code = True
                    observed = ""
            return_code = process.poll()
            if return_code is not None:
                if return_code != 0:
                    raise BlindPasteError("child-failed")
                raise BlindPasteError("token-not-seen")
        raise BlindPasteError("completion-timeout")
    finally:
        if process is not None:
            terminate_child(process)
        try:
            os.close(master_fd)
        except OSError:
            pass


def token_writer(target: Path, *, replace: bool) -> Callable[[str], None]:
    ensure_untracked_or_external(target)
    try:
        contents = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        contents = ""
    except UnicodeDecodeError as exc:
        raise BlindPasteError("target-is-not-utf8") from exc

    assignment = find_assignment(contents.splitlines(keepends=True), ENV_NAME)
    if assignment is not None and not value_is_missing(assignment[1]) and not replace:
        raise BlindPasteError("credential-already-set")

    def save(token: str) -> None:
        if len(token) != TOKEN_LENGTH:
            raise BlindPasteError("invalid-token-length")
        write_atomically(target, merge_values(contents, {ENV_NAME: token}))

    return save


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
        target = resolve_target(args.target)
        claude_binary = shutil.which("claude")
        if claude_binary is None:
            raise BlindPasteError("command-not-found")
        status = capture_from_command(
            [claude_binary, "setup-token"],
            save_token=token_writer(target, replace=args.replace),
            timeout=args.timeout,
        )
        print(status)
        return 0
    except Cancelled:
        print("cancelled")
        return 2
    except BlindPasteError as exc:
        print(f"error:{exc.code}", file=sys.stderr)
        return 1
    except OSError:
        print("error:capture-failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
