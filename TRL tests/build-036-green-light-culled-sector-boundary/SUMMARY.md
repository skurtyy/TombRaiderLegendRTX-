# Build 036 — Green Light Culled at Sector Boundary

## Result

**FAIL** — Green stage light missing in clean render screenshot 3. Red light visible in all 3, green only in 2/3.

## What Changed This Build

- Fixed `ctypes.cast(buf, wt.LPARAM)` crash in setup dialog automation (`run.py`) — replaced with `ctypes.addressof(buf)` and added proper `SendMessageW.argtypes` declaration
- No proxy code changes from build-035; this is a re-test with fixed automation

## Proxy Log Summary

- Draw counts: ~1440 (menus) ramping to ~95,520 (gameplay), stable
- vpValid=1 on all scene reports
- passthrough=0, skippedQuad=0, xformBlocked=0
- All patches applied successfully:
  - Frustum threshold: -1e30
  - Cull jumps NOPed: 7/7
  - Frustum cull function ret: 0x407150
  - Sector visibility checks NOPed: 2/2
  - Cull mode globals: D3DCULL_NONE
  - Light frustum rejection NOPed: 0x60CE20
  - Light_VisibilityTest always TRUE: 0x60B050
  - Sector light count gate NOPed: 0xEC6337

## Retools Findings (from static-analyzer subagent)

All patch sites verified correct on-disk. Original bytes match expected patterns. The RET at 0x407150 correctly overwrites `push ebp` (0x55→0xC3). All 7 cull NOPs, 2 sector visibility NOPs, and light frustum NOP are 6-byte `0F 8x` conditional jumps → 6x `0x90`. No issues found with patch byte patterns.

## Ghidra MCP Findings

- `RenderLights_FrustumCull` (0x60C7D0) decompiled — function accesses `tmpSortInfo[0x7A12].m_matID` for device state and calls into lighting dispatch. The function itself is reached only if the sector light gate passes.

## Open Hypotheses (what we think is still wrong and why)

**Primary hypothesis: Sector light list boundary issue.** When Lara walks far enough from the stage area, she enters a different sector whose light list (`[lightGroup+0x1B0]`) contains 0 lights. The gate at 0x60E345/0x60E354 checks this count and skips `RenderLights_FrustumCull` entirely — none of the frustum/visibility patches matter because the lights never reach that code path.

The sector light count gate at 0xEC6337 is already NOPed, but the findings suggest there's an additional gate at 0x60E345 that checks the per-sector light count directly. This upstream gate blocks lights before they reach any of our patched functions.

Evidence:
- Clean render shots 1-2: both lights visible (Lara near stage, in the correct sector)
- Clean render shot 3: only red light visible (Lara has walked far enough to cross into a sector with no green light in its list)
- Hash debug confirms movement is real (not false positive)

## Next Build Plan (what to change next and what result to expect)

1. **Patch the sector light count gate at 0x60E345** — force `[ebx+0x1B0]` check to always pass, or patch the conditional jump to never skip the light rendering path
2. **Alternatively**: find where sector light lists are populated and ensure stage lights are added to ALL sectors, not just the one containing them
3. **Live verification first**: use `livetools trace 0x60E345` to confirm the light count drops to 0 when Lara moves to the far position

Expected result: if the 0x60E345 gate is the true bottleneck, patching it should make both lights visible at all 3 positions. If lights still disappear, there's yet another sector-scoped gate upstream.
