# Phase 6: Performance - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 06-performance
**Areas discussed:** Size-filter scope, Two-pass UI, Benchmark validation

---

## Size-Filter Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Cross-drive only | Hash a file only if the OTHER drive has a file of the same byte size. Most aggressive speedup — ~90%+ of files skipped on real-world drives. Matches two-drive use case precisely. | ✓ |
| Combined pool | Group all files from both drives; hash any file whose size appears ≥2 times in the combined pool. Simpler, but hashes same-drive size matches too. | |

**User's choice:** Cross-drive only
**Notes:** None

---

### Size threshold follow-up

| Option | Description | Selected |
|--------|-------------|----------|
| Keep existing 1KB floor | Retain min_size_bytes=1024; files below 1KB continue to be excluded before filtering. | ✓ |
| Hash everything ≥1 byte | Drop the floor; let size filter do all the work. | |

**User's choice:** Keep existing 1KB floor
**Notes:** None

---

## Two-Pass UI

| Option | Description | Selected |
|--------|-------------|----------|
| Brief status line | After scanning, print a single line: "Size filter: N files → M candidates (X% skipped)" then start hash bar. | ✓ |
| No visible change | Size filtering happens silently inside the hasher — user just sees a smaller hash count. | |
| Separate progress phase | Add a dedicated "Filtering..." indicator before hashing. | |

**User's choice:** Brief status line
**Notes:** Approved format: `Size filter: 8,412 files → 1,203 candidates (86% skipped)`

---

### Hash bar label follow-up

| Option | Description | Selected |
|--------|-------------|----------|
| Show candidates label | Change label to "Hashing 1,203 / 1,203 candidates" so smaller number doesn't confuse users. | ✓ |
| Keep current label | Keep "files done / total" as-is. | |

**User's choice:** Show candidates label
**Notes:** None

---

## Benchmark Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Test fixture | Add tests/test_performance.py with synthetic drive fixture, assert ≥5× speedup. Lives in CI, reproducible. | ✓ |
| --benchmark flag | Add user-facing flag that compares approaches on real drives. | |
| Manual / documented only | No automated validation. | |

**User's choice:** Test fixture
**Notes:** None

---

### Benchmark CI follow-up

| Option | Description | Selected |
|--------|-------------|----------|
| Optional / @slow tag | Skipped unless RUN_SLOW_TESTS=1. Developer runs explicitly before release. | ✓ |
| Always in CI | Runs on every push. | |

**User's choice:** Optional / @slow tag
**Notes:** Env var: `RUN_SLOW_TESTS=1`

---

## Claude's Discretion

- Where the size-filtering logic lives (new module vs helper function)
- Exact variable/method naming for two-pass approach
- Whether to expose `size_filter_stats` as a return value or just print inline

## Deferred Ideas

None.
