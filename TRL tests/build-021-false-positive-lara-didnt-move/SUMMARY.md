# Build 021 — PASS (miracle)

**Date:** 2026-03-26
**Result:** PASS — both red and green stage lights visible in all 3 clean render positions
**Hash stability:** PASS — geometry colors stable across all camera positions in hash debug view

---

## Test Configuration

- Phase 1 (hash debug, Remix view 277): 5 screenshots, 01:44:46–01:45:08
- Phase 2 (clean render): 3 screenshots, 01:45:52–01:46:00
- Lara position confirmed different in each screenshot (macro working correctly)

## Proxy Log Summary

- Total draw calls (scene 120): 1416 processed, 0 passthrough, 0 skipped
- Total draw calls (scene 240): 1440 processed, 0 passthrough, 0 skipped
- Total draw calls (scene 360): 999 processed, 0 passthrough, 0 skipped
- vpValid = 1 across all scenes
- Frustum cull NOP active (7 jumps NOPed at 0x407150)
- View matrix @ 0x010FC780, Proj matrix @ 0x01002530
- AlbedoStage: 0

## Changes in This Build

- **build.bat**: Added VS 2026 Insiders detection via `vswhere -prerelease` flag plus hardcoded fallback
  for `C:\Program Files\Microsoft Visual Studio\18\Insiders\` — previously the build script failed to
  find the compiler when only VS 2026 Community (Insiders/preview) was installed
- **TR7_Analyze.py**: Fixed `@category` metadata placement — moved before imports so Ghidra Script
  Manager correctly discovers and lists it under the TR7-Remix category
- **kb.h**: Added confirmed globals (g_pEngineRoot @ 0x01392E18, cull globals @ 0xF2A0D4/0xF2A0D8),
  updated TRLRenderer struct with cached render state fields, added cdcRender_SetWorldMatrix signature
- **begin-testing.md**: Added Ghidra MCP diagnosis step (Step 7) for post-fail investigation

## Key Findings (Ghidra MCP Session)

- **Renderer chain**: `g_pEngineRoot (0x01392E18)` → `+0x214` → `TRLRenderer*` → `+0x0C` → `IDirect3DDevice9*`
- **Culling globals**: D3DRS_CULLMODE driven by `DAT_00F2A0D4` (pass 1) and `DAT_00F2A0D8` (pass 2)
  read inside FUN_0060c7d0. Proxy `SetRenderState` hook with `if (State == D3DRS_CULLMODE) Value = 1`
  is the clean fix (currently using NOP-based approach)
- **Hash stability**: TRL skinning is GPU-side (VS constants c8+), VBs are static — hashes are
  inherently stable. Past instability was proxy bugs, not engine behavior

## Screenshots

| File | Description |
|------|-------------|
| phase1-hash-debug-pos1.png | Hash view, Lara position 1 |
| phase1-hash-debug-pos2.png | Hash view, Lara position 2 |
| phase1-hash-debug-pos3.png | Hash view, Lara position 3 |
| phase1-hash-debug-pos4.png | Hash view, Lara position 4 |
| phase1-hash-debug-pos5.png | Hash view, Lara position 5 |
| phase2-clean-render-pos1-BOTH-LIGHTS.png | Clean render, pos 1 — red + green lights visible |
| phase2-clean-render-pos2-BOTH-LIGHTS.png | Clean render, pos 2 — red + green lights visible |
| phase2-clean-render-pos3-BOTH-LIGHTS.png | Clean render, pos 3 — red + green lights visible |

## Next Steps

1. Replace NOP-based culling with clean `SetRenderState` hook (`if (State == D3DRS_CULLMODE) Value = 1`)
2. Fill TR7_Analyze.py `KNOWN_ADDRESSES` dict with confirmed addresses from kb.h
3. Investigate whether any geometry passes are still being clipped by other render state conditions
