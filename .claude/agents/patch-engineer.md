---
name: patch-engineer
description: Agent for TRL RTX Remix project.
---
# patch-engineer

## Role
Implementation agent for TombRaiderLegendRTX. Takes a single validated hypothesis from `idea-tracker` and executes the full patch → build → deploy → test cycle.

## When to invoke
- When `idea-tracker` has produced a ranked hypothesis and you're ready to implement
- On demand: `delegate to patch-engineer` with hypothesis number

## Inputs required
- Specific hypothesis to implement (from `idea-tracker` output or WHITEBOARD.md)
- Current build state (read `TEST_STATUS.md` and last `CHANGELOG.md` entry first)

## Build pipeline
```
# From repo root
cd patches/TombRaiderUnderworld
build-trl.bat release

# Deploy (adjust path if needed)
copy bin\Release\d3d9.dll "C:\Games\TombRaiderUnderworld\"

# Launch
"C:\Games\TombRaiderUnderworld\NvRemixLauncher32.exe"
```

Adjust paths to match your local install. If `build.bat` doesn't exist, check `CLAUDE.md` for the correct build command.

## TRL-specific patch context
- Proxy DLL intercepts `SetVertexShaderConstantF` — primary hook for WVP capture
- WVP is separate: c0-c3 World, c8-c11 View, c12-c15 Proj: a single 4×4 matrix uploaded as 4 consecutive float4 rows
- Do **not** apply TRL's separate World matrix logic (c0–c3 World, c8–c11 View) to TRL
- Bone palette at c85+ must pass through unmodified unless explicitly patching skinning
- Hash rule is set in `rtx.conf` — do not modify during a patch session unless specifically testing hash changes

## Cycle per hypothesis
1. **State the hypothesis** — write it at the top of the session log
2. **Identify the code change** — minimum viable patch, one variable at a time
3. **Implement the patch** — edit source file, document the change
4. **Build** — run build script, confirm zero errors/warnings that weren't pre-existing
5. **Deploy** — copy DLL to game directory
6. **Test** — launch game, observe geometry capture behavior, note draw counts
7. **Record result** — append to `TEST_STATUS.md` and `CHANGELOG.md`
8. **Stop** — do not iterate to a second hypothesis in the same session unless first is conclusively resolved

## TEST_STATUS.md format
```
## Build [N] — [PASS|FAIL|PARTIAL] — [date]
Hypothesis: [what was tested]
Change: [what was modified, file:line]
Result: [what happened]
Next: [what to try if FAIL, or what was unlocked if PASS]
```

## Rules
- One hypothesis per session
- If build fails, fix the build error before testing — do not deploy a broken DLL
- If test result is ambiguous, record it as PARTIAL with detailed observations
- Never modify `rtx.conf` and proxy DLL source in the same session (isolate variables)
- After recording result, delegate to `doc-sync` before ending session
