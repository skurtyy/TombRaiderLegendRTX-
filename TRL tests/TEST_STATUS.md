# TRL RTX Remix — Test Status Report

**Last reviewed:** 2026-03-27
**Builds reviewed:** 001, 002, 016–033 (20 builds, 003–015 not preserved)
**Overall status:** FAILING — per-light culling gates patched, sector light list population is the remaining blocker

---

## Current Findings

### What Works

1. **Asset hash stability (static + moving camera):** Hash rule `indices,texcoords,geometrydescriptor` produces stable, session-reproducible hashes. Lara's character model is rock-solid across all positions and sessions. World geometry hashes are stable since sector visibility patches were added (build 028+).

2. **Proxy transform pipeline:** View/Proj matrices read from game memory (`0x010FC780`, `0x01002530`), World computed via WVP decomposition. 100% of draws processed (passthrough=0, xformBlocked=0, vpValid=1) in all recent builds.

3. **All geometry culling defeated:**
   - Frustum threshold stamped to -1e30 per BeginScene
   - Per-object frustum function RETed at 0x407150
   - 7 scene traversal cull jumps NOPed
   - Backface culling forced to D3DCULL_NONE
   - Cull mode globals stamped (0xF2A0D4/D8/DC)
   - Sector/portal visibility gates NOPed (0x46C194, 0x46C19D) — produced 65x draw count increase

4. **Per-light culling gates defeated:**
   - Light frustum 6-plane test NOPed (0x60CE20)
   - Light broad-visibility test NOPed (0x60CDE2)
   - `Light_VisibilityTest` patched → always TRUE (0x60B050 → `mov al,1; ret 4`, build 031)
   - Sector light count gate NOPed (0xEC6337, build 033)

5. **Automated test pipeline:** Two-phase (hash debug + clean render), randomized movement, scancode input delivery confirmed working since build 018.

6. **Stage lights visible at baseline position:** Both red and green stage lights appear correctly in screenshot 1 (Lara at start position) in all recent builds.

### What Fails

1. **Stage lights disappear when Lara moves far from stage.** Lights are visible at baseline (close to stage) but vanish when Lara walks away. Root cause confirmed: the per-sector light array at `[sector+0x1B0]` is only populated for sectors near the camera. When Lara enters a different sector, its light count is 0 and `RenderLights_FrustumCull` is never called.

2. **Sector light list population unpatched.** `FUN_006033d0` and `FUN_00602aa0` (called in `RenderScene_TopLevel` at 0x60A0F0 before `RenderScene_Main`) build per-sector light lists with a proximity filter. This filter is the last unpatched culling mechanism.

3. **Test macro broken (build 033).** The automated macro captured the in-game pause menu instead of gameplay for all 6 screenshots. An ESCAPE keypress is needed after level load to dismiss the menu. Build 033's proxy changes (0xEC6337 NOP) are untested.

### Hurdles

1. **Sector light list builder not yet located precisely.** `FUN_006033d0` and `FUN_00602aa0` are candidate functions but need decompilation to confirm which one applies the proximity filter and where to patch it.

2. **`sector+0x84` gate in `RenderScene_Main`.** Even with a non-zero light count, `RenderScene_Main` only calls the light pass if `sector+0x84 + sector+0x94 != 0`. The function that sets this field per-frame is unknown — if it also uses proximity, disabling the light list builder's filter may not be sufficient alone.

3. **Test macro reliability.** Build 033 exposed that the macro can capture the pause menu. This needs a one-time fix before results can be trusted again.

4. **Remaining unexplored light path.** Light Draw virtual method (`vtable[0x18]` per light) may have internal culling that activates after all upstream gates are bypassed (hypothesis from build 025, never confirmed).

---

## Build-by-Build Summary

