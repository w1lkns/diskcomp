---
name: Performance Issue
about: diskcomp is slow or uses too much memory/CPU
title: "[PERFORMANCE] "
labels: ["performance"]
assignees: []

---

## ⏱️ Performance Issue Description
Describe what's slow or resource-intensive.

## 📊 Environment Details
- **OS**: (macOS 14.1, Ubuntu 22.04, Windows 11, etc.)
- **diskcomp version**: (run `pip show diskcomp`)
- **Hardware**: (CPU, RAM, drive types - SSD/HDD/network)

## 📁 Dataset Information
- **Drive sizes**: (e.g., 500GB, 2TB)
- **Number of files**: (approximate - use `find /path -type f | wc -l`)
- **Average file size**: (mostly photos, documents, videos, etc.)
- **Duplicate rate**: (rough estimate - 10%, 50%, mostly unique?)

## 🐌 Performance Symptoms
- [ ] **Slow scanning** - Taking too long to find files
- [ ] **Slow hashing** - Taking too long to compute SHA256 hashes  
- [ ] **Memory usage** - Using too much RAM
- [ ] **CPU usage** - Pegging CPU for too long
- [ ] **Disk I/O** - Too much disk activity

## ⏲️ Timing Information
**How long did it take?** (e.g., "45 minutes for 100GB")  
**How long should it take?** (e.g., "other tools finish in 5 minutes")

## 🔍 Additional Context
- Are you scanning network drives?
- Any antivirus software running?
- Did you try `--dry-run` to test scanning speed separately?
- How does performance compare to other duplicate finders?