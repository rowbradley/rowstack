---
name: worktree-hygiene
description: Audit and safely close Git worktree lanes without losing resumable agent tasks, uncommitted or ignored files, unique commits, active processes, or provider-managed state. Use whenever the user asks to inspect, tidy, prune, remove, or reason about stale, abandoned, old, or numerous worktrees and their owning tasks.
---

# Worktree Hygiene

Treat worktree cleanup as an ownership and recoverability decision, not a disk
cleanup shortcut. A clean Git status or merged commit is not enough to remove a
worktree: an agent task may still resume there, ignored files may be the only
copy, or a process may still use the directory.

The goal is a closed work lane, not merely an absent directory. Establish what
happened to the work and what remains recoverable before proposing cleanup.

## Permission boundary

A broad request such as "do worktree hygiene," "clean up old worktrees," or
"remove stale ones" authorizes an audit and a proposed cleanup only. It does not
authorize removal.

Before any removal, show the user the exact worktree path and repository, owner
or task state, branch and HEAD, local state including ignored files, active
operations and processes, proposed mechanism, practical effect, and recovery
consequence. Remove only the exact targets the user approves after seeing that
preview. If any of those facts changes, stop and show a new preview.

Never infer permission to:

- delete a branch or ref;
- use `--force`, `rm -rf`, or another filesystem bypass;
- change global Git or GitHub authentication;
- clean caches, simulators, containers, or other non-worktree state;
- remove a provider-managed worktree through raw Git when ownership is unclear.

## Audit

1. Resolve the repository and requested scope. Do not widen one repository into
   a machine-wide cleanup without saying so.
2. Run the bundled read-only auditor from the repository root:

   ```bash
   python3 <skill-dir>/scripts/audit_worktrees.py --repository "$PWD"
   ```

   Use `--json` when structured output will make comparison safer. The helper
   reports evidence only. It never decides that removal is allowed. Its default
   output keeps file names private.
3. Resolve provider ownership using
   [provider-ownership.md](references/provider-ownership.md). Check the owning
   product before reading transcript content.
4. For every candidate, account for:
   - tracked, staged, untracked, and ignored changes;
   - branch/ref retention and whether HEAD is reachable from a discovered base;
   - detached or unique commits;
   - locked or prunable registry state;
   - submodules and nested repositories;
   - merge, rebase, cherry-pick, revert, bisect, or sequencer state;
   - processes whose working directory is inside the worktree, or a stated
     process-visibility gap;
   - active, pinned, interrupted, resumable, or otherwise retained agent tasks.

Do not inspect file contents to make the decision. Report counts and state. If a
file's meaning matters, ask before opening it. Never print secrets from ignored
environment files, databases, or tool state.

## Classify the owning work lane

Give every lane one outcome label before classifying its worktree:

- `ACTIVE` means the work is intentionally continuing or still has unresolved
  changes, tasks, processes, or decisions.
- `LANDED` means the requested outcome is complete and every intended change is
  present in its target. A completed diagnostic with no product change can also
  be `LANDED` when its result was delivered.
- `SUPERSEDED` means another lane or decision replaced this one. Prove where the
  intended tracked work went, and account for ignored local state separately.
- `PARKED` means the work was intentionally deferred. Name the retained ref or
  artifact and the condition that would resume it.
- `DROPPED_BY_DECISION` means the user explicitly chose not to continue it.
  Record the decision and which refs or artifacts remain.

Never infer `SUPERSEDED`, `PARKED`, or `DROPPED_BY_DECISION` from age,
interruption, inactivity, or a clean worktree. Keep the lane outcome separate
from the worktree safety label below. A non-active lane is not closed until its
task state, local files, worktree, and retained or deleted refs each have an
explicit terminal action.

## Classify each worktree

Use exactly these labels:

- `HOLD` — removal is unsafe or ownership/recoverability is unresolved. This
  includes active or resumable tasks, active processes or Git operations, any
  tracked, staged, or untracked change, unresolved ignored-only state, unique
  commits without a proven recovery path, locked worktrees, nested repositories
  needing separate review, and unknown ownership under a managed provider path.
- `NATIVE_CLEANUP` — the owning product has identified an inactive managed
  worktree and provides its own cleanup lifecycle. Recommend that lifecycle;
  do not substitute raw Git removal.
- `REVIEW` — evidence supports proposing removal, but explicit target approval
  is still required.
- `REMOVE_APPROVED` — an ephemeral execution label applied only after the user
  approves the exact, current preview. Never persist or reuse it.

Reachability, age, a closed pull request, or a clean tracked status can support a
`REVIEW` decision but cannot produce it alone. Unknown evidence resolves to
`HOLD`, not to a guess.

Ignored entries start as unresolved. To make an ignored-only worktree
actionable, first show the count-only audit, then ask before disclosing path
names. If the user agrees, rerun with `--show-ignored-paths`. Show names only,
never contents. Move past this hold only when the user confirms every listed
path is reproducible, backed up, or otherwise disposable. Do not recognize
`node_modules`, build output, environment files, or databases automatically.

Present a compact table with one row per worktree: path, owner/task, lane
outcome, branch or detached HEAD, local state, process/operation state,
recoverability, safety label, terminal action, and reason. Separate verified
facts from inferences and visibility gaps.

## Execute an approved cleanup

Prefer the owning product's cleanup for `NATIVE_CLEANUP` candidates. Follow its
native safeguards and verify the result through both the product inventory and
Git's worktree registry.

Do not treat a task handoff, move, or checkout switch as worktree cleanup unless
the provider's contract explicitly says it removes the source directory and
registry entry. A handoff can relocate task state and change the primary
checkout while leaving the old worktree intact. If the provider has no removal
operation, close or archive the task only when the user independently requested
that lifecycle action. After ownership is resolved, the worktree may become a
manual `REVIEW` candidate. Show that manual mechanism in a fresh approval
preview rather than substituting it silently.

For an approved manual `REVIEW` candidate:

1. Rerun the audit immediately before removal.
2. Confirm the exact path, HEAD, branch/ref state, local-state counts, owner,
   process state, and operation state match the approved preview.
3. Run `git worktree remove` with the exact path and without force. Do not delete
   the branch afterward unless the user separately requests and approves it.
4. Verify the path and registry entry are absent and every promised branch/ref
   still exists. Report whether recovery is available from a retained ref.

If normal removal refuses, classify the target `HOLD` and report the reason. Do
not escalate to force or filesystem deletion.

For stale registry metadata, first run `git worktree prune --dry-run`. Show the
complete exact dry-run result and obtain approval for that unchanged set before
running `git worktree prune`. If the dry-run set changes, stop for a new preview.

## Finish

Report what was audited, what was kept and why, what native cleanup was
recommended, and what exact approved removals succeeded. State remaining
visibility gaps. For every lane, report the outcome label, terminal action,
retained refs, and whether its owning tasks remain open or were archived. Never
call cleanup complete while an approved target is unverified, a provider still
reports it as active, or the work's outcome is unknown.
