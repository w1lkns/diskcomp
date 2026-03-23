# Phase 6: Performance - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Optimize the scan pipeline so large drives (500GB+) complete in reasonable time. The mechanism is a two-pass approach: the scanner already collects file sizes — use those to skip files that cannot be duplicates before any SHA256 hashing occurs. No new user-facing features; all existing behavior is preserved with identical output.

</domain>

<decisions>
## Implementation Decisions

### Size Filter Scope
- **D-01:** Filter is **cross-drive only** — a file is a hashing candidate only if the OTHER drive has at least one file of the same byte size. Files with a size that appears on one drive only are skipped entirely. This is the most aggressive speedup path and matches the two-drive use case precisely.
- **D-02:** The existing `min_size_bytes=1024` (1KB) floor is retained. Files below 1KB continue to be excluded before the size filter is applied — no change to scanner behavior.

### Two-Pass Progress UI
- **D-03:** After the scan completes and before hashing begins, print a single status line:
  `Size filter: {total_scanned} files → {candidate_count} candidates ({pct_skipped}% skipped)`
  This line uses the existing ANSI/Rich output pattern — no new UI component needed.
- **D-04:** The hash progress bar label changes from "files done / total files" to **"candidates"** — e.g., `Hashing 1,203 / 1,203 candidates`. This prevents confusion when users see a small hash count on a large drive.

### Benchmark Validation
- **D-05:** Speedup is validated by a **test fixture** in `tests/test_performance.py`. The test builds a synthetic directory structure with a known low duplicate rate (<10%), runs both single-pass and two-pass approaches, and asserts ≥5× speedup.
- **D-06:** The benchmark test is **opt-in** — decorated with `@unittest.skipUnless(os.environ.get('RUN_SLOW_TESTS'), 'slow')` (or equivalent). It does not run in CI on every push. Developers run it explicitly before a release with `RUN_SLOW_TESTS=1 python -m unittest`.

### Claude's Discretion
- Where the size-filtering logic lives (new module vs helper in hasher.py vs utility function) — Claude decides based on the existing architecture
- Exact variable/method naming for the two-pass approach
- Whether to expose `size_filter_stats` as a return value or just print inline

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core pipeline files
- `diskcomp/scanner.py` — `FileScanner.scan()` already collects `size_bytes` per `FileRecord`; this is the data the size filter uses
- `diskcomp/hasher.py` — `FileHasher.hash_files()` accepts `List[FileRecord]`; the filtered list is passed here
- `diskcomp/cli.py` — wiring point where scan results flow into hasher; size filter logic plugs in between
- `diskcomp/ui.py` — `UIHandler` factory; status line and progress bar updates go through here
- `diskcomp/types.py` — `FileRecord` dataclass (has `size_bytes`, `hash`, `error` fields)

### Requirements
- `.planning/ROADMAP.md` §Phase 6 — success criteria (two-pass, ≥5× speedup, identical results, UI update)

### No external specs — requirements fully captured in decisions above

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FileScanner.scan()` — already returns `ScanResult` with all `FileRecord.size_bytes` populated; no scanner changes needed for size collection
- `FileHasher.hash_files(records, on_file_hashed)` — accepts a list; passing the filtered sublist is the only change needed
- `UIHandler` / `RichProgressUI` / `ANSIProgressUI` — existing factory pattern; the status line can use the same print/console pattern as current output
- `on_file_hashed` callback — already carries `(current_index, total, speed_mbps, eta_secs)`; total will now be `len(candidates)` not `len(all_files)`

### Established Patterns
- Zero mandatory dependencies — size filtering must use stdlib only (dict grouping by int)
- `@dataclass` contracts in `types.py` — any new stats struct should follow this pattern
- Graceful error handling — never crash; filtering logic should handle empty candidate lists
- Python 3.8+ — no walrus operator, no `dict | dict` merge syntax

### Integration Points
- `cli.py` `main()` — between `scanner.scan()` return and `hasher.hash_files()` call; this is where the size filter runs
- Progress output — the status line prints after scan completes and before `hash_files()` is called
- `on_file_hashed` total parameter — must be updated to `len(candidates)` so ETA and progress bar are accurate

</code_context>

<specifics>
## Specific Ideas

- Status line format approved: `Size filter: 8,412 files → 1,203 candidates (86% skipped)`
- Hash progress bar label: `Hashing {done} / {total} candidates`
- Benchmark env var: `RUN_SLOW_TESTS=1`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-performance*
*Context gathered: 2026-03-23*
