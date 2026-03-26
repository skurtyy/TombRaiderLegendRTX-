# Vibe Reverse Engineering — Tomb Raider Legend RTX

## What We're Doing

**Goal:** Get Tomb Raider Legend (2006, PC) working under NVIDIA RTX Remix so it can be path-traced with accurate per-mesh material assignments.

**The Problem:** TRL renders via vertex shaders. RTX Remix needs games to use the D3D9 Fixed-Function Pipeline (FFP) to identify geometry, assign asset hashes, and inject path-traced lighting. Shader-based games produce unstable hashes and wrong material assignments because Remix can't decode shader constant semantics.

**The Solution:** A custom `d3d9.dll` proxy that sits between TRL and RTX Remix. The proxy intercepts D3D9 API calls, reverse-engineers the vertex shader constant layout, reconstructs world/view/projection matrices, NULLs the shaders, calls `SetTransform` to push those matrices through FFP, then chains to the real Remix DLL. Remix sees geometry as if it were an FFP game.

**Secondary Requirement:** The proxy must also defeat TRL's frustum culling, which aggressively culls geometry that should remain visible for Remix to hash and light correctly.

---

## Repository Structure

```text
.
├── proxy/                          # Current working proxy source + compiled DLL
│   ├── d3d9_device.c               # Core proxy: ~2100 lines, intercepts ~15 of 119 device methods
│   ├── d3d9_main.c                 # DLL entry, logging, chain-load to Remix
│   ├── d3d9_wrapper.c              # IDirect3D9 wrapper (create + relay)
│   ├── d3d9_skinning.h             # Optional skinning (ENABLE_SKINNING=0 by default)
│   ├── build.bat                   # MSVC x86 build script (uses vswhere to find VS)
│   ├── d3d9.def                    # DLL export table
│   ├── d3d9.dll                    # Compiled proxy binary (deployed to game dir)
│   └── proxy.ini                   # Runtime config: Remix chain-load, albedo stage
│
├── patches/TombRaiderLegend/       # Project workspace (git-ignored)
│   ├── proxy/                      # Authoritative proxy source (synced to proxy/)
│   ├── run.py                      # Test orchestrator (build → deploy → launch → macro → collect)
│   ├── macros.json                 # Recorded input macros for test sessions
│   ├── kb.h                        # Knowledge base: discovered functions, globals, structs
│   ├── findings.md                 # Accumulated Ghidra + static analysis findings
│   ├── screenshots/                # Captures from last test run
│   ├── ffp_proxy.log               # Proxy diagnostic output from last test run
│   ├── TRL_TEST_CYCLE.md           # Pass/fail criteria and common mistakes
│   ├── AUTOMATION.md               # Test pipeline documentation
│   ├── SUMMARY.md                  # Build 016 detailed results
│   └── backups/                    # Timestamped backups before each proxy edit
│
├── TombRaiderLegendRTX-/           # Test build archive (pushed to GitHub after every run)
│   └── TRL tests/
│       ├── build-001-baseline-passthrough/
│       ├── ...
│       ├── build-019-miracle-both-lights-stable-hashes/  ← last confirmed PASS
│       ├── build-020-lights-partial-fail/
│       └── build-021-false-positive-lara-didnt-move/     ← latest
│
├── retools/                        # Static analysis toolkit (offline PE analysis)
├── livetools/                      # Live dynamic analysis toolkit (Frida-based)
├── graphics/directx/dx9/tracer/    # D3D9 frame capture and analysis tool
├── Tomb Raider Legend/             # Game directory (trl.exe, NvRemixLauncher32.exe, rtx.conf)
├── .claude/rules/                  # Agent workflow rules (tool catalog, delegation, testing)
└── requirements.txt                # Python deps: frida, pefile, capstone, r2pipe, minidump
```

---

## The Proxy: How It Works

The proxy is a no-CRT `d3d9.dll` compiled with MSVC x86. It replaces the game's D3D9 entry point via COM vtable replacement. The key methods it intercepts:

| Method | What the proxy does |
| --- | --- |
| `SetVertexShader` | If shader active, starts intercepting constants. If NULL, triggers FFP engage. |
| `SetVertexShaderConstantF` | Captures VS constant registers into a per-draw constant bank. |
| `SetRenderState` | Intercepts `D3DRS_CULLMODE` — forces `D3DCULL_NONE` to defeat frustum culling. |
| `DrawIndexedPrimitive` | On each draw: reconstruct matrices from constant bank, call `SetTransform` for World/View/Proj, NULL the shader, then relay the draw. |
| `Present` | Logs diagnostics every 120 frames (draw counts, vpValid, patch stats). |

