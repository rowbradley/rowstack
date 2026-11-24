# rowstack

A small collection of standalone agent skills for Claude Code and Codex.

## Install

### Claude Code

```text
/plugin marketplace add rowbradley/rowstack
/plugin install rowstack
```

### Codex

Clone the repository and copy or symlink the skills you want into `$CODEX_HOME/skills/` (default `~/.codex/skills/`):

```bash
git clone https://github.com/rowbradley/rowstack.git
ln -s "$PWD/rowstack/skills/"* "${CODEX_HOME:-$HOME/.codex}/skills/"
```

You can also load the repository directly as a local Codex plugin using `.codex-plugin/plugin.json`.

## Skills

| Skill | What it does | When to use it |
|---|---|---|
| `blind-paste` | Collects API keys, tokens, and one-time codes without exposing values to the model or shell history. | Missing local env credentials, interactive CLI login codes, or Claude setup tokens. |
| `worktree-hygiene` | Audits Git worktrees, local state, processes, and provider ownership before proposing safe removal. | Inspecting, tidying, or safely removing stale or numerous Git worktrees. |
| `implementation-brief` | Adds baseline pinning, mismatch gates, and explicit propagation rules to handoff plans. | Writing or reviewing a plan another agent will execute without conversation context. |
| `planning` | Builds minimal, verifiable implementation plans with a cross-model simplification pass. | Non-trivial, multi-phase, multi-PR, or delegated work with non-obvious scope or ownership. |
| `conveying-information` | Structures and audits data decks, readouts, and reports so the first pass stands alone. | Creating, simplifying, or reviewing findings docs or slides for a product or leadership audience. |
| `visualize-data` | Guides chart selection, encoding, uncertainty display, and visual verification across surfaces. | Choosing, building, or checking quantitative charts for answers, reports, or exported figures. |
| `interloop` | Pairs a coding agent's commit hooks with a second-terminal conversational PM loop for decisions. | Running a coding agent in one terminal while capturing decisions and resolving ambiguities in another. |
| `wave` | Runs three parallel web searches and fetches to produce a compact, source-backed summary. | Quick factual lookups, comparisons, prices, or pre-meeting briefs that do not need deep research. |
