# Creating GitHub Release for v1.0.0

The Linux binary download failed because we only created a git tag, not a GitHub Release. 

## Issue
- Git tag exists: `v1.0.0`  
- GitHub Release doesn't exist
- Release workflow only triggers on GitHub Release creation, not tag pushes
- Therefore no binaries were built

## Solution
Create a GitHub Release using the existing v1.0.0 tag:

1. Go to https://github.com/w1lkns/diskcomp/releases/new
2. Choose tag: v1.0.0 
3. Release title: "diskcomp 1.0.0"
4. Description: First stable release with binary distribution
5. Publish release

This will trigger the `.github/workflows/release.yml` workflow to build binaries.