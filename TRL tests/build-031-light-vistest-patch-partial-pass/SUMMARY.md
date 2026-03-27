# Build 031 — Light_VisibilityTest Patch (Partial Pass)

## Result
**FAIL** — Both lights visible at baseline position (screenshot 1), but lights disappear when Lara moves far from stage. Green light only in screenshot 3, no lights in screenshot 2.

## What Changed This Build
- Added runtime patch at `0x0060B050` (`Light_VisibilityTest`): `mov al, 1; ret 4` — forces all lights to pass the pre-frustum visibility gate.
- This was identified as the root cause in build 030's Ghidra analysis.

## Proxy Log Summary (draw counts, vpValid, patch addresses)
- All patches confirmed applied:
  - Frustum threshold → -1e30
  - 7/7 cull jumps NOPed
  - Frustum cull function → ret (0x407150)
  - 2/2 sector visibility checks NOPed
  - Cull mode globals → D3DCULL_NONE
  - Light frustum rejection NOPed (0x60CE20)
  - **Light_VisibilityTest → always TRUE (0x60B050)** ← NEW
- Draw counts: 1,416-189,960 (sector patches working, high counts during gameplay)
- vpValid=1, passthrough=0, xformBlocked=0
- No crashes

## Retools Findings (from static-analyzer subagent)
- Pending (subagent running)

## Ghidra MCP Findings
- `Light_VisibilityTest` (0x60B050) is `__thiscall` with 1 stack param. Performs distance/sphere/cone checks per light type (0, 1, 2). Our `ret 4` patch is correct for the calling convention.
- `RenderLights_FrustumCull` (0x60C7D0) iterates lights from `[sector+0x1B0]` count / `[sector+0x1B8]` array. Our `Light_VisibilityTest` patch correctly bypasses the per-light gate.
- **Root cause of remaining failure**: `RenderScene_Main` (0x603810) iterates all sectors but only calls `RenderScene_LightPass` if `sector+0x84 + sector+0x94 != 0`. The light list is per-sector — when Lara moves to a sector without the stage lights in its list, the light count is 0 and no lights render.
- `RenderScene_LightPass` (0x60E2D0) clears `sector+0x84 = 0` after rendering, so it must be re-set each frame by an upstream light collection system.
- Config table at 0xF1325C has entry "Disable extra static light culling and fading" mapping to variable at **0x01075BE0**. No direct xrefs (accessed through table lookup).

## Open Hypotheses (what we think is still wrong and why)
1. **Sector light list population (Layer 12)**: The per-sector light array at `[sector+0x1B0]` is only populated for sectors near the camera. Stage lights exist in the stage sector's list but not in distant sectors. This is the primary remaining blocker.
2. **Config flag 0x01075BE0**: "Disable extra static light culling and fading" may control the upstream light collection system. Setting it to 1 might force all lights into all sectors.
3. **Light collection system**: Some function sets `sector+0x84` each frame based on proximity/visibility. Finding and patching this system would let all sectors receive lights.

## Next Build Plan (what to change next and what result to expect)
1. **Stamp config flag**: Add `*(DWORD*)0x01075BE0 = 1` to proxy patches — this is the engine's own debug toggle for disabling extra light culling/fading. If the config system reads this, it should prevent the upstream light collector from filtering lights by sector proximity.
2. **Expected result**: If the config flag controls light collection, lights should remain visible at all positions. If it only affects rendering-side culling (already patched), no change.
