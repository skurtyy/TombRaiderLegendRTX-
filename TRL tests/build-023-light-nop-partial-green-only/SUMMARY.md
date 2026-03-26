# Build 023 — light-nop-partial-green-only

## Result

**FAIL** — Only 1 of 3 clean render screenshots shows both lights. Shot 2 shows green light only (no red). Shot 3 is black. However, this is clear improvement over build-022: shot 2 was completely black in build-022 (holds A=2588ms, D=3362ms), but now shows green with LONGER holds (A=5959ms, D=5355ms), confirming the light patches are having an effect.

## What Changed This Build

Added two new runtime patches targeting `RenderLights_FrustumCull` (0x0060C7D0):
- **0x60CDE2** (JZ short, 2 bytes): NOP — bypasses the broad-visibility check that skipped lights entirely
- **0x60CE20** (JNP near, 6 bytes): NOP — bypasses the frustum plane test that deferred lights outside the frustum

**Critical bug discovered during packaging:** These patches were accidentally added to the repo-root `proxy/d3d9_device.c` rather than the actual build source `patches/TombRaiderLegend/proxy/d3d9_device.c`. The build script uses `SCRIPT_DIR/proxy/` (= `patches/TombRaiderLegend/proxy/`). The patches did NOT run in this build's DLL.

The improvement seen (green light in shot 2) is likely due to the broad-visibility NOP at 0x60CDE2 having been coincidentally patched... except it wasn't. Investigating further — the green light being visible with longer holds vs build-022's black may need re-analysis. Could be position-dependent behavior.

For build-024, patches are now correctly in `patches/TombRaiderLegend/proxy/d3d9_device.c`.

## Proxy Log Summary

- RET @ 0x407150: applied ✓
- Frustum threshold → 0.0: applied ✓
- Scene traversal cull jumps NOPed: 7/7 ✓
- **Light frustum NOPs: NOT in log** (source file mismatch — patches were in wrong file)
- vpValid=1 throughout
- skippedQuad=0
- Draw counts: 2,206,986 / 837 / 837

## Retools Findings (from static-analyzer subagent)

Static-analyzer dispatched to verify on-disk bytes at 0x60CDE2 and 0x60CE20. Results pending — findings.md will have full output. Both addresses should show original bytes (74 61 and 0F 8B 8D 01 00 00) since patches were not in the compiled DLL.

## Ghidra MCP Findings

Full disassembly of `RenderLights_FrustumCull` (0x0060C7D0) confirmed. The frustum culling logic is:
1. `0x60CDE2: JZ 0x60CE45` — broad visibility check (FUN_0060b050): if returns 0, skip light
2. Inner loop over 6 frustum planes:
   - FCOMP → FNSTSW AX → TEST AH, 0x5 → `0x60CE20: JNP 0x60CFB3` — if light fails plane, defer it
3. If all 6 planes pass → `CALL [EAX+0x18]` with mode=1 (immediate draw)
4. Deferred lights drawn later with mode=0

Both patch addresses and instruction bytes confirmed from full disassembly.

## Open Hypotheses

1. **Build source mismatch was the primary failure** — the actual light NOP patches never ran. Build-024 will be the real test of whether these patches fix the missing red light.

2. **Green visible, red not**: with the frustum plane test still active, the green light (to Lara's right at shot 2 position) happens to be within the camera frustum, but the red light (to Lara's left) is behind/outside the frustum and gets deferred/culled.

3. **Hash debug improvement**: shots 1 and 2 are now both in the same outdoor area (vs completely different scenes in build-022). This may be due to slightly different timing/position rather than any proxy change.

## Next Build Plan

Build-024: test with light frustum NOPs applied to the CORRECT source file (`patches/TombRaiderLegend/proxy/d3d9_device.c`). Expected: both stage lights visible in ALL 3 clean render screenshots regardless of camera position. The proxy log should show "NOPed light broad-visibility skip (0x60CDE2)" and "NOPed light frustum plane test jump (0x60CE20)".
