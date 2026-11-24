## Interloop

This project uses interloop for cross-session context continuity.

**At session start:** Read `.interloop/decisions.md` before beginning any work. Decisions made in prior interloop sessions live there and should inform your approach.

**Before complex multi-file changes:** Append a brief reasoning note to `.interloop/breadcrumbs.md` using this format:
```
## HH:MM — [topic]
[What you're about to do / approach you're taking / what you're uncertain about]
```

Commit hooks capture post-commit summaries automatically. Your pre-commit notes capture the WHY before it happens — this is the context that survives compaction.