**VS Constant Layout for TRL** (discovered via `dx9tracer` and `datarefs.py`):

```c
// In d3d9_device.c — top of file, game-specific section
#define VS_REG_WVP_START     0   // c0–c3: combined World-View-Projection (4x4)
#define VS_REG_VIEW_START    8   // c8–c11: View matrix
#define VS_REG_PROJ_START    12  // c12–c15: Projection matrix
#define VS_REG_BONE_START    48  // c48+: skinning matrices (3 regs/bone)
```

The proxy reads `View` and `Projection` directly from TRL's in-memory matrix globals (confirmed addresses), reconstructs `World` as `WVP * (VP)^-1`, and feeds all three to `SetTransform`.

**Anti-Culling Patches** (applied at proxy startup via memory writes):

| Address | What | Why |
| --- | --- | --- |
| `0x407150` | Write `0xC3` (RET) | Returns immediately from frustum cull entry, skipping the cull decision entirely |
| `0x4070F0–0x40723x` | NOP branches | Disables individual scene-traversal cull jumps |
| `SetRenderState hook` | Force `D3DCULL_NONE` | Overrides per-pass cull mode globals (`0x00F2A0D4`, `0x00F2A0D8`) |

---

## Testing: What PASS Means

The test scene is the **level-opening area** where two colored stage lights (one red, one green) are set dressing. They're good test geometry because:

- They're spatially separated, so they only appear together when frustum culling is fully defeated
- They have distinct asset hashes in RTX Remix
- Their position in frame shifts left/right as Lara walks past them

**Pass criteria — ALL must be true:**

1. Both the **red** and **green** stage lights are visible in **all 3** clean render screenshots
2. The lights **shift position** across the 3 screenshots (left/right relative to Lara)
3. Hash debug view shows **same color for same geometry** across all 3 positions (no hash flipping)
4. No crash, no proxy log errors
5. Proxy log shows `vpValid=1`, patch addresses confirmed, draw counts ~91,800

**False positive detection:** If both lights appear in all 3 shots but Lara's position hasn't changed (lights are in the same frame location in all 3), it's a false positive — the macro didn't deliver movement to the game. This happened in builds 016 and 021.

---

## Testing: How to Run

```bash
# Full build + test (compiles proxy, deploys to game dir, launches, runs macro, collects results)
python patches/TombRaiderLegend/run.py test --build --randomize

# Test only (skip build, use last compiled proxy)
python patches/TombRaiderLegend/run.py test --randomize

# Record a new test macro
python patches/TombRaiderLegend/run.py record
```

`run.py` does the entire pipeline autonomously:

1. (Optional) Build proxy via `proxy/build.bat`
2. Deploy `d3d9.dll` + `proxy.ini` to `Tomb Raider Legend/`
3. Write TRL graphics registry settings (lowest quality, fullscreen)
4. Kill any running `trl.exe`
5. Launch via `NvRemixLauncher32.exe trl.exe` — **no focus touching**, 20-second wait
6. Dismiss setup dialog via Win32 automation
7. Replay `test_session` macro (menu nav → level load → A/D strafes with `]` screenshot triggers)
8. Wait up to 70 seconds for `ffp_proxy.log` (proxy has a 50-second startup delay)
9. Kill `trl.exe`
10. Collect the 3 most recent screenshots from NVIDIA capture folder

**Never trigger this manually.** When the user says "begin testing", "run tests", or "test the build", the agent runs the full workflow defined in `.claude/rules/begin-testing.md`.

---

## Build Numbering and Packaging

Every test run produces a build folder in `TombRaiderLegendRTX-/TRL tests/`:

```text
build-NNN-<description>/
├── SUMMARY.md          # Required sections (see below)
├── phase1-hash-debug-posN.png      # Hash debug view screenshots
├── phase2-clean-render-posN-*.png  # Clean render screenshots
├── ffp_proxy.log
└── proxy/              # Source files at time of test
    ├── d3d9_device.c
    ├── d3d9_main.c
    ├── d3d9_wrapper.c
    └── proxy.ini
```

