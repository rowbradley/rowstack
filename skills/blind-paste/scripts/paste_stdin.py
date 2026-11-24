#!/usr/bin/env python3
"""Model-blind one-time secret handoff to a trusted interactive command."""

from __future__ import annotations

import argparse
import os
import pty
import re
import select
import signal
import subprocess
import sys
import termios
import time
from collections.abc import Callable, Sequence

from paste_env import BlindPasteError, Cancelled, native_hidden_prompt


READ_SIZE = 4096
PROMPT_WINDOW = 65_536


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect a one-time secret in a native dialog and pass it to a "
            "trusted child process without exposing it in tool output."
        ),
    )
    parser.add_argument("--label", required=True, help="Non-secret value label")
    parser.add_argument(
        "--prompt-pattern",
        required=True,
        help="Regex emitted by the child immediately before reading the value",
    )
    parser.add_argument("--title", default="Secure one-time paste")
    parser.add_argument("--prompt-timeout", type=float, default=300.0)
    parser.add_argument("--completion-timeout", type=float, default=60.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("a trusted child command is required after --")
    if args.prompt_timeout <= 0 or args.completion_timeout <= 0:
        parser.error("timeouts must be positive")
    try:
        args.compiled_prompt = re.compile(args.prompt_pattern)
    except re.error as exc:
        parser.error(f"invalid --prompt-pattern: {exc}")
    return args


def validate_secret_value(value: str) -> str:
    if not value or "\x00" in value or "\n" in value or "\r" in value:
        raise BlindPasteError("value-must-be-single-line")
    return value


def disable_terminal_echo(file_descriptor: int) -> None:
    attributes = termios.tcgetattr(file_descriptor)
    attributes[3] &= ~(termios.ECHO | termios.ECHONL)
    termios.tcsetattr(file_descriptor, termios.TCSANOW, attributes)


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


def write_all(file_descriptor: int, payload: bytes) -> None:
    written = 0
    while written < len(payload):
        written += os.write(file_descriptor, payload[written:])


def read_available(master_fd: int, timeout: float) -> bytes:
    readable, _, _ = select.select([master_fd], [], [], timeout)
    if not readable:
        return b""
    try:
        return os.read(master_fd, READ_SIZE)
    except OSError:
        return b""


def wait_for_prompt(
    process: subprocess.Popen[bytes],
    master_fd: int,
    pattern: re.Pattern[str],
    timeout: float,
) -> None:
    deadline = time.monotonic() + timeout
    observed = ""
    while time.monotonic() < deadline:
        chunk = read_available(master_fd, min(0.1, deadline - time.monotonic()))
        if chunk:
            observed = (observed + chunk.decode("utf-8", errors="replace"))[
                -PROMPT_WINDOW:
            ]
            if pattern.search(observed):
                return
        if process.poll() is not None:
            raise BlindPasteError("prompt-not-seen")
    raise BlindPasteError("prompt-timeout")


def wait_for_completion(
    process: subprocess.Popen[bytes],
    master_fd: int,
    timeout: float,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        # Drain and discard child output. A trusted CLI should not echo the
        # secret, but suppressing the post-submit stream makes leakage fail-safe.
        read_available(master_fd, min(0.1, deadline - time.monotonic()))
        return_code = process.poll()
        if return_code is not None:
            if return_code != 0:
                raise BlindPasteError("child-failed")
            return
    raise BlindPasteError("completion-timeout")


def run_command_with_secret(
    command: Sequence[str],
    *,
    prompt_pattern: re.Pattern[str],
    label: str,
    title: str,
    prompt_timeout: float,
    completion_timeout: float,
    prompt: Callable[[str, str], str] = native_hidden_prompt,
) -> str:
    master_fd, slave_fd = pty.openpty()
    process: subprocess.Popen[bytes] | None = None
    try:
        disable_terminal_echo(slave_fd)
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

        wait_for_prompt(process, master_fd, prompt_pattern, prompt_timeout)
        value = validate_secret_value(prompt(label, title))
        write_all(master_fd, value.encode("utf-8") + b"\n")
        value = ""
        wait_for_completion(process, master_fd, completion_timeout)
        return "submitted"
    finally:
        if process is not None:
            terminate_child(process)
        try:
            os.close(master_fd)
        except OSError:
            pass


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
        status = run_command_with_secret(
            args.command,
            prompt_pattern=args.compiled_prompt,
            label=args.label,
            title=args.title,
            prompt_timeout=args.prompt_timeout,
            completion_timeout=args.completion_timeout,
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
        print("error:handoff-failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
