# Roadmap

diskcomp is actively developed with a focus on user feedback and real-world usage patterns. Here's what's planned:

## 🎯 Current Status: v1.0.2 (March 2026)

✅ **Core functionality complete**: Safe duplicate detection and deletion  
✅ **Cross-platform support**: macOS, Linux, Windows  
✅ **Multiple interfaces**: Interactive CLI, scripted mode, direct flags  
✅ **Safety features**: Undo logs, dry-run, read-only detection  
✅ **Performance optimized**: Two-pass scanning (5× faster on typical drives)  
✅ **Professional distribution**: PyPI package, automated CI/CD  
✅ **User experience fixes**: Clean drive picker interface (v1.0.1) — *Linux only, macOS still broken*  
✅ **Deletion workflow fixes**: Interactive mode parameter bug (v1.0.2)  

---

## 🚀 Next Up: Solidify Foundation (v1.1-1.2)

### Critical UX Fixes
- [ ] **Fix drive picker for macOS single-drive mode** — *Still showing 8+ system volumes (/, /System/Volumes/VM, etc.) instead of user-friendly drives*
- [ ] **Add `--version` flag** (missing basic CLI feature) — *Issue #2*
- [ ] **Fix Linux binary builds** (CI permissions issue)

### User Experience Polish
- [ ] **Progress indicators for long operations** (drive detection, large scans, deep directory traversal)
- [ ] **Loading states with context** ("Scanning drives...", "Analyzing 50,000 files...", "Hashing candidates...")
- [ ] **Better cancellation feedback** (show what's stopping when user hits Ctrl+C)
- [ ] **Homebrew formula** (`brew install diskcomp`) — *Planned but not implemented*
- [ ] **GUI version** (PyQt/tkinter for less technical users)
- [ ] **Better error messages** (actionable guidance when things fail)
- [ ] **Progress persistence** (resume interrupted scans)
- [ ] **Config files** (save preferences between runs)

### Technical Improvements
- [ ] **Windows compatibility testing** (ensure all features work)
- [ ] **Large dataset performance testing** (>100K files)
- [ ] **Drive detection reliability** (handle USB disconnects, network timeouts)

*Target: 2-3 months • Based on user feedback and reported issues*

---

## 📈 Growth Phase: Advanced Features (v1.3-1.5)

### Power User Features
- [ ] **Regex filename filters** (`--include "*.jpg"`, `--exclude "backup*"`)
- [ ] **Size range filters** (`--larger-than 1GB`, `--between 10MB-100MB`)
- [ ] **Network drive support** (SMB, NFS mounts)
- [ ] **Advanced reporting** (HTML reports, duplicate size charts)

### Performance & Scale
- [ ] **Parallel hashing** (multi-core CPU usage)
- [ ] **Smart caching** (remember hashes between runs)
- [ ] **Incremental scanning** (only check changed files)
- [ ] **Memory optimization** (handle massive directories efficiently)

### Distribution & Installation
- [ ] **Homebrew formula** (`brew install diskcomp`)
- [ ] **Debian packages** (`apt install diskcomp`)
- [ ] **Chocolatey package** (`choco install diskcomp`)
- [ ] **Standalone binaries** (no Python required)

*Target: 4-6 months • Priority based on download stats and feature requests*

---

## 🌟 Mature Platform: Ecosystem (v2.0+)

### Integration & Automation
- [ ] **Plugin system** (custom duplicate detection logic)
- [ ] **Cloud storage support** (Google Drive, Dropbox, OneDrive APIs)
- [ ] **Backup tool integration** (rsync, rclone, Time Machine hooks)
- [ ] **Scheduled scanning** (cron/systemd integration, automated reports)

### Community & Ecosystem  
- [ ] **Web interface** (browser-based GUI for remote servers)
- [ ] **Docker container** (containerized scanning for CI/CD)
- [ ] **API endpoints** (HTTP API for integration with other tools)
- [ ] **Community plugins** (marketplace for custom filters/reports)

*Target: 6+ months • Depends on adoption and contributor interest*

---

## 📊 Success Metrics We Track

- **PyPI downloads per month** (adoption growth)
- **GitHub stars and issues** (community engagement)  
- **User-reported bugs** (stability and reliability)
- **Performance benchmarks** (speed on large datasets)
- **Platform compatibility** (macOS/Linux/Windows feature parity)

---

## 🤝 Contributing to the Roadmap

**Found a bug?** [Open an issue](https://github.com/w1lkns/diskcomp/issues/new)  
**Want a feature?** [Start a discussion](https://github.com/w1lkns/diskcomp/discussions)  
**Ready to code?** Check out issues labeled [`good first issue`](https://github.com/w1lkns/diskcomp/labels/good%20first%20issue)

**Priority is driven by:**
1. **Safety and reliability** (bugs always come first)
2. **User feedback** (what people actually request)
3. **Download patterns** (what features get used)
4. **Contributor interest** (what people want to build)

---

## 📅 Release Schedule

- **Patch releases** (1.0.x): Bug fixes, minor features → 2-4 weeks
- **Minor releases** (1.x.0): New features, performance improvements → 2-3 months  
- **Major releases** (x.0.0): Breaking changes, architectural improvements → 6+ months

**Current focus: v1.1** with macOS drive picker fix, Homebrew support, and progress indicators.

---

*Roadmap last updated: March 25, 2026*  
*Next review: May 2026*