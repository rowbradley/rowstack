---
name: implementation-brief
description: Use when writing or reviewing an implementation plan, brief, or task handoff that a different agent will execute without the current conversation context, or when an implementer reports a mismatch, blocker, or completion claim against a brief. Apply it together with the Planning skill.
---

# Implementation Brief

A brief is a plan that must survive an implementer who has none of your context and cannot ask you questions mid-task. Planning owns goal alignment, decomposition, execution shape, and proving checks. This skill adds the constraints a context-free handoff needs. Every requirement below exists because its absence produced a real failure; the reason is stated so you can judge edge cases instead of following rules blindly.

## Writing the brief

**1. Pin the baseline, verify every claim against it.**
Name the exact ref/SHA the implementer starts from. Every statement about current code carries a file:line reference verified *in this session against that ref* (`git show <ref>:<path>`), never from memory or an earlier session. Check that your local checkout matches the ref before reading anything. A stale checkout produces confident wrong baselines, and one wrong baseline claim poisons every task built on it. If origin moved since you audited, re-verify the seams that changed before writing.

**2. Open with a global constraints block.**
Everything the implementer cannot infer and must not violate: gates to run per commit, commit-message rules, mirrored files that must stay identical, spec/docs that must move with schema changes, ledger obligations, spend caps for live or paid calls. State each once here; every task implicitly includes them. Constraints scattered through tasks get skipped by an implementer executing tasks out of order.

**3. Include the mismatch gate, verbatim.**
"When this plan and the live code disagree, stop and report; do not improvise around a mismatch." This one sentence converts silent drift into clean stop-reports. A context-free implementer who hits a discrepancy has exactly two options: guess or stop. The gate makes stopping the instructed path, and a good implementer will use it.

**4. Name exact task mechanics and interfaces.**
Each task names its exact files, observable behavior, and proving command or check. Later tasks reference only names, signatures, and types defined in earlier tasks' Produces blocks. The implementer may see one task at a time; these details are how neighboring tasks agree.

**5. Carry a complexity ledger.**
State deletions alongside additions. A brief that only adds to the touched cluster must say why the cluster earns growth. This is what makes "simpler" checkable in review instead of a vibe.

**6. Defer hardening behind named triggers.**
Every protection you consciously chose NOT to build gets one line: what it guards, and the observable failure that would earn it. Without this list, the next session re-proposes the armor; with it, the decision is durable.

**7. Make every protection red-capable.**
Each test or check the brief asserts must include the step that proves it can fail (delete the guarded line, watch the test fail, restore). A protection never seen red is a hope, not a check.

**8. Cap live, paid, and externally stateful steps.**
Hard call budgets, stop-on-first-miss, and artifact paths for evidence. An implementer without caps will reroll a flaky live step until it passes.

**9. Spell out propagation, never say "automatically."**
When a change must ripple (schema → tool declaration → prompt → docs → QA fixtures), name each file and the invariant that enforces it. "The drift checks adjust automatically" is exactly the kind of claim implementers falsify. If you can't name the enforcing test at file:line, verify it before writing it.

## Reviewing the implementer's reports

When the implementer stops on a mismatch or claims completion:

- **Verify the key claim yourself** at file:line before accepting or rejecting it. Implementer reports are claims, not results, including "everything is green." The most valuable stop-reports are the ones that contradict your brief; treat them as review findings on the plan, not as noise.
- **Amend the plan file, not just the chat.** The implementer executes the file; a correction that lives only in conversation is invisible to a resumed or fresh session.
- **Scope re-review to the interdiff** after a fix round; a full re-review is earned only by a new high-risk seam, not by the passage of a round.

## Anti-patterns

- "Similar to Task N." Repeat the content; the implementer may read tasks out of order.
- Baseline claims from memory, or from a checkout you didn't confirm matches the pinned ref.
- "Handled automatically" for any cross-file propagation you did not verify.
- A brief with no deletion list touching a cluster that already has duplication.
- Hardening for failures nobody has observed, without a named trigger to defer it behind.
- Unbounded live steps ("retry until it works") in paid or stateful territory.
