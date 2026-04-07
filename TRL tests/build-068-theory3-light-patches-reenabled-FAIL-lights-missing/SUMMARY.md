## Result

**FAIL-lights-missing** across all 3 theories. No red or green stage lights visible.

## Three Theory Test (Builds 066-068)

### Theory 1 (Build 066): Disable Draw Cache
- **Hypothesis:** The 4096-entry draw cache replays draws with stale COM resource pointers (VB/IB/texture freed by game between frames), causing textures to disappear.
- **Change:** `DRAW_CACHE_ENABLED 0`
- **Result:** No change. Same brown/tan buildings, no lights. Hash debug stable.
- **Conclusion:** Draw cache is not causing texture absence. The cache only replays 3 draws and the stale pointer concern was unfounded — the game doesn't free these resources between frames.

### Theory 2 (Build 067): Remove VP Inverse Cache Threshold
- **Hypothesis:** The 1e-4 epsilon in `mat4_changed()` means small camera movements don't trigger VP inverse recalculation → stale world matrices → hash drift.
- **Change:** Removed threshold, always recalculate VP inverse.
- **Result:** No change. Hash debug identical to baseline. Clean render still no lights.
- **Conclusion:** VP inverse cache threshold is not contributing to hash instability. The threshold is fine — VP changes are large enough on camera pan to always trigger recalculation.

### Theory 3 (Build 068): Re-enable Light System Patches
- **Hypothesis:** LightVisibilityTest, sector light gate, and RenderLights gate patches were disabled citing crash at 0xEE88AD. Other patches added since (ProcessPendingRemovals fix, null-check trampoline) may have fixed the underlying crash.
- **Change:** Re-enabled all 3 light patches:
  - `Light_VisibilityTest` at 0x60B050 → `mov al, 1; ret 4`
  - Sector light count gate NOP at 0xEC6337
  - RenderLights gate NOP at 0x60E3B1
- **Result:** **No crash!** All 3 patches confirmed active in proxy log. BUT still no lights visible.
- **Conclusion:** The crash was indeed caused by something else (likely ProcessPendingRemovals stale field_48). Light patches are safe to keep. However, they don't solve the visibility problem because the mesh geometry carrying light-anchor hashes is never submitted to the renderer.

## Key Finding

All three light pipeline gates are now unblocked AND stable. The problem is definitively **upstream of the light rendering pipeline** — the mesh geometry that Remix lights are anchored to is not being drawn. This confirms the whiteboard's Priority 1: hash instability from useVertexCapture is the fundamental blocker, not missing culling patches.

## Proxy Log Confirmation (Theory 3)

All 20+ patches confirmed active:
- Frustum threshold -1e30
- 11 cull jump NOPs
- Null-check trampoline at 0xEDF9E3
- ProcessPendingRemovals fix
- Sector visibility NOPs (2)
- Sector-object proximity filter NOP
- Sector already-rendered skip NOP
- **Light_VisibilityTest always TRUE** (NEW)
- **Sector light count gate NOP** (NEW)
- **RenderLights gate NOP** (NEW)
- Terrain cull gate NOP
- MeshSubmit_VisibilityGate → return 0
- Post-sector loop enabled
- Stream unload gate NOPed
- Post-sector bitmask/distance culls NOPed
- Mesh eviction NOPed

## Next Steps

1. **Keep Theory 3 changes** — light patches are safe and should stay enabled
2. **Focus on hash instability** — the real blocker is `useVertexCapture=True` producing clip-space hashes
3. **Debug SHORT4→FLOAT3 CPU expansion** — the proxy has the cache but rendering issues remain with `useVertexCapture=False`
4. **Investigate mesh streaming** — are the anchor meshes even loaded into memory?
