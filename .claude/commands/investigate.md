---
description: Investigate TerrainDrawable at 0x40ACF0 (the anchor-disappearance blocker) or any other render function. Delegates to the terrain-drawable-investigator subagent.
argument-hint: [optional address, defaults to 0x40ACF0]
allowed-tools: Task, Read
---

Delegate to the `terrain-drawable-investigator` subagent.

If $1 is provided, target that address. Otherwise default to `0x40ACF0` (TerrainDrawable).

After the subagent returns, summarize:
1. Top 3 patch candidates ranked by effort-to-impact
2. Which call sites need decompilation next
3. Whether `culling-patch-reviewer` should be invoked before any patch is written

Append the full JSON output to `retools/investigations/YYYY-MM-DD-${1:-terrain}.json`.
