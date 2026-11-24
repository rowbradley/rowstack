# Provider ownership

Git records commits and worktree registrations. It does not know whether Codex,
Cursor, Claude, another agent, or a person expects to resume work in a linked
directory. Resolve that ownership before recommending removal.

## Codex

1. Treat paths under a Codex-managed worktree directory as managed until Codex
   proves otherwise.
2. Use Codex task inventory first. Include archived tasks when the available app
   tools distinguish them. Inspect candidate tasks with the task-reading tool;
   do not open or navigate to each task merely to classify it.
3. An active, running, pinned, interrupted, waiting, or otherwise resumable task
   that uses the path makes the worktree `HOLD`. A completed task may still be
   resumable, so completion alone is not permission to remove its worktree.
4. If inventory does not expose the path, use this exact metadata fallback:
   - search structured JSON records under `$CODEX_HOME/sessions/**/*.jsonl` and
     `$CODEX_HOME/archived_sessions/*.jsonl`;
   - parse JSON and accept only a structured `cwd` field whose normalized
     realpath equals the candidate worktree realpath;
   - derive every task UUID from the matching rollout filenames, then inspect
     every exact task with the Codex task tool; never select one arbitrary match;
   - do not treat a path mentioned in prompts, messages, command output, or other
     transcript prose as ownership evidence.
5. Any retained or resumable exact match is sufficient for `HOLD`. If any exact
   match cannot be inspected, ownership remains unknown and the worktree is
   `HOLD`. When all exact matches are resolved, use `NATIVE_CLEANUP` only if
   Codex provides an operation whose contract explicitly removes the worktree.
   If Codex has no such operation and the user independently closed the owning
   tasks, the worktree can become a manual `REVIEW` candidate after the full
   Git, process, ignored-state, and recovery audit passes.

Do not rewrite, move, hand off, archive, or interrupt a task just to make its
worktree removable. Those are separate user-visible task operations.

Codex task handoff is relocation, not cleanup. It can create or check out a
branch in the destination checkout and leave the source worktree registered.
Never use it as a worktree-removal mechanism. Archiving a task also does not
remove its worktree; verify task state and Git worktree state separately.

## Cursor

Treat Cursor-managed worktree paths as owned by Cursor unless its native task or
worktree inventory establishes otherwise. Active or pinned chats are `HOLD`.
When Cursor exposes a native cleanup decision for an inactive worktree, label it
`NATIVE_CLEANUP`.

If native inventory is unavailable, report that visibility gap and use `HOLD`.
Do not infer abandonment from filesystem age, closed pull requests, missing
transcripts, or the absence of a matching path in another provider's inventory.

## Claude and other agents

Apply the same rule to Claude-managed or tool-managed paths: prefer the owning
product's inventory and cleanup lifecycle. An unavailable or ambiguous owner is
`HOLD`. Transcript search is supporting evidence only unless the provider has a
documented structured path binding comparable to Codex's `cwd` metadata.

## Human-created worktrees

A worktree outside a recognized provider path may be human-created, but location
is not proof. Ask when ownership is ambiguous. A confirmed manual worktree can
become `REVIEW` only after the Git and process audit is complete and its state is
recoverable.
