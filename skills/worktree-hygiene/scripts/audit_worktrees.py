#!/usr/bin/env python3
"""Read-only evidence collector for Git worktree cleanup decisions."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Iterable


OPERATION_MARKERS = {
    "MERGE_HEAD": "merge",
    "CHERRY_PICK_HEAD": "cherry-pick",
    "REVERT_HEAD": "revert",
    "REBASE_HEAD": "rebase",
    "BISECT_LOG": "bisect",
    "rebase-apply": "rebase",
    "rebase-merge": "rebase",
    "sequencer": "sequencer",
}
CONVENTIONAL_BASES = {"main", "master", "trunk", "develop"}


class AuditError(RuntimeError):
    pass


def run(
    command: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise AuditError(f"cannot run {command[0]}: {exc}") from exc
    if check and result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise AuditError(detail or f"command failed with exit {result.returncode}")
    return result


def git(
    repository: str, *args: str, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    return run(["git", "-C", repository, *args], check=check)


def decode(value: bytes) -> str:
    return value.decode("utf-8", "surrogateescape")


def parse_worktree_list(raw: bytes) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_record in raw.split(b"\0\0"):
        if not raw_record:
            continue
        record: dict[str, Any] = {}
        for raw_field in raw_record.split(b"\0"):
            if not raw_field:
                continue
            key, separator, raw_value = raw_field.partition(b" ")
            name = decode(key)
            value = decode(raw_value) if separator else True
            if name == "worktree":
                record["path"] = value
            elif name == "HEAD":
                record["head"] = value
            elif name == "branch":
                record["branch"] = value
            elif name == "detached":
                record["detached"] = True
            elif name in {"locked", "prunable"}:
                record[name] = value
        if "path" in record:
            records.append(record)
    return records


def parse_status(raw: bytes) -> tuple[dict[str, int], list[str], list[str]]:
    counts = {
        "staged": 0,
        "unstaged": 0,
        "conflicted": 0,
        "untracked": 0,
        "ignored": 0,
        "tracked_entries": 0,
    }
    candidates: list[str] = []
    ignored_paths: list[str] = []
    fields = raw.split(b"\0")
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        if len(field) < 3:
            continue
        status = decode(field[:2])
        path = decode(field[3:])
        candidates.append(path)
        if status == "??":
            counts["untracked"] += 1
            continue
        if status == "!!":
            counts["ignored"] += 1
            ignored_paths.append(path)
            continue
        counts["tracked_entries"] += 1
        x, y = status
        if x not in {" ", "?", "!"}:
            counts["staged"] += 1
        if y not in {" ", "?", "!"}:
            counts["unstaged"] += 1
        if status in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}:
            counts["conflicted"] += 1
        if x in {"R", "C"} or y in {"R", "C"}:
            if index < len(fields) and fields[index]:
                index += 1
    return counts, candidates, ignored_paths


def git_dir_for(path: str) -> Path:
    result = git(path, "rev-parse", "--path-format=absolute", "--git-dir")
    return Path(decode(result.stdout).strip())


def active_operations(path: str) -> list[str]:
    try:
        git_dir = git_dir_for(path)
    except AuditError:
        return []
    found = {
        operation
        for marker, operation in OPERATION_MARKERS.items()
        if (git_dir / marker).exists()
    }
    return sorted(found)


def submodule_state(path: str) -> dict[str, Any]:
    gitmodules = Path(path) / ".gitmodules"
    if not gitmodules.is_file():
        return {"configured": 0, "initialized": 0, "modified": 0, "missing": 0}
    configured = git(
        path,
        "config",
        "-f",
        str(gitmodules),
        "--get-regexp",
        r"^submodule\..*\.path$",
        check=False,
    )
    paths = [
        line.split(maxsplit=1)[1]
        for line in decode(configured.stdout).splitlines()
        if " " in line
    ]
    state = git(path, "submodule", "status", "--recursive", check=False)
    initialized = modified = missing = 0
    for line in decode(state.stdout).splitlines():
        if line.startswith("-"):
            missing += 1
        elif line.startswith(("+", "U")):
            modified += 1
        elif line:
            initialized += 1
    result: dict[str, Any] = {
        "configured": len(paths),
        "initialized": initialized,
        "modified": modified,
        "missing": missing,
    }
    if state.returncode:
        result["visibility_gap"] = "git submodule status did not complete"
    return result


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def nested_repositories(worktree: str, candidates: Iterable[str]) -> dict[str, Any]:
    root = Path(worktree).resolve()
    found: set[str] = set()
    for candidate in candidates:
        candidate_path = (root / candidate.rstrip("/")).resolve()
        if candidate_path == root or not is_within(candidate_path, root):
            continue
        if candidate_path.is_dir() and (candidate_path / ".git").exists():
            found.add(str(candidate_path))
    return {
        "count": len(found),
        "detection": "Git status directory candidates; configured submodules reported separately",
    }


def process_cwds() -> tuple[dict[int, str], str | None]:
    if shutil.which("lsof") is None:
        return {}, "lsof unavailable; process working directories not observed"
    result = run(["lsof", "-a", "-d", "cwd", "-Fpn", "-w"], check=False)
    if result.returncode not in {0, 1}:
        return {}, "lsof could not enumerate process working directories"
    processes: dict[int, str] = {}
    current_pid: int | None = None
    for raw_line in result.stdout.splitlines():
        if raw_line.startswith(b"p"):
            try:
                current_pid = int(raw_line[1:])
            except ValueError:
                current_pid = None
        elif raw_line.startswith(b"n") and current_pid is not None:
            processes[current_pid] = decode(raw_line[1:])
    return processes, None


def processes_within(
    path: str, observed: dict[int, str], gap: str | None
) -> dict[str, Any]:
    root = Path(path).resolve()
    pids = sorted(
        pid
        for pid, cwd in observed.items()
        if Path(cwd).resolve() == root or is_within(Path(cwd).resolve(), root)
    )
    result: dict[str, Any] = {
        "count": len(pids),
        "pids": pids,
        "coverage": "best-effort local CWD visibility from lsof; permissions and sandbox boundaries may hide processes",
    }
    if gap:
        result["visibility_gap"] = gap
    return result


def discover_base_refs(repository: str, records: list[dict[str, Any]]) -> list[str]:
    refs = git(
        repository,
        "for-each-ref",
        "--format=%(refname)%00%(symref)",
        "refs/heads",
        "refs/remotes",
    )
    candidates: list[str] = []
    fields = refs.stdout.split(b"\n")
    for field in fields:
        if not field:
            continue
        raw_ref, _, raw_symref = field.partition(b"\0")
        ref = decode(raw_ref)
        symref = decode(raw_symref)
        short = ref.rsplit("/", 1)[-1]
        if ref.startswith("refs/heads/") and short in CONVENTIONAL_BASES:
            candidates.append(ref)
        if symref:
            candidates.append(symref)
    if records:
        primary_branch = records[0].get("branch")
        if isinstance(primary_branch, str):
            candidates.insert(0, primary_branch)
    return list(dict.fromkeys(candidates))


def ref_evidence(
    repository: str, record: dict[str, Any], bases: list[str]
) -> dict[str, Any]:
    head = str(record.get("head", ""))
    branch = record.get("branch")
    retained: bool | None = None
    branch_matches_head: bool | None = None
    if isinstance(branch, str):
        result = git(repository, "show-ref", "--verify", "--hash", branch, check=False)
        retained = result.returncode == 0
        branch_matches_head = retained and decode(result.stdout).strip() == head
    reachable = []
    for base in bases:
        if (
            git(
                repository, "merge-base", "--is-ancestor", head, base, check=False
            ).returncode
            == 0
        ):
            reachable.append(base)
    containing_result = git(
        repository,
        "for-each-ref",
        "--contains",
        head,
        "--format=%(refname)",
        "refs/heads",
        "refs/remotes",
        "refs/tags",
        check=False,
    )
    containing = [
        line for line in decode(containing_result.stdout).splitlines() if line
    ]
    return {
        "branch_retained": retained,
        "branch_matches_head": branch_matches_head,
        "reachable_from_bases": reachable,
        "containing_ref_count": len(containing),
        "containing_refs": containing[:20],
        "containing_refs_truncated": len(containing) > 20,
    }


def audit(repository: str, *, show_ignored_paths: bool = False) -> dict[str, Any]:
    repository = decode(git(repository, "rev-parse", "--show-toplevel").stdout).strip()
    raw = git(repository, "worktree", "list", "--porcelain", "-z").stdout
    records = parse_worktree_list(raw)
    bases = discover_base_refs(repository, records)
    observed_processes, process_gap = process_cwds()
    worktrees: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        raw_path = str(record["path"])
        path = os.path.realpath(raw_path)
        exists = os.path.isdir(path)
        item: dict[str, Any] = {
            "path": path,
            "listed_path": raw_path,
            "kind": "primary" if index == 0 else "linked",
            "path_exists": exists,
            "head": record.get("head"),
            "branch": record.get("branch"),
            "detached": bool(record.get("detached")),
            "locked": record.get("locked", False),
            "prunable": record.get("prunable", False),
        }
        if not exists:
            item["visibility_gaps"] = [
                "worktree path is missing; local state and processes were not inspected"
            ]
            item["refs"] = ref_evidence(repository, record, bases)
            worktrees.append(item)
            continue
        status = git(
            path,
            "status",
            "--porcelain=v1",
            "-z",
            "--ignored=matching",
            "--untracked-files=all",
            check=False,
        )
        if status.returncode:
            item["visibility_gaps"] = ["git status did not complete"]
            candidates: list[str] = []
        else:
            counts, candidates, ignored_paths = parse_status(status.stdout)
            item["local_state"] = counts
            if show_ignored_paths:
                item["ignored_paths"] = ignored_paths
        item["refs"] = ref_evidence(repository, record, bases)
        item["active_operations"] = active_operations(path)
        item["processes"] = processes_within(path, observed_processes, process_gap)
        item["submodules"] = submodule_state(path)
        item["nested_repositories"] = nested_repositories(path, candidates)
        worktrees.append(item)
    return {
        "repository": os.path.realpath(repository),
        "base_refs": bases,
        "worktrees": worktrees,
        "policy": "evidence-only; no cleanup classification or permission",
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [f"Repository: {report['repository']}"]
    bases = report["base_refs"]
    lines.append("Discovered base refs: " + (", ".join(bases) if bases else "none"))
    lines.append("Policy: evidence only; this report does not authorize removal")
    for item in report["worktrees"]:
        branch = item.get("branch") or "detached"
        lines.extend(
            [
                "",
                f"[{item['kind']}] {item['path']}",
                f"  HEAD: {item.get('head', 'unknown')} ({branch})",
                "  registry: "
                f"exists={item['path_exists']} locked={item['locked']!r} prunable={item['prunable']!r}",
            ]
        )
        if "local_state" in item:
            state = item["local_state"]
            lines.append(
                "  local state: "
                f"staged={state['staged']} unstaged={state['unstaged']} "
                f"conflicted={state['conflicted']} untracked={state['untracked']} ignored={state['ignored']}"
            )
            if "ignored_paths" in item:
                lines.append(
                    "  ignored paths (names only): "
                    + json.dumps(item["ignored_paths"], ensure_ascii=True)
                )
        refs = item["refs"]
        reachable = refs["reachable_from_bases"]
        lines.append(
            "  refs: "
            f"branch_retained={refs['branch_retained']} branch_matches_head={refs['branch_matches_head']} "
            f"reachable_from={','.join(reachable) if reachable else 'none'} "
            f"containing_refs={refs['containing_ref_count']}"
        )
        if "active_operations" in item:
            operations = item["active_operations"]
            lines.append(
                "  active Git operations: "
                + (", ".join(operations) if operations else "none")
            )
            processes = item["processes"]
            process_text = f"count={processes['count']}"
            if processes.get("pids"):
                process_text += " pids=" + ",".join(
                    str(pid) for pid in processes["pids"]
                )
            if processes.get("visibility_gap"):
                process_text += f"; gap={processes['visibility_gap']}"
            lines.append("  process working directories: " + process_text)
            lines.append("  process coverage: " + processes["coverage"])
            submodules = item["submodules"]
            lines.append(
                "  submodules: "
                f"configured={submodules['configured']} initialized={submodules['initialized']} "
                f"modified={submodules['modified']} missing={submodules['missing']}"
            )
            nested = item["nested_repositories"]
            lines.append(
                f"  nested repositories: count={nested['count']} ({nested['detection']})"
            )
        for gap in item.get("visibility_gaps", []):
            lines.append(f"  visibility gap: {gap}")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository", default=os.getcwd(), help="Path inside the repository to audit"
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON")
    parser.add_argument(
        "--show-ignored-paths",
        action="store_true",
        help="Include ignored path names, never file contents",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        report = audit(args.repository, show_ignored_paths=args.show_ignored_paths)
    except AuditError as exc:
        print(f"audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
