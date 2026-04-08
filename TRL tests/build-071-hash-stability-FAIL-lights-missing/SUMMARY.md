# Build 071 — Hash Stability Test

## Result
**FAIL-lights-missing** — No red or green stage lights visible in any clean render screenshot. Lara not visible. Draw counts stable (~2845).

## Test Configuration
- Level: Peru (Chapter 4, `-NOMAINMENU -CHAPTER 4`)
- Camera: Mouse pan only (300px left, 600px right)
- Debug view 277 (Phase 1), view 0 (Phase 2)
- Mod updated: `pee/mod.usda` now has 8 mesh hashes (original 5 + 3 from package)

## What Changed This Build
- Added 3 additional mesh hashes from `package/mod.usda` to the active `mod.usda`:
  - `mesh_5601C7C67406C663` (red light)
  - `mesh_ECD53B85CBA3D2A5` (red light)
  - `mesh_AB241947CA588F11` (green light)
- Total light anchors: 8 hashes (5 red, 3 green)
- No proxy code changes

## Phase 1: Hash Debug Analysis
- 3 screenshots captured at center/left/right camera positions
- Camera clearly moved between shots (different perspectives confirmed)
- Hash colors appear consistent for same geometry across views
- Lara NOT visible in any hash debug screenshot

## Phase 2: Light Anchor Analysis
- 3 screenshots captured at center/left/right positions
- Peru street scene renders correctly with ray tracing (wooden buildings, cobblestone)
- **NO red or green lights visible in ANY screenshot**
- Lara NOT visible in any clean render screenshot
- Only illumination is from fallback light (neutral white/gray ambient)

## Phase 3: Live Diagnostics

### Draw Call Census
- `dipcnt` returned "Not installed" for all 3 positions (instrumentation issue)
- Proxy log draw counts: ~2845-2849 (stable), drops to 685 at S518

### Patch Integrity
| Address | Expected | Actual | Status |
|---------|----------|--------|--------|
| 0xEFDD64 | -1e30 float | `CA F2 49 F1` (-1e30f) | PASS |
| 0xF2A0D4/D8/DC | D3DCULL_NONE (1) | `01 00 00 00` x3 | PASS |
| 0x407150 | `55` (PUSH EBP — original) | `55` | Expected (proxy NOPs internal jumps, not entry) |
| 0x60B050 | `B0 01 C2 04` (mov al,1; ret 4) | `B0 01 C2 04` | PASS |

### Memory Watch
- SetWorldMatrix trace: 51,484 calls in 15s from caller 0x004150DF
- Function is actively being called (good)

### Function Collection
- 0x00413950 (SetWorldMatrix): 51,484 records in 15s — active

## Phase 4: Frame Capture Analysis
Skipped (not implemented in current test version)

## Phase 5: Static Analysis
Background subagent dispatched for:
- Disassembly of 0x407150 (cull function)
- Disassembly of 0x40C430 (RenderQueue_FrustumCull — PRIME SUSPECT)
- Disassembly of 0x40C390 (uncull path)

## Phase 6: Vision Analysis
- Hash debug: Camera moved between shots, hash colors stable
- Clean render: No colored lights in any screenshot, only neutral ambient illumination
- Lara not visible — either behind camera or model not being drawn

## Proxy Log Summary
- Build successful, proxy loaded and chaining to Remix
- 11/11 cull jumps NOPed
- All patches applied successfully at CreateDevice time
- Draw counts stable ~2845 (significantly better than build 070's 185)
- Draw count drops to 685 at S518 (possible scene transition)
- `useVertexCapture = False` in rtx.conf

## Brainstorming: New Hash Stability Ideas
1. The 8 mesh hashes in the mod may not match what the game currently produces — need a fresh Remix capture at Peru street to compare
2. With `useVertexCapture = False`, hash generation differs from when the original hashes were captured
3. A dx9tracer near vs far frame diff would definitively show which draw calls (and thus which hashes) disappear at distance

## Open Hypotheses
1. **RenderQueue_FrustumCull (0x40C430) — PRIME SUSPECT**: Layer 30 recursive frustum culler, NOT patched. Operates after all other submission gates. May be dropping anchor geometry before DrawIndexedPrimitive.
2. **Anchor geometry never submitted**: The mesh hashes in the mod may not correspond to meshes that exist in the Peru street scene at this camera position.
3. **Hash mismatch**: With `useVertexCapture = False`, the current runtime hashes may differ from the hashes captured when lights were originally placed.
4. **Lara visibility**: Camera angle may be looking away from Lara's position after cutscene skip.

## Next Steps
1. **Patch RenderQueue_FrustumCull (0x40C430)** — redirect entry to 0x40C390 (uncull path) via single `mem write`
2. **Fresh Remix capture** at Peru street to verify current mesh hashes match mod
3. **dx9tracer frame diff** (near vs far) to identify which draws disappear
4. **Investigate Lara visibility** — may need to adjust initial camera or verify cutscene skip timing
