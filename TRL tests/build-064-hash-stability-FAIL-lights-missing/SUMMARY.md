# Build 064 — Hash Stability Test

## Result

**FAIL-lights-missing** — Both red and green stage lights absent in all Phase 2 screenshots. Phase 1 invalid (loading screen captured).

## Test Configuration

- Test: `python patches/TombRaiderLegend/run.py test --build`
- Level: Peru (Chapter 4, -NOMAINMENU -CHAPTER 4)
- Camera: Mouse-only pan (no WASD), 3 positions: center, left 300px, right 300px
- Debug view: 277 (Phase 1), 0 (Phase 2)
- Proxy: Built and deployed automatically
- useVertexCapture: False
- antiCulling: Disabled (both object and light)

## Phase 1: Hash Debug Analysis

**INVALID** — All 3 screenshots show solid magenta/pink fill with RTX Remix welcome banner. The cutscene skip fired before the Peru level loaded. The 15s wait after window detection is insufficient for Remix + Peru level initialization.

- phase1_hash_center.png: Solid magenta, "Welcome to RTX Remix" banner
- phase1_hash_left.png: Solid magenta, "Welcome to RTX Remix" banner  
- phase1_hash_right.png: Solid magenta (banner dismissed)

**Root cause**: `launch_game()` waits 15s after window detection, then `camera_pan_and_screenshot()` sends cutscene skip. But the level hasn't loaded yet — the game is still initializing.

## Phase 2: Light Anchor Analysis

Peru street geometry renders correctly with camera panning visible across 3 positions. Building facades, doorways, and awnings visible. **No red or green stage lights in any screenshot.**

- phase2_clean_center.png: Peru buildings, no lights
- phase2_clean_left.png: Slight left pan, no lights
- phase2_clean_right.png: Right pan, sky visible, no lights

Camera DID pan (perspective shifts between shots), but light anchor meshes are culled by a mechanism not yet patched.

## Phase 3: Live Diagnostics

### Draw Call Census

dipcnt returned "Not installed" — the counter wasn't active. Proxy log shows stable draw counts: d=244-245 across all sampled frames.

### Patch Integrity

| Address | Expected | Actual | Status |
|---------|----------|--------|--------|
| 0xEFDD64 | -1e30 float | -1e30 | PASS |
| 0xF2A0D4/D8/DC | D3DCULL_NONE (1) | 01 00 00 00 x3 | PASS |
| 0x407150 | 0xC3 (RET) | 0x55 (PUSH EBP) | N/A — proxy NOPs internal jumps instead |
| 0x60B050 | B0 01 C2 04 | 55 8B EC 83 | N/A — proxy patches light frustum at 0x60CE20 instead |

**Note**: Test expectations at 0x407150 and 0x60B050 are stale. The proxy uses a different strategy: NOP individual cull jumps inside 0x407150 (11 jumps), and NOP the light frustum rejection at 0x60CE20. Both approaches are valid but the test checklist needs updating.

### Memory Watch

SetWorldMatrix (0x413950) traced: 14014 records in 15.2s. Confirms world matrix is being set per-object as expected.

### Function Collection

Collected from 0x413950 (SetWorldMatrix) only. Single address, consistent hit rate.

## Phase 4: Frame Capture Analysis

Skipped (placeholder for agent-driven dx9tracer capture).

### Draw Call Diff
N/A

### Constant Evolution
N/A

### Vertex Format Consistency
N/A

### Shader Map
N/A

## Phase 5: Static Analysis

Static analyzer verified all on-disk bytes at patch sites match expected originals:
- 0x407150: `55 8B EC 83` (push ebp prologue) — proxy NOPs 11 internal jumps at runtime
- 0x4072BD, 0x4072D2, 0x407AF1, 0x407B30, 0x407B49, 0x407B62, 0x407B7B: 6-byte conditional jumps confirmed
- 0x4071CE, 0x407976, 0x407B06, 0x407ABC: Additional cull jumps confirmed
- 0x46C194, 0x46C19D: Sector visibility gates confirmed
- 0x60CE20: Light frustum rejection JNP confirmed

All addresses are correct targets for NOP patches.

## Phase 6: Vision Analysis

**Hash debug (Phase 1)**: INVALID — solid magenta fill, no geometry rendered. Cannot evaluate hash stability.

**Clean render (Phase 2)**: Peru street buildings visible with slight camera pan shifts. No colored lights (red or green) visible in any frame. The light anchor meshes (`mesh_5601C7C67406C663`, `mesh_ECD53B85CBA3D2A5`, `mesh_AB241947CA588F11`, `mesh_EFD9D357F2D3A56F`, `mesh_D4A147BEEBC48792`) are not being submitted to Remix.

## Proxy Log Summary

- Proxy loaded successfully, chain-loaded Remix
- vpValid=1 on all scene frames
- Draw counts: 244-245 per frame (stable)
- All 11 cull jumps NOPed, 2 sector visibility gates NOPed
- Frustum threshold stamped to -1e30
- Cull mode globals stamped to D3DCULL_NONE
- Null-check trampoline, ProcessPendingRemovals patch, MeshSubmit_VisibilityGate patch, terrain cull gate, post-sector patches all applied
- Mesh eviction NOPed (SectorEviction x2 + ObjectTracker_Evict)
- No crashes or errors

## Brainstorming: New Hash Stability Ideas

1. **Portal/PVS system**: The lights are anchored to meshes submitted by sectors reached through portal traversal. Even with sector visibility gates NOPed, the portal graph itself may exclude sectors containing light meshes when the camera faces away.

2. **Object streaming**: Light meshes may be in a different stream chunk that gets unloaded based on camera position. The stream unload gate NOP at 0x415C51 should prevent this, but the stream may never have been loaded in the first place.

3. **Per-object visibility flags**: Each object has a visibility bitfield at [obj+8]. The proxy NOPs the `test bit 0x10` checks, but other bits (0x01, 0x02, 0x04) may gate rendering independently.

4. **Sector bitmask incompleteness**: Post-sector bitmask stamped to 0xFFFFFFFF, but the initial sector traversal may set per-object flags before our patches run.

5. **Light mesh vs building mesh**: The light anchor meshes may be in a separate render list (e.g., dynamic objects) that follows a different cull path than static geometry.

## Open Hypotheses

1. **Portal traversal is the root blocker**: The sector-based PVS system (not individual object culling) determines which sectors submit geometry. Light anchor meshes are in sectors that become invisible when the camera rotates. All individual cull NOPs are downstream of the sector selection — if a sector isn't traversed, its objects never reach the cull function.

2. **Phase 1 timing bug**: The 15s load wait is insufficient for Remix+Peru. Need 25-30s minimum, or detect gameplay start (first valid draw call from proxy log) before sending cutscene skip.

## Next Steps

1. **Fix Phase 1 timing**: Increase load wait to 25s or add gameplay detection
2. **Update test checklist**: Remove 0x407150=C3 and 0x60B050=B001C204 expectations; replace with actual proxy patch verification (NOPed jumps, stamped values)
3. **Investigate portal traversal**: The portal/PVS system is the most likely remaining blocker. Need to trace the sector graph to find which portal gates prevent light mesh sectors from being visited.
4. **Try forced sector loading**: Stamp all sector enable flags and trace which sectors contain the light anchor meshes
