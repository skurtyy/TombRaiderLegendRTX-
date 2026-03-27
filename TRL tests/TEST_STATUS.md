# TRL RTX Remix — Test Status Report

**Last reviewed:** 2026-03-27
**Builds reviewed:** 001, 002, 016–033, 035 (21 builds, 003–015 and 034 not preserved)
**Overall status:** FAILING — green light anchor stable; red light anchor all in sectors with zero native static light data (`[sector_data+0x664]=0`)

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
   - Sector light count gate NOPed (0xEC6337) inside `FUN_00EC62A0` (0xEC62A0), confirmed build 035

5. **Automated test pipeline:** Two-phase (hash debug + clean render), randomized movement, scancode input delivery confirmed working since build 018. Pause menu macro fix applied before build 035.

6. **Green stage light stable at ALL positions (build 035):** `mesh_AB241947CA588F11` is in a sector with non-zero `[sector_data+0x664]`, so `FUN_00EC62A0` always populates its light count. Green light holds across all Lara positions.

### What Fails

1. **Red stage light disappears when Lara moves.** Build 035 confirmed: every candidate anchor mesh for the red light (`mesh_6AF01B710C2489F5` and alternatives `7DFF`, `6AF0`, `5601`, `ECD5`) is in a sector where `[sector_data+0x664]=0`. `FUN_00EC62A0` reads this field to populate the sector's light count — when it is 0, the count stays 0 even with the gate NOP. No native static light data means nothing enters the per-sector list.

2. **Directional fallback incompatible with sphere light.** `rtx.fallbackLightMode=2` with a red directional radiance was tried (build 035) but incompatible intensity profiles with the green sphere light mean one always dominates — can't balance both simultaneously.

3. **Sector light list upstream population unpatched.** `FUN_006033d0` and `FUN_00602aa0` (called in `RenderScene_TopLevel` at 0x60A0F0 before `RenderScene_Main`) build per-sector light lists. These have not been decompiled; the proximity filter that limits which lights enter a sector's list lives here.

### Hurdles

1. **Sectors with `[sector_data+0x664]=0` cannot benefit from gate NOP alone.** The `FUN_00EC62A0` gate NOP at 0xEC6337 only helps sectors that already have non-zero native static light data. Red light anchor sectors have zero data — the gate NOP is a no-op for them. Need a different approach: either patch sector data at runtime, replay light draw calls, or anchor to a mesh that is always in a light-populated sector (e.g., Lara's body).

2. **Sector light list builder not yet decompiled.** `FUN_006033d0` and `FUN_00602aa0` are the upstream candidates. Until decompiled, we cannot confirm which applies the proximity filter or where to patch it.

3. **`sector+0x84` gate in `RenderScene_Main`.** `RenderScene_Main` only calls the light pass if `sector+0x84 + sector+0x94 != 0`. The setter for this field is unknown — if it is also proximity-gated, patching the light list builder alone may be insufficient.

4. **Remaining unexplored light path.** `LightVolume::Draw` (vtable[0x18], vtable[6]) may have internal culling that activates after upstream gates are bypassed (hypothesis from build 025, never confirmed). Lights failing frustum are deferred to a global list at `0x13107FC` — unknown whether those are eventually rendered.

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
| 035 | FAIL | Sector light gate NOP confirmed + Light_VisibilityTest patch + directional red fallback | Green stable at all positions; red anchor meshes all in sectors with `[sector_data+0x664]=0` |

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
- [x] Sector light count gate NOPed (0xEC6337) inside `FUN_00EC62A0` (0xEC62A0) — confirmed build 035
- [x] Automated two-phase test pipeline (hash debug + clean render, randomized movement)
- [x] Scancode input fix for DirectInput games
- [x] Stage light anchoring via mod.usda mesh hashes
- [x] Test macro pause menu fix applied (before build 035)
- [x] `user.conf` override issue identified and fixed
- [x] Source file bug identified: always edit `patches/TombRaiderLegend/proxy/d3d9_device.c`
- [x] VirtualProtect failure detection: always verify patches in proxy log
- [x] Engine config flag at 0x01075BE0 investigated — no effect (build 032)
- [x] Directional fallback light (rtx.fallbackLightMode=2) tried — incompatible with sphere light, ruled out (build 035)
- [x] Alternative red anchor meshes (7DFF, 6AF0, 5601, ECD5) investigated — all in sectors with `[sector_data+0x664]=0`, ruled out (build 035)

## What Still Needs To Be Done

Three alternative approaches for the red light (any one would unblock):

- [ ] **Option A — Runtime sector data patch:** Find `*(renderCtx+0x220)` base at runtime and write 1 to `[sector_data + N*0x684 + 0x664]` for all N sectors. Forces all sectors to claim they have native static lights, enabling `FUN_00EC62A0` to populate their light counts.
- [ ] **Option B — Draw call replay in proxy:** Record light volume `DrawIndexedPrimitive` calls during the first frame (when all lights render). Replay them every subsequent frame to keep anchor hashes always present for Remix regardless of sector state.
- [ ] **Option C — Anchor to Lara's mesh:** Identify Lara's body mesh hash (compare Remix captures across positions). Anchor both stage lights to it — Lara is always rendered, always in the same sector as the camera.

- [ ] **Decompile `FUN_006033d0` and `FUN_00602aa0`** — understand the upstream light list builder and proximity filter (needed for deeper fix or confirmation that Option A/B/C is sufficient)
- [ ] **Investigate `sector+0x84` setter** — `RenderScene_Main` gates the light pass on this field; confirm whether a proximity filter here would re-block lights after sector data is patched
- [ ] **Achieve a "miracle" build** — both stage lights visible in ALL positions with stable hashes

### Lower Priority
- [ ] Investigate `LightVolume::Draw` (vtable[0x18]) for internal culling — only if upstream options are insufficient
- [ ] Investigate global deferred light list at `0x13107FC` — lights failing frustum are appended here; unknown if they are rendered elsewhere
- [ ] Investigate LOD alpha fade at 0x446580 (10 callers) — may fade geometry at distance, low priority
- [ ] Investigate particle/effect distance culling at 0x446B5A, 0x446BE0 — not related to current blocker

---

## Review Schedule

This document is reviewed and updated every 5 commits to track progress across builds.
