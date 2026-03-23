# Phase 7: UX Polish + Single-Drive Mode - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 07-ux-polish-single-drive-mode
**Areas discussed:** Single-drive keep rule, Startup banner tagline, --min-size edge cases, Wizard Help option

---

## Single-Drive Keep Rule

| Option | Description | Selected |
|--------|-------------|----------|
| Alphabetically first path | Lexicographically smallest path survives. Deterministic, reproducible, no extra I/O. | ✓ |
| Oldest file (earliest mtime) | Oldest copy treated as original. mtime can be unreliable after copies/moves. | |
| Shallowest path (fewest slashes) | Copy closest to drive root survives. | |
| User picks per group (interactive only) | Show all paths, ask user which to keep. Safest but slow. | |

**User's choice:** Alphabetically first path
**Notes:** None

---

## Startup Banner Tagline

| Option | Description | Selected |
|--------|-------------|----------|
| Find duplicates. Free space. Stay safe. | Direct, feature-focused. 6 words. | ✓ |
| Compare drives. Kill duplicates. | Punchy, memorable. | |
| Safe duplicate finder for external drives. | Clear, specific, safety-first. | |

**User's choice:** "Find duplicates. Free space. Stay safe."
**Notes:** None

---

## --min-size Edge Cases

| Option | Description | Selected |
|--------|-------------|----------|
| KB/MB/GB + plain bytes, error on bad CLI input | Case-insensitive suffix (500KB, 10mb, 1GB) or plain int (bytes). Error+exit on bad CLI flag. Retry loop in interactive wizard. | ✓ |
| KB/MB/GB only, silently use 1KB on bad input | Simpler parser. Silent fallback. | |
| KB/MB/GB only, error on bad input | Suffixed values only, rejects plain ints. | |

**User's choice:** Option 1 (KB/MB/GB + plain bytes, error on bad CLI input)
**Notes:** User wants case-insensitive parsing. In the interactive wizard, bad input should trigger a retry prompt rather than exiting.

---

## Wizard 'Help' Option

| Option | Description | Selected |
|--------|-------------|----------|
| Wizard-style quick guide | Short plain-English summary: what diskcomp does, 2 modes, 3 safety facts. Returns to main menu after. | ✓ |
| Full --help text | Standard argparse --help output, then exit. | |
| Link to README + brief summary | 2-line summary + GitHub URL. Returns to main menu. | |

**User's choice:** Wizard-style quick guide
**Notes:** Returns to main menu after displaying help.

---

## Claude's Discretion

- Exact ASCII art rendering method (textwrap vs hardcoded)
- Internal module structure for wizard logic (new wizard.py vs inline in cli.py)
- Exact wording of wizard quick guide help text
- Unit test structure for single-drive dedup

## Deferred Ideas

None.
