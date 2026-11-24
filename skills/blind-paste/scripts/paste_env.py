#!/usr/bin/env python3
"""Model-blind macOS credential intake for ignored dotenv files."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Sequence


ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PLACEHOLDERS = {
    "changeme",
    "placeholder",
    "replace-me",
    "todo",
}

JXA_SCRIPT = r'''
ObjC.import('AppKit');

function run(argv) {
  const app = $.NSApplication.sharedApplication;
  app.setActivationPolicy($.NSApplicationActivationPolicyAccessory);

  const alert = $.NSAlert.alloc.init;
  alert.messageText = argv[1];
  alert.informativeText = argv[0] +
    '\n\nCopy the value, then click “Paste from Clipboard”. ' +
    'Or type it below and click “Save Typed Value”.';
  alert.addButtonWithTitle('Paste from Clipboard');
  alert.addButtonWithTitle('Save Typed Value');
  alert.addButtonWithTitle('Cancel');

  const field = $.NSSecureTextField.alloc.initWithFrame(
    $.NSMakeRect(0, 0, 360, 24)
  );
  field.placeholderString = 'Value is hidden';
  alert.accessoryView = field;
  alert.window.initialFirstResponder = field;

  app.activateIgnoringOtherApps(true);
  const response = alert.runModal;
  if (response == $.NSAlertFirstButtonReturn) {
    const clipboard = $.NSPasteboard.generalPasteboard;
    const clipboardValue = clipboard.stringForType(
      $.NSPasteboardTypeString
    );
    const value = clipboardValue ? ObjC.unwrap(clipboardValue) : '';
    if (value) clipboard.clearContents;
    return value;
  }
  if (response == $.NSAlertSecondButtonReturn) {
    return ObjC.unwrap(field.stringValue);
  }
  throw new Error('__BLIND_PASTE_CANCELLED__');
}
'''


class BlindPasteError(Exception):
    """A safe-to-report error identified only by a non-secret code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class Cancelled(BlindPasteError):
    def __init__(self) -> None:
        super().__init__("cancelled")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect hidden values and merge them into an ignored env file.",
    )
    parser.add_argument("--target", required=True, help="Absolute dotenv target path")
    parser.add_argument(
        "--key",
        action="append",
        dest="keys",
        default=[],
        help="Environment variable to collect interactively (fallback outside T3); repeat for multiple values",
    )
    parser.add_argument(
        "--from-file",
        action="append",
        dest="from_files",
        default=[],
        metavar="KEY=PATH",
        help="Merge KEY from a one-use secret delivery file (e.g. T3 request_secret delivery=file) and unlink it",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace populated values (requires user authorization)",
    )
    parser.add_argument(
        "--allow-worktree-local",
        action="store_true",
        help="Allow an explicitly authorized env file in a linked worktree",
    )
    parser.add_argument("--title", default="Secure env paste", help="Dialog title")
    args = parser.parse_args(argv)
    if bool(args.keys) == bool(args.from_files):
        parser.error("provide either --from-file KEY=PATH or --key NAME (not both)")
    return args


def parse_file_inputs(entries: Sequence[str]) -> list[tuple[str, Path]]:
    parsed: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for entry in entries:
        if "=" not in entry:
            raise BlindPasteError("invalid-from-file")
        key, raw_path = entry.split("=", 1)
        if not ENV_NAME_RE.fullmatch(key):
            raise BlindPasteError("invalid-env-name")
        if not raw_path:
            raise BlindPasteError("invalid-from-file")
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            raise BlindPasteError("source-must-be-absolute")
        if key in seen:
            raise BlindPasteError("duplicate-env-name")
        seen.add(key)
        parsed.append((key, path))
    return parsed


def read_secret_file(path: Path) -> str:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise BlindPasteError("source-file-missing") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise BlindPasteError("source-file-unreadable") from exc
    value = raw.rstrip("\r\n")
    if not value:
        raise BlindPasteError("empty-value")
    return value


