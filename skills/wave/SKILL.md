---
name: wave
description: Quick, source-backed web research (~60s) for current facts, recommendations, comparisons, reviews, prices, citations, links, and pre-meeting briefs. Skip local file/code searches, private data, and deep research.
---

# Searchwave

Quick web research synthesis in ~60 seconds.

## Overview

Single orchestrator, 3 parallel searches, 3 parallel fetches. Produces a
300-400 word summary with sources. No questions asked — receives topic and
runs immediately.

## When to Use

**Use `wave` when:**
- User asks for "quick lookup" or "fast research"
- Need context before a meeting or decision
- Simple factual questions, comparisons, prices, or citations
- Time-sensitive requests

**Skip `wave` when:**
- Local file or codebase searches are what is needed
- Complex topics require deep multi-angle synthesis, confidence scoring, or
  exhaustive source evaluation
- Sources are heavily JS-rendered SPAs where standard web fetch returns empty
  shells (use a browser tool instead)

## Execution

**Complete in 60 seconds. Dense facts, not fluff.**

### Step 0: Print banner

Print this banner immediately:
```
╔═════════════════════════════════════════╗
║           S E A R C H W A V E           ║
║                · · · · ·                ║
║      Searching: 3 parallel queries      ║
╚═════════════════════════════════════════╝
```

### Step 1: Search (3 parallel)

Fire 3 parallel web searches in ONE turn:
```
"[topic]"              → baseline
"[topic] interesting"  → non-obvious angles
"[topic] guide"        → actionable content
```

Exclude `medium.com` when your search tool supports domain filtering (for
example, `blocked_domains: ["medium.com"]`) — Medium rarely fetches cleanly.

### Step 2: Curate (10 sec)

Pick 3 URLs. Prefer: gov/institutional, domain authorities, quality blogs.

Skip for fetching:
- Wikipedia (often returns 403 — use the snippet from search results instead)
- Medium (rarely fetches cleanly)
- Paywalled sites
- SEO farms, outdated content

### Step 3: Fetch (3 parallel)

Fire 3 parallel web fetches in ONE turn. Proceed with available results if any
fail.

### Step 4: Write

**Adapt structure to topic. No rigid template.**

Always include:
- **Overview** — 2-3 sentences, plain language
- **Key Findings** — Specific numbers, names, thresholds. This is the meat.
- **Sources** — With one-line descriptions

Include ONLY if warranted:
- **Practical Takeaways** — If topic has actionable advice
- **Of Interest** — ONLY if genuinely surprising. Skip if straightforward.
- **Go Deeper?** — ONLY if topic clearly warrants more research

**Style:**
- Concrete > abstract
- Numbers > vague claims
- Useful > clever
- Skip sections that don't add value
- ASCII tables/diagrams when helpful for comparisons
- No --- dividers between sections
- Tight, scannable organization
- Inline citations for statistics: "According to X...", "One study found..."

**Avoid AI writing patterns:**
- No dramatic reframes or hyperbole
- Let facts speak; don't editorialize
- Be concise, lead with numbers

**Line width formatting (for terminal readability):**
- Prose paragraphs: hard-wrap at 80 columns
- Bullet lists: hard-wrap at 80 columns
- Tables: NO width limit (columns break if wrapped)
- Code blocks: NO width limit
- ASCII diagrams: NO width limit

**User override:** If the user asks to "ignore the wrapping rule" or similar,
skip all hard-wrapping for the rest of the session (or until they say otherwise).

End with: `*Searchwave · [N] sources*` (where N is the number of sources fetched)
