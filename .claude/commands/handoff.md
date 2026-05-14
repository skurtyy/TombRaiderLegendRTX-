---
description: Generate a verbose, LLM-ingestible handoff log of the current session state. Captures full technical context, open blockers, and reproducible next steps.
allowed-tools: Read, Write, Bash, Grep, Glob
---

Produce an exhaustive handoff document at `handoffs/YYYY-MM-DD-HHMM-handoff.md` covering:

1. **Project state snapshot**
   - Current build number, last commit SHA, dirty/clean working tree
   - Active blockers (TerrainDrawable @ 0x40ACF0, hash instability)
   - Confirmed facts (VS const layout, DLL chain, rtx.conf values)

2. **Last 3 builds**
   - Build number, patches applied, pass/fail per criterion, screenshots referenced

3. **Open investigations**
   - Files in `retools/investigations/`
   - Pending GhidraMCP decompilations

4. **Dead ends added in this session**
   - Approach, why it failed, evidence link

5. **Next session priorities** (ranked, with reproducible commands)

6. **Environment state**
   - GhidraMCP status, game install path, Python/pyghidra version, MSVC version
   - PowerShell launch commands needed to resume

Write this in verbose technical style suitable for another LLM to ingest cold. Do not use the headless-terminal user-facing persona — use the documentation protocol style with full logic paths and granular failure points.
