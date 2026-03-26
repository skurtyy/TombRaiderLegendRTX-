# Build 026 — vis-state-nop-red-light-still-culled

## Result

**FAIL** — Same pattern as builds 024-025: clean render shot 1 shows both red and green stage lights, shots 2-3 show green only. The red light is still culled when Lara moves away. New LightVolume_UpdateVisibility patches were added to the source but did NOT appear in the proxy log, suggesting the patches either failed to apply or the code path was not reached during initialization.

## What Changed This Build

Added Layer 6: LightVolume_UpdateVisibility (0x6124E0) visibility-state check NOPs. This function writes intensity/visibility data into render command buffer slots. Each slot has a visibility state check (`cmp visState, 1; jg skip_slot`) where values > 1 mean "frustum-culled". Five patch sites (9 bytes each: 3-byte CMP + 6-byte conditional near jump) were NOPed:

- 0x006125EC: unrolled slot 1
- 0x0061264C: unrolled slot 2
- 0x006126AA: unrolled slot 3
- 0x00612701: unrolled slot 4
- 0x0061279A: remainder slot

**Bug:** These patches compiled into the DLL but their log messages do NOT appear in ffp_proxy.log. The 4 previously-existing light patches (0x60CDE2, 0x60CE20, 0x603832, 0x60E30D) all logged correctly. The new visibility patches may have silently failed (VirtualProtect returned 0) or were not reached in the execution flow.

Active patches this build (attempted 12, confirmed 7+5 attempted):
1. 0x407150: RET (frustum cull function)
2. Frustum threshold -> 0.0
3. Scene traversal cull jumps: 7 NOPs
4. 0x60CDE2: 2 NOPs (light broad-visibility skip)
5. 0x60CE20: 6 NOPs (light frustum plane test)
6. 0x603832: 2 NOPs (scene-list pending-flag skip)
7. 0x60E30D: 2 NOPs (render-gate pending-flag check)
8-12. 5x visibility-state NOPs at 0x6125EC-0x61279A (NOT confirmed in log)

## Proxy Log Summary (draw counts, vpValid, patch addresses)

- Draw counts: 1416-1440 per scene (full scenes), dropping to 119-120 in later scenes (expected: menu/loading transitions)
- vpValid=1 throughout all reported scenes
- skippedQuad=0, passthrough=0, xformBlocked=0
- No crashes
- All 7 original patches confirmed in log
- 5 new visibility patches NOT in log (silent failure suspected)

## Retools Findings (from static-analyzer subagent)

Static analyzer verified on-disk bytes at all confirmed patch addresses. The on-disk code is unmodified (patches are runtime-only via VirtualProtect). Disassembly at:
- 0x407150: original function prologue intact on disk (patched to RET at runtime)
- 0x60CDE2: JE instruction present on disk (NOPed at runtime)
- 0x60CE20: JNP instruction present on disk (NOPed at runtime)
- 0x603832: JE instruction present on disk (NOPed at runtime)
- 0x60E30D: JE instruction present on disk (NOPed at runtime)

## Ghidra MCP Findings

No Ghidra MCP server was available this session. Previous session findings (build-025) remain valid: the light Draw virtual method at `vtable[0x18]` (called from 0x60CE35) is the most likely remaining culling path. The Draw method receives camera data and may internally skip rendering for lights behind the camera.

## Open Hypotheses

1. **Visibility-state patches failed silently (INVESTIGATE FIRST)**: The 5 new NOP sites at 0x6125EC-0x61279A did not log. Possible causes: (a) VirtualProtect failed for that address range, (b) the code block where these patches are applied wasn't reached during `TRL_ApplyMemoryPatches`, (c) the addresses are wrong. Must verify the patch application before concluding they have no effect.

2. **Light Draw virtual method has internal culling (from build-025, STRONGEST if vis patches are confirmed applied)**: The `vtable[0x18]` Draw call at 0x60CE35 receives camera position data and likely performs its own screen-space or clip-space test. When the camera rotates (A/D keys in TRL), lights behind the camera are clipped by the Draw method itself.

3. **A/D keys = ROTATE, not strafe**: In TRL, A/D causes Lara to turn (rotate camera), not strafe. Even short holds rotate 90+ degrees, putting lights behind the camera. This explains why lights disappear so quickly.

## Next Build Plan

**Step 1 — Debug the silent patch failure:** Add explicit error logging to the visibility-state NOP loop. Check if `VirtualProtect` returns 0 for any address. Log the old protection value and the exact bytes at each site before patching.

**Step 2 — If patches ARE applying but have no effect:** The culling is deeper than the visibility-state checks. Focus on the vtable[0x18] Draw method:
- Use static analyzer to identify the concrete function at vtable offset 0x18 for stage light objects (RTTI on the light vtable)
- Decompile the Draw method and find internal frustum/clip tests
- NOP the internal culling conditional

**Step 3 — Alternative approach:** Instead of chasing ever-deeper culling paths, consider forcing the light objects' visibility state to "always visible" by writing directly to the light object's memory fields at runtime, before the render loop reads them.
