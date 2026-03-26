# Build 025 — pending-flag-nop-same-result

## Result

**FAIL** — Same pattern as build-024: shot 1 (initial position) shows BOTH red and green stage lights, shot 2 shows green only, shot 3 is black. Adding Layer 5 patches (pending-render flag bypasses) had NO effect, confirming the bottleneck is not in the caller chain but inside the light's own Draw virtual method.

## What Changed This Build

Added Layer 5: two new NOP patches targeting the "pending-render flag" gates upstream of `RenderLights_FrustumCull`:

- **0x603832: JZ (74 0B) → NOP** — in `FUN_00603810`, bypasses the check that skips lights when `(light+0x94)+(light+0x84)==0`. Forces ALL lights in the scene list into `FUN_0060E2D0`.
- **0x60E30D: JZ (74 2B) → NOP** — in `FUN_0060E2D0`, bypasses the check that requires `light+0x84!=0` before calling `RenderLights_FrustumCull`. Forces the render-gate variable to always be set.

Active patches this build (all 7):
1. 0x407150: RET (frustum cull function)
2. Frustum threshold → 0.0
3. Scene traversal cull jumps: 7 NOPs
4. 0x60CDE2: 2 NOPs (light broad-visibility skip)
5. 0x60CE20: 6 NOPs (light frustum plane test)
6. **0x603832: 2 NOPs** (NEW — scene-list pending-flag skip)
7. **0x60E30D: 2 NOPs** (NEW — render-gate pending-flag check)

## Proxy Log Summary

- All 7 patches applied ✓ (including both new Layer 5 patches)
- vpValid=1 throughout
- skippedQuad=0
- No crashes
- Movement: A hold 1838ms, D hold 1554ms (short holds, Lara stays close to center)

## Retools Findings (from static-analyzer subagent)

Build-024 static-analyzer completed deep analysis (appended to findings.md):

1. On-disk bytes at all patch sites verified as unmodified — all patches are runtime-only.
2. The caller at 0x60E2D0 has an outer gate at 0x60E3B1 that skips `RenderLights_FrustumCull` if `[ebx+0x1B0]` (light COUNT) is zero. This is a count check, not per-light — does not explain individual light disappearance.
3. `RenderLights_FrustumCull` has TWO draw paths: immediate (mode=1) and deferred (mode=0). Current NOPs force all to immediate.
4. **Most likely root cause: the light's Draw virtual method (`vtable[0x18]`)** contains its own internal culling. When the Draw method is called, it may internally decide not to render based on camera/screen-space position.

## Ghidra MCP Findings

Full call chain decompiled and disassembled:

| Function | Address | Role |
|----------|---------|------|
| `FUN_00603810` | 0x603810 | Outer loop: iterates light list, checks `+0x84`/`+0x94` flags |
| `FUN_0060E2D0` | 0x60E2D0 | Per-light setup: checks `+0x84`, sets render states, calls frustum cull |
| `FUN_0060C7D0` | 0x60C7D0 | `RenderLights_FrustumCull`: 6-plane test, draws via `vtable[0x18]` |

Key assembly at 0x60CE35-0x60CE42 (inside `RenderLights_FrustumCull`):
```asm
mov eax, [esi]        ; load vtable pointer
push 1                ; mode = immediate draw
push ...              ; camera data
call [eax+0x18]       ; vtable[6] = Draw method
```

The Draw method is a VIRTUAL CALL on the light object. Each light type (spotlight, pointlight, directional) may have a different implementation. The method receives camera position data and may internally skip rendering if the light is behind the camera.

## Open Hypotheses

1. **Light Draw method has internal view-frustum clipping (STRONGEST)**: The `vtable[0x18]` Draw call receives camera data and likely performs its own screen-space or clip-space test before submitting geometry. When the camera rotates (A key = rotate in TRL), lights behind the camera are clipped by the Draw method itself, not by any of the callers we've patched.

2. **A key = ROTATE, not strafe**: In TRL, the A/D keys cause Lara to turn (rotate camera), not strafe sideways. Even 1.8 seconds of turning is enough to rotate 90+ degrees, putting lights behind the camera. This explains why even very short movement destroys the lights.

3. **Layer 5 patches are unnecessary but not harmful**: The `+0x84` pending flag WAS being set correctly for all visible lights. Bypassing it didn't change behavior because `FUN_0060E2D0` was already being called for the stage lights.

## Next Build Plan

Build-026: Patch the light Draw virtual method (`vtable[0x18]`) internal culling.

**Step 1 — Identify the Draw method address:**
- Static-analyzer is investigating the light vtable structure
- Search for the concrete function at vtable offset 0x18 for stage light objects
- Use RTTI, string search ("light", "spot"), or trace the object creation path

**Step 2 — Decompile the Draw method:**
- Look for any conditional skip before DrawPrimitive/DrawIndexedPrimitive calls
- Look for screen-space position tests, clip-space checks, or early returns
- The culling condition is likely a simple comparison (e.g., z < 0, behind camera)

**Step 3 — NOP the internal culling:**
- Patch the JZ/JNZ that prevents the Draw method from submitting geometry
- This should force ALL lights to submit their geometry to D3D regardless of camera angle

Expected result: With Draw method culling disabled, both stage lights should submit geometry to RTX Remix in ALL 3 screenshots regardless of Lara's rotation. The path tracer will then create proper lights from the emissive geometry.
