# Phase 5: Packaging + Distribution - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-22
**Phase:** 05 — Packaging + Distribution

---

## Area 1: Single-File Bundling

**Q:** How should diskcomp.py (the zero-dep single-file version) be created and maintained?

| Option | Description |
|--------|-------------|
| ✅ **Build script** | `build_single.py` concatenates all modules at release time. Package is canonical, single-file is generated. |
| Manual copy | diskcomp.py maintained by hand — risks drift |
| zipapp / shiv | Bundle as zip executable — no concatenation but larger file |

**Selected:** Build script (Recommended)

---

## Area 2: CI Scope

**Q:** What should GitHub Actions CI do?

| Option | Description |
|--------|-------------|
| ✅ **Tests + matrix** | macOS, Linux, Windows × Python 3.8–3.12. No publish step. |
| Tests + auto-publish | Matrix + PyPI publish on version tag |
| Tests only (no matrix) | ubuntu-latest / Python 3.11 only |

**Selected:** Tests + matrix (Recommended)

---

## Area 3: README Format

**Q:** What style of README for the public release?

| Option | Description |
|--------|-------------|
| ✅ **Practical + badges** | Install, usage, flags, safety model, CI/PyPI badges. No recordings. |
| Full showcase | Same + asciinema terminal recording |
| Minimal | Just install + one example |

**Selected:** Practical + badges (Recommended)

---

## Area 4: PyPI Publishing

**Q:** When should diskcomp actually land on PyPI?

| Option | Description |
|--------|-------------|
| ✅ **Not yet — machinery only** | pyproject.toml + build script + CI ready, but no publish |
| Test PyPI now | Publish to test.pypi.org to validate pipeline |
| Real PyPI now | Ship v0.1.0 to PyPI live |

**Selected:** Not yet — machinery only (Recommended)
