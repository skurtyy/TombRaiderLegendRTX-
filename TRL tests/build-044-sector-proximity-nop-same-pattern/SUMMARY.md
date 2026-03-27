# Build 044 — Sector-Object Camera Proximity NOP (FAIL — Same Pattern)

## Result

**FAIL** — Same pattern. Both lights near stage (shot 1), fallback-only at distance (shots 2-3). The camera-sector proximity filter NOP didn't fix it.

## What Changed This Build

- NOPed 2-byte JNE at 0x46B85A — the camera-sector proximity filter in RenderSector (0x46B7D0) that skips objects without flag 0x200000 when not in camera's sector
- Build 043 (all 7 NOPs including disabled-object flag checks) crashed — removed the aggressive patches, kept only the proximity filter NOP

## Proxy Log Summary

- Sector-object camera proximity filter NOPed at 0x46B85A
- No crash, all other patches active
- Draw counts ~190K, consistent with builds 040-041

## Upstream Caller Analysis (from static-analyzer)

Full call chain traced: 0x450DE0 -> 0x450B00 -> 0x443C20 -> 0x407150

RenderFrame (0x450B00) calls TWO separate render paths:
1. RenderVisibleSectors (0x46C180) -> RenderSector (0x46B7D0) — sector geometry
2. SceneTraversal wrapper (0x443C20) -> 0x407150 — scene graph objects

Plus a post-sector moveable object loop at 0x40E2C0.

All three paths now have culling patches, yet anchor geometry still disappears. Remaining possibility: the anchor meshes are **terrain** geometry going through TerrainDrawable (0x40ACF0) which has its own separate culling path.

## Next Steps

1. Investigate terrain rendering path — TerrainDrawable constructor at 0x40ACF0, TERRAIN_DrawUnits
2. dx9tracer frame capture to definitively identify which draw calls disappear at distance
3. Consider that the randomized strafes push Lara past ALL sector boundaries into areas with genuinely no geometry
