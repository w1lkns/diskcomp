---
phase: 2
slug: terminal-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | unittest (stdlib) |
| **Config file** | none — stdlib, no config needed |
| **Quick run command** | `python3 -m unittest discover tests/ -v` |
| **Full suite command** | `python3 -m unittest discover tests/ -v` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m unittest discover tests/ -v`
- **After every plan wave:** Run `python3 -m unittest discover tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | UI-01, UI-03 | unit | `python3 -m unittest tests.test_ui -v` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | UI-02, UI-04 | unit | `python3 -m unittest tests.test_ui -v` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 2 | UI-01, UI-02 | integration | `python3 -m unittest tests.test_ui_integration -v` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 2 | UI-05 | unit | `python3 -m unittest tests.test_ui -v` | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 3 | UI-03, UI-04 | integration | `python3 -m unittest discover tests/ -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ui.py` — unit tests for RichProgressUI and ANSIProgressUI (stubs for UI-01–05)
- [ ] `tests/test_ui_integration.py` — integration tests for scanner + hasher callback hooks

*Existing infrastructure (tests/test_scanner.py, tests/test_hasher.py, tests/test_reporter.py) covers non-UI behavior.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live progress bar updates in real terminal | UI-02 | Can't assert terminal animation in unit tests | Run `python3 -m diskcomp --keep /tmp/A --other /tmp/B` and visually confirm MB/s + ETA appear |
| Windows cmd.exe renders without garbled chars | UI-04 | No Windows CI environment available | Test on Windows 10+ cmd.exe: run diskcomp, confirm no `ESC[` literals appear |
| Summary banner alignment in narrow terminal | UI-05 | Layout depends on terminal width | Resize terminal to 60 cols, run diskcomp, confirm banner doesn't overflow |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