**SUMMARY.md must include all of:**

```markdown
## Result
## What Changed This Build
## Proxy Log Summary (draw counts, vpValid, patch addresses)
## Retools Findings (from static-analyzer subagent)
## Ghidra MCP Findings
## Open Hypotheses (what we think is still wrong and why)
## Next Build Plan (what to change next and what result to expect)
```

Naming: `build-019-miracle-...` for PASS, `build-020-lights-partial-fail` for FAIL. Every build pushed to `skurtyyskirts/TombRaiderLegendRTX-` immediately, no batching.

---

## Tools Available

### Static Analysis (`retools/`) — Offline PE Analysis

Run all tools from repo root with `python -m retools.<tool>`. Always pass `--types patches/TombRaiderLegend/kb.h` to the decompiler.

| Tool | Purpose |
| --- | --- |
| `decompiler.py` | Ghidra-quality C decompilation with KB type injection |
| `disasm.py` | Disassemble N instructions at a virtual address |
| `xrefs.py` | Find all callers/jumps to an address |
| `callgraph.py` | Caller/callee tree (multi-level, --up/--down) |
| `datarefs.py` | Find instructions that read/write a global address |
| `structrefs.py` | Find `[reg+offset]` accesses; reconstruct structs with `--aggregate` |
| `search.py` | String search, byte pattern search, import/export list, instruction search |
| `rtti.py` | MSVC RTTI: resolve C++ class name + inheritance from vtable |
| `bootstrap.py` | Seed KB: compiler ID, signatures, RTTI classes, propagated labels (2–5 min) |
| `sigdb.py` | Bulk signature scan, single function ID, compiler fingerprint |
| `context.py` | Assemble full analysis context for a function; postprocess decompiler output |
| `dumpinfo.py` | Minidump analysis: exception, threads, stack walk, memory scan |
| `throwmap.py` | Map MSVC `_CxxThrowException` call sites to error strings; match against dump |

**Delegation rule:** Never run more than one `retools` command inline. Delegate to a `static-analyzer` subagent. Exception: `sigdb identify`, `sigdb fingerprint`, `context assemble`, `context postprocess`, `readmem.py` — these are fast (<5s) and run inline.

### Live Analysis (`livetools/`) — Frida-Based, Requires Running Process

```bash
python -m livetools attach trl.exe
python -m livetools trace 0x407150 --count 20
python -m livetools mem write 0x00F2A0D4 01000000   # Write uint32 = 1
python -m livetools dipcnt on
```

| Command | Purpose |
| --- | --- |
| `trace $VA` | Non-blocking: log hits with register/memory reads |
| `bp add $VA` + `watch` | Blocking breakpoint; inspect with `regs`/`stack`/`bt` |
| `mem read/write $VA` | Inspect or patch live process memory |
| `memwatch` | Write watchpoint: catch who writes to an address |
| `dipcnt on/read` | D3D9 DrawIndexedPrimitive counter |
| `modules` | List loaded modules + base addresses |

**Note on addresses:** TRL is 32-bit without ASLR. Static addresses from `retools` map directly to runtime addresses.

### D3D9 Frame Tracer (`graphics/directx/dx9/tracer/`) — Full API Capture

Captures every D3D9 call for one or more frames with arguments, matrices, shader bytecodes, and backtraces. Deploy as `d3d9.dll` (chains to the FFP proxy via `proxy.ini Chain.DLL`).

```bash
python -m graphics.directx.dx9.tracer trigger --game-dir "Tomb Raider Legend/"
python -m graphics.directx.dx9.tracer analyze capture.jsonl --shader-map --render-passes --classify-draws
```

Key analysis options: `--shader-map` (disassemble all shaders + CTAB), `--const-provenance` (which SetVSConstantF call set each register), `--matrix-flow` (track matrix uploads), `--classify-draws` (auto-tag draws), `--state-snapshot DRAW#` (full device state at a draw).

### Ghidra MCP (`mcp__ghidra__*`) — Interactive Decompiler

Ghidra runs as an MCP server with `trl.exe` loaded. Use on every build run, not just failures.

```text
mcp__ghidra__get_code     # Decompile a function by address
mcp__ghidra__xrefs        # Cross-references to/from an address
mcp__ghidra__search_bytes # Find byte patterns
mcp__ghidra__list_programs # Confirm trl.exe is loaded
```

