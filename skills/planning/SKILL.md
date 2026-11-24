---
name: planning
description: Create decision-ready implementation plans for non-trivial, multi-phase, multi-PR, or delegated work with goal alignment and cross-model simplification. Use when asked for an implementation plan or when scope, dependencies, or ownership are non-obvious. Skip simple reversible work.
---

# Planning

Produce the smallest implementation plan that fully delivers the user's outcome.
Planning itself is read-only. It does not revoke execution authority the user
already granted.

## Keep authority in one place

- The applicable runtime and project instructions own authorization, worker
  counts, model routing, worker briefs, write isolation, execution review
  limits, and final acceptance.
- Dedicated roadmap documents or issue trackers own long-term project roadmaps
  and shared planning state.
- Targeted evidence checks own validation of consequential assumptions and
  option choices. Cross-model agreement is review evidence, not factual proof.
- Implementation Brief owns extra constraints for a plan that a different agent
  will execute without the current conversation context.
- This skill owns the implementation plan, delegation map, and its single
  cross-model minimization pass.

Write the plan in chat. Create a durable plan only when the user explicitly
requests one. Do not create a new log, tracker, decision store, or orchestration
system.

## Decide whether a full plan earns its cost

Use the full workflow when the work has at least one of these properties:

- multiple phases, owners, pull requests, or sessions;
- a consequential product or architecture choice;
- plan-changing uncertainty about behavior, ownership, or dependencies;
- requested subagent delegation whose boundaries need design.

For obvious, reversible, single-owner work, give a brief approach and the
proving check. State that a full plan would add no useful decision support.
An explicit request to use this skill always uses the full workflow.

Every full plan gets one cross-model minimization review. The entry decision is
the complexity gate; do not add a second review threshold inside the workflow.

## Build the plan

### 1. Frame the goal

State the user-visible, engineering, or operational outcome. Define the first
usable checkpoint and a checkable completion condition. Record constraints and
the authorization boundary.

Use this evidence order for goals:

1. The user's request and acceptance criteria.
2. Authoritative product documents, tickets, decisions, or ADRs.
3. Current behavior, ownership, and sources of truth.
4. Established repository conventions.

Classify each goal:

| Goal status | Action |
|---|---|
| Explicit | Use directly. |
| Supported inference | Use it and cite the evidence. |
| Weak inference with a reversible consequence | Choose the smallest reversible default and disclose it. |
| Weak inference with a material consequence | Ask the operator before settling the plan. |

A consequence is material when it changes product behavior, a public contract,
priority, cost, scope, hard-to-reverse architecture, or external state. Ask only
when the choice cannot be settled from accessible evidence or a cheap reversible
probe. If alignment is required, present the evidence and the exact decision it
changes, then stop before decomposition.

### 2. Resolve plan-changing unknowns

Inspect current ownership, boundaries, sources of truth, prior decisions, and
the behavior the plan will change. Name only unknowns that could alter the
direction or unit boundaries.

Use the cheapest useful read or reversible probe. Run a targeted evidence check
before committing when a consequential assumption or option choice is uncertain.
If ownership or causation is unclear, make diagnosis the first checkpoint
instead of planning a speculative fix.

### 3. Decompose into verifiable units

Each unit must have:

- one observable outcome;
- one owner;
- bounded scope;
- explicit dependencies;
- proof that its outcome exists.

Order units by dependency and decision value while preserving the first usable
checkpoint. Prefer units that can be verified and landed independently. Do not
invent phases, pull requests, abstractions, or artifacts that do not change an
owner, dependency, outcome, or proving check.

### 4. Choose the execution shape

- Use one owner for sequential, context-heavy, same-file, or shared-state work.
- Use parallel slices for genuinely independent seams.
- Use a competitive race only when several credible approaches remain and the
  selection rubric is written before spawning.
- Use a mixed shape only when distinct slices and a real option race both exist.

Use a pilot unit before large fan-out only when the workflow, verification
recipe, or repeated unit contract is novel or expensive to get wrong. Reuse the
applicable runtime and project instructions for worker briefs and model
selection rather than copying those policies into the plan.

### 5. Run the cross-model minimization review

Before presenting a full plan, request one read-only peer review from a reviewer
in a different model family from the lead's. The runtime's configured peer
tooling decides the concrete peer.

Give the peer the explicit goals, supported inferences and their evidence,
constraints, plan-changing unknowns, and draft plan. Keep the request
artifact-focused and compact:

> Return the smallest plan that still meets the evidenced goals. Every phase,
> artifact, role, handoff, stored record, review, and check must point to an
> acceptance criterion or a material product, correctness, security, privacy,
> contract, data-integrity, or operational risk. Remove or merge it otherwise.
> Prefer an existing owner, boundary, source of truth, check, or tool over a new
> mechanism. Identify inferred goals that require operator alignment. Add an
> element only for a named missing criterion or material risk.

Ask the peer to return only:

- `SURVIVES`, `REVISED`, or `NEEDS ALIGNMENT`;
- the rewritten plan;
- what it removed or merged;
- any addition and the criterion or risk requiring it;
- operator decisions still needed.

Judge the review rather than accepting it automatically. Reject additions that
lack a named requirement or material risk. Repeat the review only when it finds
a strategy-changing blocker.

If the peer call fails, follow the active runtime's failure and retry rules.
A peer timeout ends that delegation for the milestone; do not automatically
retry, extend its window, or switch models. If peer coverage is unavailable,
state that gap and continue safe, authorized work unless the missing review
gates a consequential decision. Never label local self-review as cross-model
validation.

### 6. Present, then continue or stop

Lead with the outcome and first usable checkpoint. Then show:

- explicit goals, supported inferences, reversible defaults, and any operator
  decisions;
- ordered units with owner, dependency, outcome, and proof;
- the execution shape and why it earns its coordination cost;
- the cross-model verdict and the concrete removals, merges, or justified
  additions it caused;
- the current authorization boundary and any operator decision needed before
  execution.

Use six structural fields: **Goal, Checkpoint, Unit, Owner, Dependency, Proof**.
Constraints and evidence are inputs to those fields. Any other plan construct
must identify the requirement or material risk that earns its place.

When another agent will execute the plan without the current conversation
context, apply `implementation-brief` before presenting it.

If the user asked only for a plan, stop after presenting it. If execution was
already authorized, continue unless the plan exposes a material change in
scope, product behavior, risk, cost, architecture, or external-state impact
that requires a new operator decision.