| Build | Result | Key Change | Key Finding |
|-------|--------|------------|-------------|
| 001 | PASS | Baseline passthrough + transform override | Hashes stable (static camera), cross-session reproducible |
| 002 | PASS | Two-phase test confirmation | RTX path tracing works, hash stability confirmed |
| 016 | PASS* | 3-layer anti-culling + frustum threshold | Draw count 91.8K; *movement was broken (false positive — no scancode) |
| 017 | FAIL | NOPs in proxy + BeginScene re-stamp | Lights disappear after D-strafe, hash colors shift |
| 018 | FAIL | Scancode fix — movement actually works | Green light disappears on D-strafe; real movement confirmed |
| 019 | PASS* | Same code as 018, different RNG seed | False positive — wrong screenshots evaluated |
| 020 | FAIL | Fixed screenshot selection | Build 019 was false positive; red light missing in 2/3 shots |
| 021 | PASS* | VS 2026 Insiders build fix | False positive — Lara didn't move |
| 022 | FAIL | Confirmed exe is unmodified (runtime-only patches) | D held too long, Lara left stage area |
| 023 | FAIL | Light frustum NOPs in wrong source file | Bug: repo-root proxy/ not compiled — always edit patches/ proxy |
| 024 | FAIL | Light frustum NOPs in correct source | Shot 1 both lights visible; shots 2-3 fail — zone hypothesis formed |
| 025 | FAIL | Pending-render flag NOPs (0x603832, 0x60E30D) | No effect — bottleneck is not in caller chain flags |
| 026 | FAIL | LightVolume_UpdateVisibility state NOPs (5 addrs) | Patches NOT in proxy log — silent VirtualProtect failure |
| 027 | FAIL | Same patches + randomized movement | Draw counts 93K-189K confirm sector patch works; issue is light range |
| 028 | FAIL | Sector visibility NOPs + removed native light patches | Geometry fully submitting (65x increase); clean render dark |
| 029 | FAIL | Cull globals stamped + light frustum NOP + threshold -1e30 | All geometry culling defeated; light disappearance remains |
| 030 | FAIL | Baseline retest + Ghidra analysis | Root cause: `Light_VisibilityTest` at 0x60B050 unpatched |
| 031 | FAIL | `Light_VisibilityTest` → always TRUE (0x60B050) | Lights at baseline; disappear at distance — root moved to sector light list |
| 032 | FAIL | Config flag 0x01075BE0 = 1 ("Disable extra light culling") | No effect — flag has no code xrefs, not connected to light collection |
| 033 | FAIL | NOP at 0xEC6337 (sector light count gate); no proxy changes | Macro failure — pause menu blocked all screenshots; result inconclusive |

*False positive — movement input not reaching game or Lara didn't move.

---

## What's Been Done

- [x] D3D9 proxy DLL with shader passthrough + transform override
- [x] Asset hash rule: `indices,texcoords,geometrydescriptor` (excluding positions)
- [x] View/Proj matrix reading from game memory
- [x] World matrix decomposition from WVP
- [x] Frustum threshold stamped to -1e30 per BeginScene (0xEFDD64)
- [x] Per-object frustum function RETed (0x407150)
- [x] 7 scene traversal cull jumps NOPed
- [x] Backface culling forced to D3DCULL_NONE
- [x] Cull mode globals stamped (0xF2A0D4/D8/DC)
- [x] Sector/portal visibility gates NOPed (0x46C194, 0x46C19D)
- [x] Light frustum 6-plane test NOPed (0x60CE20)
- [x] Light broad-visibility test NOPed (0x60CDE2)
- [x] `Light_VisibilityTest` patched → always TRUE (0x60B050)
- [x] Sector light count gate NOPed (0xEC6337)
- [x] Automated two-phase test pipeline (hash debug + clean render, randomized movement)
- [x] Scancode input fix for DirectInput games
- [x] Stage light anchoring via mod.usda mesh hashes
- [x] `user.conf` override issue identified and fixed
- [x] Source file bug identified: always edit `patches/TombRaiderLegend/proxy/d3d9_device.c`
- [x] VirtualProtect failure detection: always verify patches in proxy log
- [x] Engine config flag at 0x01075BE0 investigated — no effect (build 032)

## What Still Needs To Be Done

- [ ] **Fix test macro pause menu** — add ESCAPE keypress after level load; re-run build 033 proxy code to get valid screenshots for the 0xEC6337 NOP
- [ ] **Decompile `FUN_006033d0` and `FUN_00602aa0`** — identify which one populates per-sector light lists and where the proximity filter lives
- [ ] **Patch the sector light list builder** — remove proximity filter so all level lights enter every sector's list
- [ ] **Investigate `sector+0x84` setter** — `RenderScene_Main` gates the light pass on this field; find the function that sets it and confirm it doesn't also apply proximity filtering
- [ ] **Achieve a "miracle" build** — both stage lights visible in ALL positions with stable hashes

### Lower Priority
- [ ] Investigate Light Draw virtual method (vtable[0x18]) for internal culling — only if sector light list patch is insufficient
- [ ] Investigate LOD alpha fade at 0x446580 (10 callers) — may fade geometry at distance, low priority post-sector-patch
- [ ] Investigate particle/effect distance culling at 0x446B5A, 0x446BE0 — not related to current blocker

---

## Review Schedule

This document is reviewed and updated every 5 commits to track progress across builds.