Key function to check every build: `RenderLights_FrustumCull` at `0x0060C7D0`.

---

## Knowledge Base (`patches/TombRaiderLegend/kb.h`)

Accumulates all reverse engineering discoveries. Format:

```c
// Structs
struct TRLRenderer {
    // ...
};

// Functions — @ address name(sig)
@ 0x00413950 void __cdecl cdcRender_SetWorldMatrix(float* pMatrix);
@ 0x0060C7D0 void __cdecl RenderLights_FrustumCull(void* pScene);

// Globals — $ address type name
$ 0x01392E18 void* g_pEngineRoot
$ 0x00F2A0D4 int   g_cullMode_pass1
$ 0x00F2A0D8 int   g_cullMode_pass2
$ 0x010FC780 float g_viewMatrix[16]
$ 0x01002530 float g_projMatrix[16]
```

Always pass `--types patches/TombRaiderLegend/kb.h` to the decompiler so discovered names propagate through decompilation output.

---

## Key Addresses (Current)

| Address | Symbol | Notes |
| --- | --- | --- |
| `0x00407150` | `FrustumCull_Entry` | Patched to RET — skips entire cull decision |
| `0x004070F0` | Scene traversal cull | NOP'd branch block |
| `0x0060C7D0` | `RenderLights_FrustumCull` | Light render dispatch with cull guard |
| `0x00413950` | `cdcRender_SetWorldMatrix` | Sets world matrix on renderer |
| `0x00F2A0D4` | `g_cullMode_pass1` | Opaque pass cull mode (proxy forces NONE) |
| `0x00F2A0D8` | `g_cullMode_pass2` | Transparent pass cull mode |
| `0x010FC780` | `g_viewMatrix` | Live view matrix read by proxy |
| `0x01002530` | `g_projMatrix` | Live projection matrix read by proxy |
| `0x01392E18` | `g_pEngineRoot` | Engine root object |

---

## Current Status

**Last confirmed PASS:** `build-019-miracle-both-lights-stable-hashes` (2026-03-25)

- Both red and green stage lights visible in all 3 clean render screenshots
- Asset hashes stable across strafing positions
- Anti-culling patches applied: `0x407150→RET`, scene traversal NOPs, `D3DCULL_NONE` hook

**Latest build:** `build-021-false-positive-lara-didnt-move` (2026-03-26)

- Both lights visible in all 3 screenshots, but Lara didn't move between them
- Classified as false positive — test procedure issue, not a regression in proxy code
- Code is likely still in a passing state

**Open hypotheses:**

1. `0x407150→RET` may be over-aggressive — could suppress geometry submission for some draw configurations
2. LOD fade system at `0x446580` (10 callers) may fade geometry to invisible without a cull flag
3. Level sector streaming may remove geometry that frustum culling alone wouldn't explain
4. Per-pass cull globals (`0x00F2A0D4/D8`) may be reset by game code between frames, overriding the proxy hook

---

## Operating Conventions

### Delegation

Static analysis (`retools`) → `static-analyzer` subagent (background). Live tools → main agent directly. Never run more than one `retools` command inline.

### Backups

Before any proxy edit: `patches/TombRaiderLegend/backups/YYYY-MM-DD_HHMM_<description>/` with all modified files. Create backup **before** making changes.

### Never Do

- Change the test procedure (A/D hold times are the only tunable)
- Batch-push multiple test results without a code change between runs
- Launch the game without the 20-second pre-input wait
- Touch the game window focus after launch
- Ask the user to copy files, launch the game, or confirm anything in the test pipeline

### Git

Push to `skurtyyskirts/TombRaiderLegendRTX-`. Every build — pass or fail — gets committed and pushed. PASS builds include "miracle" in the folder name.

---

## Quick Start for a New LLM Session

1. Read `patches/TombRaiderLegend/kb.h` — accumulated address map and struct layouts
2. Read `patches/TombRaiderLegend/findings.md` — Ghidra and static analysis findings
3. Check `TombRaiderLegendRTX-/TRL tests/` for the latest build folder and its `SUMMARY.md`
4. Read `.claude/rules/begin-testing.md` before running any test
5. Check `.claude/rules/tool-catalog.md` before choosing an analysis tool

To run a test: tell the agent "begin testing" — it handles everything.
