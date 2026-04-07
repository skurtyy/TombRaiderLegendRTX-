# "Begin Testing" Trigger — Hash Stability Test

When the user says **"begin testing"**, **"run tests"**, **"start testing"**, or **"test the build"**, immediately execute this workflow without asking questions:

## Workflow

1. **Run the test**: `python patches/TombRaiderLegend/run.py test --build`

   The script handles 4 phases automatically:
   - **Phase 1**: Hash debug screenshots (debug view 277) with gentle camera-only pan (no WASD)
   - **Phase 2**: Clean render screenshots (debug view 0) with same camera pan
   - **Phase 3**: Livetools diagnostics — draw call census, function tracing, patch integrity checks, VB mutation detection
   - **Phase 4**: Placeholder for dx9tracer capture (agent-driven, see step 4 below)

   **Camera movement**: Only mouse pan — 300px left, then 600px right (nets 300px right of center). Lara stays in place. Three screenshots per phase (center, left, right).

2. **Spawn static-analyzer subagent in background** immediately after Phase 1 starts:
   - `disasm.py trl.exe 0x407150 -n 10` — verify RET at cull function
   - `disasm.py trl.exe 0x4070F0 -n 30` — verify NOP bytes at scene traversal cull jumps
   - `disasm.py trl.exe 0x60B050 -n 5` — verify LightVisibilityTest patch (mov al,1; ret 4)
   - Write findings to `patches/TombRaiderLegend/findings.md`

3. **Read proxy log**: Check `ffp_proxy.log` for crashes, draw counts, patch activation

4. **dx9tracer frame capture** (Phase 4 — agent-driven):
   - Swap proxy DLL for tracer DLL in game dir
   - Launch game, skip cutscene, pan camera left
   - `python -m graphics.directx.dx9.tracer trigger --game-dir "<GAME_DIR>" --frames 2 --delay 0 --wait`
   - Pan camera right, trigger another 2-frame capture
   - Kill game, restore proxy DLL
   - Delegate analysis to static-analyzer subagent:
     - `--diff-frames 0 1` — detect draw call changes between consecutive frames (expect 0)
     - `--animate-constants` — which VS constants change frame-to-frame
     - `--const-evolution vs:c0-c3` — prove World matrix stays stable
     - `--const-evolution vs:c8-c15` — confirm View/Proj change as expected
     - `--vtx-formats` — verify consistent vertex declarations
     - `--shader-map` — verify same shaders bound
     - `--classify-draws` — compare draw classifications left vs right

5. **View ALL screenshots**: Read every Phase 1 (hash debug) and Phase 2 (clean render) screenshot

6. **Evaluate against success criteria**:
   - Hash debug: same geometry must keep same color across all 3 camera positions
   - Clean render: both red AND green stage lights must be visible in ALL 3 screenshots
   - Lights must shift position in frame as camera pans (proves camera actually moved)
   - `dipcnt` variance < 5% across center/left/right positions
   - Patch memory reads match expected values (frustum threshold = -1e30, cull RET = 0xC3, etc.)
   - World matrix (c0-c3) stable across frames; View/Proj change as expected

7. **Use gamepilot vision** to analyze screenshots:
   - Hash debug: "Do the same colored blocks appear in the same spatial arrangement across all 3 images?"
   - Clean render: "Are red lights visible on the left side and green lights visible on the right?"

8. **Determine result**: PASS only if ALL criteria met.

   **FAIL categories:**
   - `FAIL-hash-shift` — hash colors change between camera positions
   - `FAIL-lights-missing` — one or more anchor lights not visible
   - `FAIL-lights-static` — lights visible but no position shift (camera didn't pan)
   - `FAIL-draw-drop` — significant draw count drop at a camera position
   - `FAIL-world-matrix-drift` — World matrix registers change unexpectedly
   - `FAIL-vb-mutation` — vertex buffer data written during camera rotation
   - `FAIL-patch-lost` — memory patches not holding
   - `FAIL-crash` — game crashed

9. **Read findings and GitHub context**:
   - `patches/TombRaiderLegend/findings.md` — static-analyzer output
   - `TombRaiderLegendRTX-/TRL tests/WHITEBOARD.md` — project status
   - `TombRaiderLegendRTX-/FINDINGS_PAPER.md` — technical findings
   - `TombRaiderLegendRTX-/README.md` — project overview

10. **Package build**: Create `TombRaiderLegendRTX-/TRL tests/build-NNN-hash-stability-<result>/` with:
    - Screenshots (renamed descriptively)
    - `ffp_proxy.log`
    - Proxy source files (`proxy/` subfolder)
    - Live analysis JSONL files (if non-empty)
    - dx9tracer capture JSONL files (if captured)
    - `SUMMARY.md` — must include ALL of the following sections:
      ```
      ## Result
      ## Test Configuration
      ## Phase 1: Hash Debug Analysis
      ## Phase 2: Light Anchor Analysis
      ## Phase 3: Live Diagnostics
      ### Draw Call Census
      ### Patch Integrity
      ### Memory Watch
      ### Function Collection
      ## Phase 4: Frame Capture Analysis
      ### Draw Call Diff
      ### Constant Evolution
      ### Vertex Format Consistency
      ### Shader Map
      ## Phase 5: Static Analysis
      ## Phase 6: Vision Analysis
      ## Proxy Log Summary
      ## Brainstorming: New Hash Stability Ideas
      ## Open Hypotheses
      ## Next Steps
      ```

11. **Commit + push**: Push to `skurtyyskirts/TombRaiderLegendRTX-` immediately

## Light Anchor Hashes

These mesh hashes have Remix lights anchored to them:

| Hash | Color | Vertices |
|------|-------|----------|
| `mesh_2509CEDB7BB2FAFE` | Red | 365 |
| `mesh_47AC93EAC3777CA5` | Red | 332 |
| `mesh_DD7F8EE7F4F3969E` | Green | 315 |
| `mesh_CE011E8D334D2E48` | Green | 312 |
| `mesh_2AF374CD4EA62668` | Red | 298 |

## Key Patch Addresses to Verify

| Address | Expected | Purpose |
|---------|----------|---------|
| 0x407150 | `C3` (RET) | SceneTraversal_CullAndSubmit disabled |
| 0x4070F0+7 sites | `90 90 90 90 90 90` | Scene traversal cull jumps NOPed |
| 0x60B050 | `B0 01 C2 04` | Light_VisibilityTest always returns true |
| 0xEFDD64 | `-1e30` float | Frustum distance threshold (infinite range) |
| 0xF2A0D4/D8/DC | D3DCULL_NONE | Cull mode globals |

## Build Numbering

- Check existing builds in `TombRaiderLegendRTX-/TRL tests/` and increment
- PASS builds: include "miracle" in the folder name
- FAIL builds: include the failure category (e.g., "hash-stability-FAIL-hash-shift")

## No Questions

Do not ask the user to launch the game, copy files, or confirm anything. The entire pipeline is automated. Just run it and report results.
