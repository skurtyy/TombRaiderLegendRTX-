# Build 037 — RenderLights Gate NOP + Light Count Clear NOP (FAIL)

## Result

**FAIL** — Green stage light missing in clean render screenshots 2 and 3. Red light visible in all 3. Both lights visible only in shot 1 (near stage).

## What Changed This Build

Added two new runtime patches:
1. **RenderLights gate NOP at 0x60E3B1** — 6-byte JE (`0F 84 FF 00 00 00`) that skips `RenderLights_FrustumCull` when sector light count is 0. Now NOPed to force light rendering regardless of sector light count.
2. **Sector light count clear NOP at 0x603AE6** — 6-byte MOV (`89 B8 B0 01 00 00`) that zeroes `[eax+0x1B0]` every frame. Now NOPed so sectors retain their initial light count.

## Proxy Log Summary

- All patches applied successfully (confirmed in log):
  - Frustum threshold: -1e30
  - Cull jumps NOPed: 7/7
  - Frustum cull function ret: 0x407150
  - Sector visibility checks NOPed: 2/2
  - Cull mode globals: D3DCULL_NONE
  - Light frustum rejection NOPed: 0x60CE20
  - Light_VisibilityTest always TRUE: 0x60B050
  - Sector light count gate NOPed: 0xEC6337
  - **NEW: RenderLights gate NOPed: 0x60E3B1**
  - **NEW: Sector light count clear NOPed: 0x603AE6**
- vpValid=1 on all scenes, passthrough=0, no crashes
- Draw counts: ~1440 (menus), ramping to ~93,480 (gameplay)

## Retools Findings (from static-analyzer subagent)

Previous build findings confirmed all existing patch sites correct. New analysis identified the JE at 0x60E3B1 as the sector light count gate — now patched. The MOV at 0x603AE6 clears light counts per frame — now patched.

## Ghidra MCP Findings

`RenderLights_FrustumCull` (0x60C7D0) decompiled — accesses `tmpSortInfo[0x7A12].m_matID` for device state. The function is reached only after the sector gate passes.

## Open Hypotheses (what we think is still wrong and why)

The green light still disappears at distance despite NOPing the RenderLights gate AND preventing light count clears. This rules out the sector light count gate as the sole cause. Remaining possibilities:

1. **Light data pointer is NULL for remote sectors.** Even with the gate NOPed, if `[lightGroup+0x1B8]` (the light data pointer) is NULL for sectors that don't own lights, `RenderLights_FrustumCull` gets called but has no light data to iterate over. The light count may be nonzero (preserved), but the actual light pointer array was never populated for that sector.

2. **Light volume geometry is sector-owned.** The green light's mesh geometry may be associated with a specific sector and only submitted during that sector's render pass. Our sector visibility patches force all sectors to render, but if the green light is in a sector that the engine doesn't traverse when Lara is far away, its draw calls never reach the pipeline.

3. **Distance-based light attenuation.** The Remix-placed lights may have a maximum range. When Lara walks far enough, the light falls off to zero. This would be a Remix config issue, not an engine patch issue.

4. **The red light is the fallback light.** The red tint in screenshots 2-3 may actually be the `rtx.fallbackLightRadiance = 3, 0.3, 0.3` (heavy red bias) rather than the red stage light. If both stage lights are gone and only the fallback remains, it would look exactly like this.

## Next Build Plan (what to change next and what result to expect)

1. **Verify hypothesis 4 first**: Change `rtx.fallbackLightRadiance` to something neutral (e.g., `1, 1, 1`) and re-test. If shots 2-3 turn white instead of red, the "red light" is actually the fallback and BOTH stage lights are being culled at distance.
2. **If fallback confirmed**: The issue is geometry submission, not light function calls. Need to trace which draw calls are missing when Lara moves away — use dx9tracer frame capture at both positions.
3. **If red light is real**: Focus on why green is culled but red isn't — they may be in different sectors or have different light types.
