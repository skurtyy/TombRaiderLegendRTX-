# Build 039 — Remove RET, More Geometry Submitted (FAIL — Progress)

## Result

**FAIL** — but significant progress. Green stage light now appears at extreme distance (clean shot 3). Red+green both visible in shot 1 (near stage). Shot 2 shows only fallback red (both stage lights gone at that position). Shot 3 shows ONLY green — meaning Lara walked through the red light's zone into the green light's zone.

## What Changed This Build

**Removed the RET patch at 0x407150.** The frustum cull function now runs to completion with its 7 internal cull jumps NOPed. Previously, the RET skipped the entire function including its geometry submission logic. Now the function:
1. Runs all its tests (which always pass due to NOPed jumps)
2. Submits geometry that was previously being silently skipped

Draw counts nearly doubled: ~93,000 → ~180,000 per frame.

## Proxy Log Summary

- Draw counts: ~1440 (menus), ramping to ~180,000 (gameplay) — up from ~93K
- All other patches unchanged from build-037
- Frustum cull function: RET DISABLED, 7 NOPs active
- vpValid=1, passthrough=0, no crashes

## Retools Findings (from static-analyzer subagent)

N/A — carried forward from previous builds. All patch sites verified.

## Ghidra MCP Findings

N/A — carried forward.

## Open Hypotheses (what we think is still wrong and why)

1. **The cull function handles per-OBJECT visibility within sectors.** Removing the RET brought back ~87,000 draw calls that were being silently skipped. This extra geometry includes the anchor meshes for Remix lights, which is why the green light now appears at extreme distance.

2. **Some geometry is STILL not submitted at all positions.** The function at 0x407150 handles one category of culling (frustum/distance), but there may be additional per-instance visibility flags or LOD-based filtering in other code paths. The fact that shot 2 loses both lights while shot 3 keeps green suggests the anchor geometry coverage is position-dependent.

3. **The NOPed jumps inside 0x407150 may not cover all rejection paths.** The function has ~4KB of code. The 7 NOPs target specific conditional jumps, but there may be other exit paths (e.g., early returns based on object flags, LOD selection, draw distance thresholds beyond the frustum test).

## Next Build Plan (what to change next and what result to expect)

1. **Decompile 0x407150 fully** (with kb.h types) to identify ALL rejection paths — not just the 7 known cull jumps. Look for any other conditional that leads to the function returning without submitting geometry.
2. **Also NOP the frustum threshold** approach is already in place (`-1e30`), but verify it's being read by this function at runtime.
3. **Consider that the randomized movement sends Lara too far** — the strafes may push her into areas where sector geometry genuinely doesn't exist (edge of playable area). The green-only shot 3 suggests she walked into the green light's sector but out of the red's render range.
