## Result

**FAIL-lights-missing** -- No red or green stage lights visible in any clean render screenshot.

## Test Configuration

- Test type: Hash Stability Test (camera-only pan, no WASD)
- Level: Peru (Chapter 4, -NOMAINMENU)
- Camera motion: 300px left, 600px right (nets 300px right of center)
- Debug view: 277 (Phase 1), 0 (Phase 2)
- useVertexCapture: False
- antiCulling: Disabled (object + light)
- Build tool: `python patches/TombRaiderLegend/run.py test --build`

## Phase 1: Hash Debug Analysis

3 screenshots captured at center/left/right camera positions.

Hash colors appear **stable** across all 3 positions -- same colored geometry blocks maintain consistent colors as camera pans. No obvious hash-shift detected.

Camera did move: perspective shift visible between shots (building edges shift relative to frame).

## Phase 2: Light Anchor Analysis

3 screenshots captured at center/left/right camera positions.

**NO red or green stage lights visible in ANY screenshot.** Only brown/tan building geometry with ambient lighting. The mesh hashes that Remix lights are anchored to are not being rendered.

Light anchor hashes expected:
- `mesh_5601C7C67406C663` (Red)
- `mesh_ECD53B85CBA3D2A5` (Red)
- `mesh_AB241947CA588F11` (Green)
- `mesh_EFD9D357F2D3A56F` (Green)
- `mesh_D4A147BEEBC48792` (Red)

## Phase 3: Live Diagnostics

### Draw Call Census

**dipcnt failed to install** at all 3 camera positions. Livetools reported "Not installed" for each attempt. Proxy log shows ~650-657 draws per diagnostic sample (relatively stable, <2% variance).

### Patch Integrity

| Address | Expected | Actual | Status |
|---------|----------|--------|--------|
| 0xEFDD64 | -1e30 float | -1e30 | PASS -- frustum threshold correct |
| 0xF2A0D4/D8/DC | D3DCULL_NONE (1) | 1, 1, 1 | PASS -- cull modes correct |
| 0x407150 | C3 (RET) | 55 (PUSH EBP) | BY DESIGN -- proxy NOPs internal jumps, doesn't RET the function |
| 0x60B050 | B0 01 C2 04 | 55 8B EC 83 | BY DESIGN -- light patches intentionally disabled (crash risk) |

### Memory Watch

SetWorldMatrix trace at 0x413950: 70,732 records in 15s. Caller 0x4150DF confirmed.

### Function Collection

Single address collected: 0x00413950 (SetWorldMatrix) with 70,732 hits over 15.1s (~4,680/s).

## Phase 4: Frame Capture Analysis

Skipped in this build version.

### Draw Call Diff

N/A

### Constant Evolution

N/A

### Vertex Format Consistency

N/A

### Shader Map

N/A

## Phase 5: Static Analysis

On-disk binary verified:
- 0x407150: Original prologue `55 8B EC 83` intact (proxy patches at runtime)
- 0x4070F0: Shows tail of prior function, not a patch site -- actual NOP targets are inside 0x407150 body
- 0x60B050: Original prologue `55 8B EC 83` intact (light patch intentionally disabled)

All on-disk bytes match originals. Runtime patches are proxy-applied.

## Phase 6: Vision Analysis

**Hash debug (Phase 1):** Same colored blocks appear in consistent spatial arrangement across all 3 images. Hash stability appears maintained.

**Clean render (Phase 2):** No red or green lights visible in any screenshot. Only brown/tan building geometry with diffuse ambient lighting. The geometry carrying the light anchor hashes is not being submitted to the renderer.

## Proxy Log Summary

- Proxy loaded successfully, Remix chain-loaded
- 17+ patches applied: frustum threshold, 11 cull jump NOPs, null-check trampoline, sector visibility, proximity filter, terrain gate, mesh visibility gate, post-sector patches, mesh eviction NOPs
- Draw counts: ~650-657 per sample (stable)
- View/Proj matrices valid at startup
- Light system patches explicitly disabled (crash at 0xEE88AD)

## Brainstorming: New Hash Stability Ideas

1. **The missing geometry may be in a different rendering path** -- the proxy patches cover SceneTraversal, sector visibility, post-sector loop, and terrain. But the light-anchor meshes might be submitted through a fourth path (e.g., dynamic objects, overlays, or a separate mesh list) that isn't patched.

2. **Mesh streaming/LOD** -- even though stream unload gate is NOPed, the mesh data for distant sectors might never be loaded in the first place. The patches prevent unloading but don't force loading.

3. **The draw count (~650) is suspiciously low** for a scene with all culling disabled. Previous builds with more geometry visible had higher counts. Some submission path is still gated.

4. **DrawCache replay** -- proxy log shows "DrawCache: replayed 3 culled draws". The draw cache mechanism could be interfering with geometry that should render every frame.

## Open Hypotheses

1. **Mesh data not loaded**: The light-anchor meshes are in sectors that never got their mesh data streamed in. Patches prevent eviction but can't force initial loading. Need to investigate the mesh streaming init path.

2. **Fourth rendering path**: There may be an additional object submission path beyond SceneTraversal/Sector/PostSector that handles the specific mesh types the lights are anchored to.

3. **Object type filtering**: The objects carrying light-anchor hashes may have a flag or type that causes them to be filtered at a point we haven't patched (e.g., in the actual DIP routing in the proxy itself).

4. **Camera position**: Peru spawn point may not be close enough to the stage area for the light-anchor geometry to be in the initial streaming set.

## Next Steps

1. Use livetools to search for the light anchor hash values in live memory -- determine if the meshes exist in the scene graph at all
2. Trace the sector mesh loading path to see if distant sector mesh data is being requested
3. Compare draw call backtraces at spawn vs. near-stage to identify which submission path handles the missing geometry
4. Consider a dx9tracer near/far differential capture to identify exactly which draws disappear
