# Build 032 — Light Culling Config Flag (No Effect)

## Result
**FAIL** — Same as build 031. Both lights at baseline, dark when Lara moves far. Config flag had no effect.

## What Changed This Build
- Added stamp of engine config flag at `0x01075BE0 = 1` ("Disable extra static light culling and fading")
- Found via config table at `0xF1325C` referencing string at `0xEFF384`

## Proxy Log Summary
- All patches confirmed including new flag: "Set light culling disable flag at 0x01075BE0"
- Draw counts same as build 031 (1,416-189,960)
- vpValid=1, no crashes

## Retools Findings
- Pending (subagent analyzing light list population code)

## Ghidra MCP Findings
- `RenderScene_Main` (0x603810) iterates sector array, gates on `sector+0x84 + sector+0x94 != 0`
- `RenderScene_TopLevel` (0x60A0F0) calls `FUN_006033d0()` and `FUN_00602aa0()` before `RenderScene_Main` — these likely populate per-sector light lists
- Config flag at 0x01075BE0 has no direct code xrefs — likely accessed through config table lookup but may not control what we need
- The per-sector light list (`+0x1B0` count, `+0x1B8` array) is the confirmed bottleneck

## Open Hypotheses
1. **Light list builder function**: One of `FUN_006033d0` or `FUN_00602aa0` (called before RenderScene_Main) builds per-sector light lists. Need to find and patch the proximity/sector filter there.
2. **Field +0x84 setter**: Something sets `sector+0x84` each frame to flag "this sector has lights." Finding that setter and forcing it on for all sectors would help, but the light count +0x1B0 also needs to be non-zero.
3. **Nuclear approach**: Patch RenderScene_Main or RenderLights_FrustumCull to iterate a global light list instead of per-sector.

## Next Build Plan
- Wait for static analyzer findings on who writes +0x1B0 and +0x1B8
- Decompile `FUN_006033d0` and `FUN_00602aa0` to find the light collection function
- Patch the light collection to include ALL lights in ALL sectors
