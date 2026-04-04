# "Begin Testing" Trigger

When the user says **"begin testing"**, **"run tests"**, **"start testing"**, or **"test the build"**, immediately execute this workflow without asking questions:

## Workflow

1. **Build + test**: Run `python patches/TombRaiderLegend/run.py test --build --randomize`

   The test script handles three phases automatically:
   - **Phase 1**: Hash debug screenshots (debug view 277) with randomized A/D movement
   - **Phase 2**: Clean render screenshots (debug view 0) with same movement pattern
   - **Phase 3**: Live analysis — attaches livetools, moves Lara with A/D strafes + mouse look-around for 60s while collecting render pipeline and light system data via `livetools collect`

2. **Spawn static-analyzer subagent in background** immediately after the test completes — do not wait for it. Give it these tasks for `trl.exe` using `--types patches/TombRaiderLegend/kb.h`:
   - `disasm.py trl.exe 0x407150 -n 10` — verify RET byte at cull function patch site
   - `disasm.py trl.exe 0x4070F0 -n 30` — verify NOP bytes at scene traversal cull jumps
   - Read the proxy log's reported patch addresses and verify each patched instruction with `disasm.py`
   - If result is FAIL: `decompiler.py trl.exe <failing_function_addr>` for any function implicated by the proxy log or Ghidra MCP — decompile it, check xrefs with `xrefs.py`, append all findings to `patches/TombRaiderLegend/findings.md`
   - Write a summary of what the static analysis found to `patches/TombRaiderLegend/findings.md`

3. **Read proxy log**: Check for crashes, skipped draws, patch activation, patched addresses

4. **View ALL screenshots**: Read every Phase 1 (hash debug) and Phase 2 (clean render) screenshot

5. **Verify movement**: Confirm Lara is in a **different position** in each of the 3 screenshots per phase. Same position = false positive, macro failed — investigate input delivery

6. **Evaluate against success criteria**:
   - Hash debug: same geometry must keep same color across all 3 positions
   - Clean render: both red AND green stage lights must be visible in ALL 3 screenshots **AND the lights must shift position across the 3 screenshots** — if the lights are on the same side of the frame in all 3 shots, Lara hasn't moved and it's a false positive even if both lights appear

7. **False positive detection**: If clean render shows both lights in all 3 screenshots but Lara's legs/feet haven't moved and the lights stay on the same sides of the frame — that is a **false positive** (FAIL). A real PASS requires the lights to shift left/right relative to Lara as she walks between them, proving actual movement occurred.

8. **Determine result**: PASS only if all criteria met. Any missing light, hash shift, or false positive = FAIL

9. **Read live analysis results**: Check `patches/TombRaiderLegend/captures/live_analysis/` for:
   - `live_render_pipeline.jsonl` — render call data during movement
   - `live_light_system.jsonl` — light function call data (zero bytes = lights still dormant)
   - Run `python -m livetools analyze <file> --summary` on any non-empty captures
   - Include findings in the SUMMARY under "Live Analysis Findings"

10. **Ghidra MCP — run on every build** (not just FAIL). Check `mcp__ghidra__list_programs` to confirm trl.exe is loaded, then:
    - Always: `mcp__ghidra__get_code` on `RenderLights_FrustumCull` (0x0060C7D0) — verify culling state
    - Always: `mcp__ghidra__get_code` on any function flagged in the proxy log
    - On FAIL: deepen analysis — hash shift → query the submitting function; missing light → decompile the light dispatch path; unexpected skip → trace the skip condition. Use `mcp__ghidra__xrefs`, `mcp__ghidra__search_bytes` as needed.
    - Summarize what Ghidra shows and propose a targeted fix before packaging.

11. **Wait for static-analyzer subagent** to return, then read `patches/TombRaiderLegend/findings.md` for its output.

12. **Read `patches/TombRaiderLegend/findings.md`** — consult all accumulated findings and open hypotheses before writing the SUMMARY.

13. **Package build**: Create `TombRaiderLegendRTX-/TRL tests/build-NNN-<description>/` with:
    - Screenshots (renamed descriptively)
    - `ffp_proxy.log`
    - Proxy source files (`proxy/` subfolder)
    - Live analysis JSONL files (if non-empty)
    - `SUMMARY.md` — must include ALL of the following sections:
      ```
      ## Result
      ## What Changed This Build
      ## Proxy Log Summary (draw counts, vpValid, patch addresses)
      ## Live Analysis Findings (render pipeline stats, light system status)
      ## Retools Findings (from static-analyzer subagent)
      ## Ghidra MCP Findings
      ## Open Hypotheses (what we think is still wrong and why)
      ## Next Build Plan (what to change next and what result to expect)
      ```

14. **Commit + push**: Push to `skurtyyskirts/TombRaiderLegendRTX-` immediately — every build gets uploaded, pass or fail

## Setup Dialog Configuration

The test script auto-configures the TRL setup dialog when it appears:
- **Resolution**: Highest available (3840x2160 preferred)
- **Graphics effects**: All OFF (shadows, reflections, water, DoF, fullscreen effects, FSAA, next-gen, shader 3.0)
- **Dev options enabled**: "Dont Defer Shader Creation" (all shaders created at startup)
- **Dev options disabled**: "Disable Pure Device" (proxy already strips PUREDEVICE; enabling it breaks game init path)
- **Dev options disabled**: All others (hardware vertexshaders, DXTC, reference device, etc.)

## Screenshot Key

The screenshot key is `]` (NVIDIA capture hotkey). This is used in the randomized movement macro and during the live analysis phase.

## Build Numbering

- Check existing builds in `TombRaiderLegendRTX-/TRL tests/` and increment
- PASS builds: include "miracle" in the folder name
- FAIL builds: include the failure reason (e.g., "lights-partial-fail")

## No Questions

Do not ask the user to launch the game, copy files, or confirm anything. The entire pipeline is automated. Just run it and report results.
