# "Begin Testing" Trigger

When the user says **"begin testing"**, **"run tests"**, **"start testing"**, or **"test the build"**, immediately execute this workflow without asking questions:

## Workflow

1. **Build + test**: Run `python patches/TombRaiderLegend/run.py test --build --randomize`
2. **Read proxy log**: Check for crashes, skipped draws, patch activation
3. **View ALL screenshots**: Read every Phase 1 (hash debug) and Phase 2 (clean render) screenshot
4. **Verify movement**: Confirm Lara is in a **different position** in each of the 3 screenshots per phase. Same position = false positive, macro failed — investigate input delivery
5. **Evaluate against success criteria**:
   - Hash debug: same geometry must keep same color across all 3 positions
   - Clean render: both red AND green stage lights must be visible in ALL 3 screenshots **AND the lights must shift position across the 3 screenshots** — if the lights are on the same side of the frame in all 3 shots, Lara hasn't moved and it's a false positive even if both lights appear
6. **False positive detection**: If clean render shows both lights in all 3 screenshots but Lara's legs/feet haven't moved and the lights stay on the same sides of the frame — that is a **false positive** (FAIL). A real PASS requires the lights to shift left/right relative to Lara as she walks between them, proving actual movement occurred.
7. **Determine result**: PASS only if all criteria met. Any missing light, hash shift, or false positive = FAIL
8. **On FAIL — diagnose with Ghidra MCP before touching code**: If the Ghidra MCP is available
   (`mcp__ghidra__list_programs` returns trl.exe), use it immediately to investigate the failure
   before proposing any code changes. Do NOT spawn a static-analyzer subagent for trl.exe — the
   MCP is faster and has the binary already loaded. Examples:
   - Hash shift on a draw call → query which function submits that geometry, check if it's a
     dynamic VB path or a double-submission from the proxy
   - Missing light → decompile the light dispatch function to see what render state is blocking it
   - Proxy log shows unexpected skip → find the condition in the engine that triggers the skip
   Use `mcp__ghidra__get_code`, `mcp__ghidra__xrefs`, `mcp__ghidra__search_bytes` as needed.
   Summarize what the engine is doing and propose a targeted fix before packaging the build.
9. **Package build**: Create `TombRaiderLegendRTX-/TRL tests/build-NNN-<description>/` with screenshots (renamed descriptively), proxy log, and SUMMARY.md
10. **Commit + push**: Push to `skurtyyskirts/TombRaiderLegendRTX-` immediately — every build gets uploaded, pass or fail

## Build Numbering

- Check existing builds in `TombRaiderLegendRTX-/TRL tests/` and increment
- PASS builds: include "miracle" in the folder name
- FAIL builds: include the failure reason (e.g., "lights-partial-fail")

## No Questions

Do not ask the user to launch the game, copy files, or confirm anything. The entire pipeline is automated. Just run it and report results.
