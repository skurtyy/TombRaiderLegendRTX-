# Build 033 — Pause Menu Macro Fail

## Result

**FAIL** — All 6 screenshots (3 hash debug, 3 clean render) show the in-game pause menu overlaying the scene. The macro failed to navigate past the pause menu into gameplay. Cannot evaluate stage lights or movement.

## What Changed This Build

No proxy code changes from build-032. This build tests the existing proxy with the automated test pipeline.

## Proxy Log Summary

- **Draw counts**: ~1440/scene early, ramping to ~190K cumulative, stabilizing at ~94K/window in-game
- **vpValid**: 1 on ALL scene reports — view-projection matrix always valid
- **passthrough**: 0 — every draw processed through FFP pipeline
- **skippedQuad**: 0
- **xformBlocked**: 0
- **total == processed** in every scene report
- **No crashes or errors** in the entire 12,042-line log

### Patch Addresses (all activated successfully)

| Address | Patch | Status |
|---------|-------|--------|
| 0x407150 | Frustum cull function → RET | Applied |
| 0x4072BD-0x407B7B | 7 cull jumps → NOP | 7/7 |
| 0x46C194, 0x46C19D | Sector visibility → NOP | 2/2 |
| 0x60CE20 | Light frustum rejection → NOP | Applied |
| 0x60B050 | Light_VisibilityTest → always TRUE | Applied |
| 0xEC6337 | Sector light count gate → NOP | Applied |
| 0xEFDD64 | Frustum threshold → -1e30 | Applied |
| 0xF2A0D4/D8/DC | Cull mode globals → D3DCULL_NONE | Applied |

## Retools Findings (from static-analyzer subagent)

All patch sites verified correct on-disk:
- 0x407150: original `55` (push ebp), runtime-patched to `C3` (ret) — correct
- All 7 cull jumps confirmed as 6-byte `0F 8x` conditional near jumps — NOP-safe
- Sector visibility at 0x46C194/0x46C19D: confirmed `0F 84`/`0F 85` — NOP-safe
- Light frustum rejection at 0x60CE20: confirmed `0F 8B` (JNP) — NOP-safe
- Light_VisibilityTest at 0x60B050: thiscall with `ret 4` — patch `B0 01 C2 04 00` matches calling convention

Redundant patch note: proxy applies patches both at device creation AND in `applyMemoryPatches`. Harmless double-write.

## Ghidra MCP Findings

### RenderLights_FrustumCull (0x60C7D0)
- Builds 6 frustum planes from camera FOV, iterates lights via `[this+0x1B0]` count
- Calls `Light_VisibilityTest` per light (patched to always return TRUE)
- Lights passing: drawn via `call [eax+0x18]` (vtable[6] = LightVolume::Draw)
- Lights failing frustum: deferred to global list at 0x13107FC
- Uses `g_cullMode_pass1/pass2` globals (patched to D3DCULL_NONE)

### Light_VisibilityTest (0x60B050)
- Three-way mode switch on `[this+0x74]->[+0x448]`:
  - Mode 0 (spotlight): calls 0x60AD20
  - Mode 1 (pointlight): radius * scale AABB via 0x60AC80 + 0x5F9A60
  - Mode 2 (directional): AABB via 0x60AC80 + 0x5F9BE0
  - Default: returns TRUE
- Patched to `mov al, 1; ret 4` — bypasses all AABB distance checks

## Open Hypotheses

1. **Pause menu issue (THIS BUILD)**: The automated macro is not dismissing the pause menu. The game loads Bolivia and enters the pause screen. All screenshots captured with menu overlay. This is a test infrastructure issue, not a proxy issue. Possible causes:
   - Game auto-pauses after Bolivia opening cutscene
   - Macro timing mismatch with game state transitions
   - Focus loss during MOVETO cursor movements triggers auto-pause

2. **Proxy code is healthy**: All patches activated, draw counts nominal, no crashes. The proxy itself is working correctly — the test just can't validate it with the menu blocking gameplay.

3. **Sector light list boundary**: Previous analysis identified that lights may only exist in the sector containing the stage. If Lara enters a different sector, `[this+0x1B0]` (light count) drops to 0 and `RenderLights_FrustumCull` is skipped entirely. The sector light count gate NOP at 0xEC6337 should address this, but needs live verification.

## Next Build Plan

1. **Debug the macro**: Investigate why the game shows the pause menu during the test. Check if Bolivia needs an extra key press after cutscene, or if focus is being lost. May need to add an ESCAPE press to dismiss the pause menu after level load.
2. **Re-run the same proxy code** with a fixed macro to get valid screenshots
3. **If screenshots pass**: lights visible at all positions + stable hashes = PASS
4. **If lights still fail at distance**: Live-trace the sector light count gate at 0x60E345 to check `[this+0x1B0]` values