def resolve_target(raw_target: str) -> Path:
    expanded = Path(raw_target).expanduser()
    if not expanded.is_absolute():
        raise BlindPasteError("target-must-be-absolute")
    target = expanded.resolve(strict=False)
    lowered = target.name.lower()
    if not (
        lowered == ".env"
        or lowered.startswith(".env.")
        or lowered.endswith(".env")
    ):
        raise BlindPasteError("env-target-required")
    if lowered.endswith((".example", ".sample", ".template")):
        raise BlindPasteError("template-target-refused")
    if target.exists() and not target.is_file():
        raise BlindPasteError("target-is-not-a-file")
    return target


def validate_keys(keys: Sequence[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if not ENV_NAME_RE.fullmatch(key):
            raise BlindPasteError("invalid-env-name")
        if key not in seen:
            unique.append(key)
            seen.add(key)
    return unique


def ensure_untracked_or_external(
    target: Path,
    *,
    allow_worktree_local: bool = False,
) -> None:
    # Callers normally arrive through resolve_target(), but this function is
    # also the security boundary for library use. Canonicalize again so macOS
    # aliases such as /var -> /private/var cannot make a repository target
    # appear to sit outside the resolved Git root.
    target = target.resolve(strict=False)
    ancestor = target.parent
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent

    try:
        root_result = subprocess.run(
            ["git", "-C", str(ancestor), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise BlindPasteError("git-check-unavailable") from exc

    if root_result.returncode != 0:
        if not is_managed_external_target(target):
            raise BlindPasteError("external-target-refused")
        return

    root = Path(root_result.stdout.strip()).resolve()
    try:
        relative = target.relative_to(root)
    except ValueError:
        return

    if is_linked_worktree(root) and not allow_worktree_local:
        raise BlindPasteError("secondary-worktree-target-refused")

    if ".git" in relative.parts:
        raise BlindPasteError("git-metadata-target-refused")

    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", str(relative)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if tracked.returncode == 0:
        raise BlindPasteError("tracked-target-refused")

    ignored = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-q", "--", str(relative)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if ignored.returncode != 0:
        raise BlindPasteError("unignored-target-refused")


def is_linked_worktree(root: Path) -> bool:
    git_dir = git_path(root, "--absolute-git-dir")
    common_dir = git_path(root, "--path-format=absolute", "--git-common-dir")
    return git_dir != common_dir


def git_path(root: Path, *args: str) -> Path:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    value = result.stdout.strip()
    if result.returncode != 0 or not value:
        raise BlindPasteError("git-check-failed")
    return Path(value).resolve()


def managed_secret_roots() -> list[Path]:
    roots = [(Path.home() / ".codex" / "secrets").resolve()]
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        configured = (Path(codex_home).expanduser() / "secrets").resolve()
        if configured not in roots:
            roots.append(configured)
    return roots


def is_managed_external_target(target: Path) -> bool:
    for root in managed_secret_roots():
        try:
            target.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def assignment_pattern(key: str) -> re.Pattern[str]:
    return re.compile(
        rf"^[ \t]*(?:export[ \t]+)?{re.escape(key)}[ \t]*=[ \t]*(?P<value>[^\r\n]*)(?P<newline>\r?\n?)$",
    )


def find_assignment(lines: Sequence[str], key: str) -> tuple[int, str] | None:
    matches: list[tuple[int, str]] = []
    pattern = assignment_pattern(key)
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            matches.append((index, match.group("value")))
    if len(matches) > 1:
        raise BlindPasteError("duplicate-env-name")
    return matches[0] if matches else None


def value_is_missing(raw_value: str) -> bool:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    elif "#" in value:
        value = value.split("#", 1)[0].rstrip()
    normalized = value.strip().lower()
    return (
        not normalized
        or normalized in PLACEHOLDERS
        or normalized.startswith("replace-with-")
        or (normalized.startswith("<") and normalized.endswith(">"))
    )


def encode_dotenv_value(value: str) -> str:
    if not value or "\x00" in value or "\n" in value or "\r" in value:
        raise BlindPasteError("value-must-be-single-line")
    if value == value.strip() and "#" not in value:
        return value
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value and "\\n" not in value and "\\r" not in value:
        return f'"{value}"'
    raise BlindPasteError("value-not-dotenv-compatible")


def native_hidden_prompt(key: str, title: str) -> str:
    if sys.platform != "darwin":
        raise BlindPasteError("unsupported-platform")
    result = subprocess.run(
        [
            "osascript",
            "-l",
            "JavaScript",
            "-e",
            JXA_SCRIPT,
            "--",
            f"Paste {key}. The value stays out of chat and command history.",
            title,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        if "__BLIND_PASTE_CANCELLED__" in result.stderr:
            raise Cancelled()
        raise BlindPasteError("dialog-failed")
    value = result.stdout.removesuffix("\n")
    if not value:
        raise BlindPasteError("empty-value")
    return value


def merge_values(contents: str, values: dict[str, str]) -> str:
    lines = contents.splitlines(keepends=True)
    for key, value in values.items():
        encoded = encode_dotenv_value(value)
        assignment = find_assignment(lines, key)
        if assignment is None:
            if lines and not lines[-1].endswith(("\n", "\r")):
                lines[-1] += "\n"
            lines.append(f"{key}={encoded}\n")
            continue
        index, _ = assignment
        newline = "\r\n" if lines[index].endswith("\r\n") else "\n"
        if not lines[index].endswith(("\n", "\r")):
            newline = ""
        lines[index] = f"{key}={encoded}{newline}"
    return "".join(lines)


def write_atomically(target: Path, contents: str) -> None:
    parent_existed = target.parent.exists()
    old_umask = os.umask(0o077)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    finally:
        os.umask(old_umask)
    if not parent_existed:
        os.chmod(target.parent, 0o700)

    temporary_path: str | None = None
    try:
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=f".{target.name}.",
            dir=target.parent,
            text=True,
        )
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
        os.chmod(target, 0o600)
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def collect_and_store(
    target: Path,
    keys: Sequence[str],
    *,
    replace: bool,
    allow_worktree_local: bool = False,
    title: str,
    prompt: Callable[[str, str], str] = native_hidden_prompt,
) -> str:
    ensure_untracked_or_external(
        target,
        allow_worktree_local=allow_worktree_local,
    )
    try:
        contents = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        contents = ""
    except UnicodeDecodeError as exc:
        raise BlindPasteError("target-is-not-utf8") from exc

    lines = contents.splitlines(keepends=True)
    missing: list[str] = []
    for key in keys:
        assignment = find_assignment(lines, key)
        if replace or assignment is None or value_is_missing(assignment[1]):
            missing.append(key)

    if not missing:
        os.chmod(target, 0o600)
        return "ready"

    collected: dict[str, str] = {}
    for key in missing:
        collected[key] = prompt(key, title)
    write_atomically(target, merge_values(contents, collected))
    return "saved"


def store_from_files(
    target: Path,
    entries: Sequence[tuple[str, Path]],
    *,
    replace: bool,
    allow_worktree_local: bool = False,
    unlink_sources: bool = True,
) -> str:
    ensure_untracked_or_external(
        target,
        allow_worktree_local=allow_worktree_local,
    )
    try:
        contents = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        contents = ""
    except UnicodeDecodeError as exc:
        raise BlindPasteError("target-is-not-utf8") from exc

    lines = contents.splitlines(keepends=True)
    needed: list[tuple[str, Path]] = []
    for key, path in entries:
        assignment = find_assignment(lines, key)
        if replace or assignment is None or value_is_missing(assignment[1]):
            needed.append((key, path))

    if not needed:
        os.chmod(target, 0o600)
        if unlink_sources:
            for _, path in entries:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
        return "ready"

    collected = {key: read_secret_file(path) for key, path in needed}
    write_atomically(target, merge_values(contents, collected))
    if unlink_sources:
        for _, path in entries:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
    return "saved"


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
        target = resolve_target(args.target)
        if args.from_files:
            entries = parse_file_inputs(args.from_files)
            status = store_from_files(
                target,
                entries,
                replace=args.replace,
                allow_worktree_local=args.allow_worktree_local,
            )
        else:
            keys = validate_keys(args.keys)
            status = collect_and_store(
                target,
                keys,
                replace=args.replace,
                allow_worktree_local=args.allow_worktree_local,
                title=args.title,
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
        print("error:write-failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
