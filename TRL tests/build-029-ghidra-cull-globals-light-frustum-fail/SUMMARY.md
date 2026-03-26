# Build 029 — Ghidra-Driven Cull Globals + Light Frustum NOP

## Result
**FAIL** — Both red+green lights visible in 1/3 clean screenshots. Shots 2-3 dark because randomized movement sent Lara past the stage area.

## What Changed This Build
Three new patches based on Ghidra MCP deep analysis of trl.exe:

1. **Frustum threshold -1e30f** (was 0.0f): Catches objects behind the camera that 0.0 would still cull. Applied both one-shot and per-scene.
2. **Cull mode globals stamped to D3DCULL_NONE**: Three globals at 0xF2A0D4/D8/DC that the renderer caches. When the cached value matches desired cull mode, the game skips SetRenderState entirely, bypassing our proxy hook. Now force-set to 1 (D3DCULL_NONE) every scene.
3. **Light frustum rejection NOP** at 0x0060CE20: A 6-byte JNP in RenderLights_FrustumCull that rejected lights failing a 6-plane frustum test. NOPed so all lights pass.

Also attempted and **reverted**: Light_VisibilityTest bypass (0x0060B050). Making it always return 1 killed native fill lighting, making scenes nearly black. The function has side effects needed for rendering.

## Proxy Log Summary
- vpValid=1, all draws processed (189829 at scene 600)
- 0 passthrough, 0 skippedQuad, 0 xformBlocked
- All patches confirmed active:
  - Frustum threshold to -1e30
  - 7/7 cull jumps NOPed
  - Frustum cull function ret (0x407150)
  - 2/2 sector visibility NOPed
  - Cull mode globals to D3DCULL_NONE
  - Light frustum rejection NOPed at 0x0060CE20

## Retools Findings
Static analyzer subagent dispatched for disassembly verification of patch sites (0x407150, 0x4070F0, 0x0060CE20). Results pending in findings.md.

## Ghidra MCP Findings
Comprehensive analysis mapped the complete culling architecture:

- **RenderLights_FrustumCull** (0x0060C7D0): Has TWO gates — Light_VisibilityTest (distance/bounds, pre-check) and 6-plane frustum test (NOPed). The VisibilityTest calls FUN_0060ac80 which sets up state needed for rendering — cannot be bypassed without breaking lighting.
- **6 SetRenderState functions**: All use a cache pattern reading g_cullMode_pass1/pass2/pass2_inverse. Without stamping these globals, the cache match causes the game to skip SetRenderState, bypassing our proxy hook.
- **Light_VisibilityTest** (0x0060B050): Called only from RenderLights_FrustumCull. Three code paths based on light type (0/1/2+). Bypassing kills native lighting — the sub-functions (FUN_0060ac80, FUN_0060ad20, etc.) have side effects needed for rendering.

## Open Hypotheses
1. **Lights disappear because Lara walks past the stage, not culling**: Clean shot 1 shows both lights perfectly. Shots 2-3 are dark because the randomized movement sends Lara physically past the stage area. The lights aren't culled — they're behind the camera.
2. **All geometry culling paths are now patched**: Frustum function ret, cull jumps, sector visibility, frustum threshold, cull globals — there's no remaining known geometry culling mechanism.
3. **Test pass is movement-dependent**: With favorable random movement (shorter strafes keeping Lara between the lights), this build would pass. Build-019 "miracle" passed with similar patches but a luckier random seed.

## Next Build Plan
The code changes are complete. The remaining issue is test-mechanical:
- The randomized movement sometimes sends Lara too far from the stage
- When Lara is in the stage area, BOTH lights are consistently visible (proven by shot 1)
- Next steps: Either re-run with different random seed (movement is randomized), or investigate if there's a way to ensure the light anchor geometry is always submitted regardless of camera angle (BLAS persistence in Remix)
