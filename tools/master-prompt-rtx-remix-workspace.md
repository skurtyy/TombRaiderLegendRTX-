# Master Prompt — RTX Remix Game Porting Workspace Setup

> **How to use:** Open Claude Code (Opus 4.6, extended thinking, max tokens) in the parent folder containing:
> 1. The **vibe reverse engineering toolkit** (cloned repo with `retools/`, `livetools/`, `graphics/`, `rtx_remix_tools/`, `gamepilot/`, `autopatch/`)
> 2. The **game directory** (e.g. `"Game Name/"` with the game's .exe)
> 3. An **empty git repo** for the game (e.g. `"GameNameRTX-/"` for tracking tests/builds/progress)
>
> Edit the `[CONFIGURE]` block, then paste the entire prompt section below into Claude Code.

---

## The Prompt

Copy everything between the `---START---` and `---END---` markers below.

---START---

You are setting up a complete RTX Remix game porting workspace. This is a "vibe reverse engineering" project — we use a D3D9 Fixed-Function Pipeline (FFP) proxy DLL to make old DirectX 9 games compatible with NVIDIA RTX Remix.

## [CONFIGURE] — Replace these values before pasting

```
GAME_DISPLAY_NAME = "Tomb Raider: Legend"
GAME_SHORT_NAME   = "TombRaiderLegend"
GAME_EXE          = "trl.exe"
GAME_DIR_NAME     = "Tomb Raider Legend"
GITHUB_REPO_NAME  = "TombRaiderLegendRTX-"
GITHUB_USER       = "skurtyyskirts"
GITHUB_REPO_URL   = "github.com/skurtyyskirts/TombRaiderLegendRTX-"
ENGINE_NAME       = "cdcEngine"
GAME_YEAR         = "2006"
GAME_DEVELOPER    = "Crystal Dynamics"
GAME_PLATFORM     = "Steam PC, 32-bit x86"
GAME_BITNESS      = "32"
LAUNCHER_EXE      = "NvRemixLauncher32.exe"
LAUNCHER_CHAIN    = "NvRemixLauncher32.exe → trl.exe → dxwrapper.dll → d3d9.dll (FFP proxy) → d3d9_remix.dll"
SCREENSHOT_PATH   = "C:\\Users\\skurtyy\\Videos\\NVIDIA\\Tomb Raider  Legend"
OWNER_NAME        = "Jeffrey"
OWNER_HANDLE      = "skurtyyskirts"
OWNER_LOCATION    = "Temple TX"
```

## Instructions

Using the vibe RE toolkit already present in this directory (`retools/`, `livetools/`, `graphics/`, `rtx_remix_tools/`, `gamepilot/`, `autopatch/`), create a full RTX Remix porting workspace inside the `GITHUB_REPO_NAME/` folder. Execute ALL phases below in order. Do not skip any phase. Do not ask questions — just build it.

---

## Phase 1: Directory Skeleton

Create all directories. The tree below shows the full structure:

```
GITHUB_REPO_NAME/
├── .claude/
│   ├── CLAUDE.md
│   ├── settings.json
│   ├── settings.local.json
│   ├── agents/
│   │   ├── static-analyzer.md
│   │   └── web-researcher.md
│   ├── rules/
│   │   ├── tool-catalog.md
│   │   ├── tool-dispatch.md
│   │   ├── subagent-workflow.md
│   │   ├── project-workspace.md
│   │   ├── dx9-ffp-port.md
│   │   └── hash-stability-test.md
│   └── skills/
│       ├── dx9-ffp-port/
│       │   └── SKILL.md
│       └── dynamic-analysis/
│           └── SKILL.md
├── .mcp.json
├── .gitignore
├── .gitattributes
├── CLAUDE.md
├── CHANGELOG.md
├── README.md
├── proxy/
│   ├── d3d9_device.c
│   ├── d3d9_main.c
│   ├── d3d9_wrapper.c
│   ├── d3d9_skinning.h
│   ├── build.bat
│   ├── d3d9.def
│   ├── proxy.ini
│   └── README.md
├── patches/
│   └── GAME_SHORT_NAME/
│       ├── kb.h
│       ├── run.py
│       ├── findings.md
│       └── proxy/ (copy of proxy/)
├── docs/
│   ├── README.md
│   ├── status/
│   │   ├── WHITEBOARD.md
│   │   └── TEST_STATUS.md
│   ├── reference/
│   ├── research/
│   └── guides/
├── automation/
│   ├── README.md
│   └── screenshots/ (.gitkeep)
├── tools/
├── GAME_SHORT_NAME tests/
└── GAME_SHORT_NAME traces/
    └── README.md
```

---

## Phase 2: Root CLAUDE.md

Create `GITHUB_REPO_NAME/CLAUDE.md`:

```markdown
# CLAUDE.md — GITHUB_REPO_NAME

## Identity
- **Game:** GAME_DISPLAY_NAME (GAME_YEAR, GAME_DEVELOPER, ENGINE_NAME, GAME_PLATFORM)
- **Project:** Vibe Reverse Engineering toolkit — D3D9 FFP proxy DLL + RE tools for RTX Remix compatibility
- **Repo:** GITHUB_REPO_URL
- **Owner:** OWNER_NAME (OWNER_HANDLE), OWNER_LOCATION
- **Builds completed:** 000 (0 commits)

## DLL Chain
LAUNCHER_CHAIN

## Architecture Summary
[TO BE DISCOVERED — fill in after initial D3D9 analysis]

The proxy intercepts D3D9 calls, reconstructs W/V/P matrices from VS constants, and feeds them to Remix through FFP calls — so Remix sees the game as a native FFP game. The proxy also patches culling layers at runtime via VirtualProtect + memory write.

### VS Constant Register Layout (game-specific)
[TO BE DISCOVERED — run find_vs_constants.py and livetools trace]

### Proxy Method Hooks
| Method | What it does |
|--------|-------------|
| `SetVertexShaderConstantF` | Captures VS constants into per-draw register bank |
| `DrawIndexedPrimitive` | Reconstructs W/V/P matrices, calls `SetTransform`, chains to Remix |
| `SetRenderState` | Intercepts `D3DRS_CULLMODE` — forces `D3DCULL_NONE` |
| `BeginScene` | Stamps anti-culling globals |
| `Present` | Logs diagnostics every 120 frames |

### Matrix Recovery Addresses
[TO BE DISCOVERED — run livetools trace on SetVertexShaderConstantF call sites]

## rtx.conf
```ini
[TO BE CONFIGURED — fill in after first successful render]
rtx.useVertexCapture = True
rtx.fusedWorldViewMode = 0
rtx.enableRaytracing = True
rtx.fallbackLightMode = 1
rtx.fallbackLightRadiance = 5, 5, 5
```

## Current Status

### DONE
(nothing yet)

### BLOCKERS
[TO BE DISCOVERED — document as they emerge]

## Culling Map

| # | Layer | Address(es) | Patched? | Build |
|---|-------|------------|----------|-------|
| — | — | — | — | — |

## Known Dead Ends — DO NOT RETRY

| # | Approach | Why It Failed | Build |
|---|----------|--------------|-------|
| — | — | — | — |

## What Has NOT Been Tried

| Idea | Why It Matters | Difficulty |
|------|---------------|------------|
| — | — | — |

## Repository Layout

| Path | Description |
|------|-------------|
| `proxy/` | D3D9 FFP proxy DLL source |
| `retools/` | Offline static analysis — decompile, xrefs, CFG, RTTI, signatures |
| `livetools/` | Live dynamic analysis — Frida-based tracing, breakpoints, memory r/w |
| `graphics/directx/dx9/tracer/` | Full-frame D3D9 API capture and offline analysis |
| `gamepilot/` | Vision-guided game automation agent |
| `autopatch/` | Autonomous hypothesis-test-patch loop |
| `automation/` | Screenshot automation and test replay infrastructure |
| `patches/GAME_SHORT_NAME/` | Game-specific workspace (kb.h, findings, proxy copy) |
| `docs/` | Full documentation — research, reference, guides |
| `docs/status/WHITEBOARD.md` | **Live status** — culling map, build history, decision tree |
| `docs/status/TEST_STATUS.md` | Build-by-build pass/fail results |
| `GAME_SHORT_NAME tests/` | Test build archive — every build with SUMMARY.md, screenshots, proxy log, source |
| `GAME_SHORT_NAME traces/` | Full-frame D3D9 API captures |
| `rtx_remix_tools/` | RTX Remix integration utilities |
| `tools/` | Build scripts, test utilities |
| `.claude/` | Claude Code settings |

## Engine Globals Reference

| Address | Name | Notes |
|---------|------|-------|
| [TO BE DISCOVERED] | | |

## Tool Catalog

### In-Repo Tools
- **retools/** — Offline static analysis: decompile, xrefs, CFG, RTTI, signatures
- **livetools/** — Frida-based live tracing, breakpoints, memory r/w
- **dx9 tracer** (`graphics/directx/dx9/tracer/`) — full-frame D3D9 API capture
- **gamepilot/** — vision-guided game automation
- **autopatch/** — autonomous hypothesis-test-patch loop
- **automation/** — screenshot capture and test replay

### External Tools
- **GhidraMCP** (localhost:8080) — MCP tools, target: GAME_EXE

## Build & Test
```bash
pip install -r requirements.txt
python verify_install.py
python patches/GAME_SHORT_NAME/run.py test --build
python -m autopatch
```

Say **"begin testing"** to run the full automated pipeline.

## Engineering Standards
1. Every session: read CLAUDE.md, then CHANGELOG.md, then WHITEBOARD.md
2. Log ALL findings to CHANGELOG.md with timestamps
3. Failed approaches go in Dead Ends table with WHY and which build
4. **Never retry a documented dead end without new evidence**
5. Every build gets a folder in `GAME_SHORT_NAME tests/` with SUMMARY.md, screenshots, proxy log, and source snapshot
6. PASS builds include `miracle` in the folder name
7. Every build — pass or fail — pushed immediately
```

---

## Phase 3: .claude/CLAUDE.md (Agent Instructions)

Create `GITHUB_REPO_NAME/.claude/CLAUDE.md`. Copy VERBATIM from the toolkit's `.claude/CLAUDE.md` file. It contains:

- **Delegation rule**: Never run static analysis tools directly — delegate to `static-analyzer` subagent. Exceptions: `sigdb.py identify/fingerprint`, `context.py assemble/postprocess`, `readmem.py`, `asi_patcher.py build`.
- **Live tools first**: Main agent owns livetools. When subagent returns addresses, immediately follow up with live tools.
- **Engineering standards**: Remove (fixes in wrong layer, tolerance inflation, catch-all swallowing, god methods, leaky abstractions). Design for (single responsibility, ownership, minimal surface). Commit to new code (no legacy fallbacks, no dead code, no multiple paths, no half-migrations). Smell tests.
- **Code comments policy**: Remove backstories, obvious narration, debugging breadcrumbs, trial-and-error reasoning. Keep non-obvious decisions, tricky invariants, API contracts.
- **References** to `@.claude/rules/` files.

---

## Phase 4: .claude/settings.json

```json
{
  "permissions": {
    "allow": [
      "Bash(python -m retools*)",
      "Bash(python -m livetools*)",
      "Bash(python -m graphics*)",
      "Bash(python verify_install.py)",
      "Bash(python rtx_remix_tools/*)"
    ]
  }
}
```

## Phase 4b: .claude/settings.local.json

```json
{
  "permissions": {
    "allow": [
      "Bash(git checkout:*)",
      "Bash(git branch:*)",
      "Bash(git rebase:*)",
      "Bash(git add:*)"
    ]
  }
}
```

---

## Phase 5: .claude/agents/

### static-analyzer.md

```markdown
---
name: static-analyzer
description: Offline PE binary analysis using retools. Delegate here for decompilation, disassembly, xrefs, string/pattern search, struct reconstruction, callgraphs, vtable/RTTI resolution, crash dump analysis, bootstrapping new binaries, signature DB operations, context assembly, and any static analysis task. Use instead of running retools commands in the main conversation.
tools: Bash, Read, Write, Glob, Grep
model: opus
memory: project
---

You are a reverse engineering analyst specializing in static analysis of PE binaries (.exe and .dll). You run offline analysis tools and return structured findings to the orchestrating agent.

## Setup

On first invocation, read the full tool catalog at `.claude/rules/tool-catalog.md` in the working directory. It contains exact syntax, flags, and caveats for every tool.

## Pre-flight Checks

Before any analysis, run these checks in order:

**1. Verify install**: Run `python verify_install.py` on first invocation. If pyghidra/Ghidra/Java show as WARN, run `python verify_install.py --setup` to auto-download JDK 21 + Ghidra + pyghidra.

**2. Signature DB**: If `retools/data/signatures.db` does not exist, pull it first:
`test -f retools/data/signatures.db || python retools/sigdb.py pull`

**3. Bootstrap**: Check if the project KB needs bootstrapping:
`grep -cE '^[@$]|^struct |^enum ' patches/GAME_SHORT_NAME/kb.h 2>/dev/null || echo 0`
If count < 50, run `python -m retools.bootstrap GAME_EXE --project GAME_SHORT_NAME` first.

## Tools

Run all tools from repo root via `python -m retools.<tool>`. ALWAYS pass `--types patches/GAME_SHORT_NAME/kb.h` to `decompiler.py`.

## Output

Write findings to `patches/GAME_SHORT_NAME/findings.md` (append). The return message is a summary — the file has full details.
```

### web-researcher.md

```markdown
---
name: web-researcher
description: Web research and documentation lookups. Delegate here for API references, library documentation, SDK docs, file format specs, protocol details, or any question requiring external knowledge. Use instead of doing web research in the main conversation.
disallowedTools: Edit, Write, NotebookEdit, Bash, Agent
model: sonnet
---

You are a technical research assistant supporting a reverse engineering workflow. You fetch documentation, API references, and technical specs from the web and return concise, actionable findings.

## Tools
- **WebFetch**: Fetch and extract content from a specific URL
- **WebSearch**: Search the web for technical information
- **Read**: Read local files for context about what's being researched

## How to Work
1. Understand what the caller needs — a specific API signature, a file format layout, a protocol detail
2. Search or fetch the most authoritative source (MSDN, official docs, specs)
3. Extract the specific information needed — don't return entire pages
4. Format findings for direct use in reverse engineering or code writing

## Output
- The specific answer or data requested
- Key details (function signatures, struct layouts, enum values, constants)
- Source URL for reference
- Any caveats or version-specific differences
```

---

## Phase 6: .claude/rules/

Copy ALL of these files VERBATIM from the toolkit's `.claude/rules/` directory:

1. **tool-catalog.md** — Full tool reference for retools, livetools, dx9tracer, crash dump analysis. Contains exact syntax, examples, and caveats. Copy verbatim.

2. **tool-dispatch.md** — Quick-reference dispatch table: what to run directly vs delegate. Copy verbatim.

3. **subagent-workflow.md** — Delegation rules, pre-flight (Ghidra backend), bootstrap-first for new binaries, dual-backend deep analysis, parallel work patterns, anti-patterns. Copy verbatim.

4. **project-workspace.md** — Workspace conventions: `patches/<project>/` for artifacts, backup policy, knowledge base `.h` format. Copy verbatim.

5. **dx9-ffp-port.md** — FFP proxy porting guide: template file map, game-specific defines, porting workflow (5 steps), architecture decision trees, common pitfalls. Copy verbatim.

6. **hash-stability-test.md** — The "begin testing" trigger. ADAPT for this game by replacing:
   - All game directory paths → use `GAME_DIR_NAME/`
   - Game exe → `GAME_EXE`
   - Launcher → `LAUNCHER_EXE`
   - Screenshot path → `SCREENSHOT_PATH`
   - Proxy log path → `GAME_DIR_NAME/ffp_proxy.log`
   - Patch addresses table → start EMPTY (fill as patches are discovered)
   - Light anchor hashes table → start EMPTY (fill as anchors are created in Remix Toolkit)
   - Keep the full phase structure: hash debug → clean render → livetools diagnostics → dx9tracer → static analysis → vision analysis
   - Keep all PASS/FAIL criteria and category codes
   - Keep build numbering conventions (check `GAME_SHORT_NAME tests/` and increment)
   - Keep the SUMMARY.md section template

---

## Phase 7: .claude/skills/

### dx9-ffp-port/SKILL.md

Copy VERBATIM from toolkit's `.claude/skills/dx9-ffp-port/SKILL.md`. This skill covers:
- FFP proxy porting workflow
- remix-comp-proxy structure
- VS constant discovery
- Draw routing decision trees
- Skinning (off by default)
- Template protection (never modify template — copy to `patches/`)

### dynamic-analysis/SKILL.md

Copy VERBATIM from toolkit's `.claude/skills/dynamic-analysis/SKILL.md`. This skill covers:
- Frida-based livetools session management
- Breakpoints, tracing, collection
- Memory read/write/scan
- D3D9 DIP counters and memory watchpoints
- Offline JSONL analysis

---

## Phase 8: .mcp.json

```json
{
  "mcpServers": {
    "ghidra": {
      "type": "sse",
      "url": "http://localhost:8080/sse"
    }
  }
}
```

---

## Phase 9: Proxy Source

Copy the ENTIRE `rtx_remix_tools/dx/dx9_ffp_template/proxy/` directory into `GITHUB_REPO_NAME/proxy/`. Also copy it into `patches/GAME_SHORT_NAME/proxy/`.

The game-specific defines at the top of `d3d9_device.c` start with template defaults — they will be updated after VS constant discovery:

```c
#define VS_REG_VIEW_START       0   // [TO BE DISCOVERED]
#define VS_REG_VIEW_END         4
#define VS_REG_PROJ_START       4   // [TO BE DISCOVERED]
#define VS_REG_PROJ_END         8
#define VS_REG_WORLD_START     16   // [TO BE DISCOVERED]
#define VS_REG_WORLD_END       20
#define ENABLE_SKINNING         0   // Only set to 1 after rigid FFP works
```

---

## Phase 10: CHANGELOG.md

```markdown
# CHANGELOG.md — GITHUB_REPO_NAME Session Log

> **Purpose:** Cross-session memory for Claude Code. Every session reads this first, every session updates it.
> **Format:** `[YYYY-MM-DD HH:MM] LABEL — Summary` followed by findings, patches, test results, dead ends.
> **Full build history:** See `docs/status/WHITEBOARD.md` for the complete build narrative.

---

## [TODAY'S DATE] BOOTSTRAP — Workspace initialized
- Created CLAUDE.md, CHANGELOG.md, WHITEBOARD.md
- Copied FFP proxy template to proxy/ and patches/GAME_SHORT_NAME/proxy/
- Created .claude/ config (agents, rules, skills, settings)
- Ready for Step 1: static analysis of GAME_EXE
```

---

## Phase 11: docs/status/WHITEBOARD.md

```markdown
# GAME_SHORT_NAME RTX Remix — Results Whiteboard

**Last updated:** TODAY'S DATE
**Builds completed:** 000
**Goal:** Get GAME_DISPLAY_NAME rendering correctly with RTX Remix — stable hashes, no culling, anchored lights

---

## Status at a Glance

| Goal | Status | Notes |
|------|--------|-------|
| FFP proxy DLL builds & chains | NOT STARTED | |
| VS constant register layout discovered | NOT STARTED | |
| Transform pipeline (View/Proj/World) | NOT STARTED | |
| Asset hash stability (static camera) | NOT STARTED | |
| Asset hash stability (with movement) | NOT STARTED | |
| Backface culling disabled | NOT STARTED | |
| Frustum/distance culling disabled | NOT STARTED | |
| Sector/portal visibility disabled | NOT STARTED | |
| Light culling disabled | NOT STARTED | |
| Automated test pipeline | NOT STARTED | |

---

## Culling Layers — Complete Map

| Layer | Address(es) | What It Does | Patched? | Build Added |
|-------|-------------|--------------|----------|-------------|
| — | — | — | — | — |

---

## Known Dead Ends

| # | Approach | Why It Failed | Build |
|---|----------|--------------|-------|
| — | — | — | — |
```

---

## Phase 12: docs/status/TEST_STATUS.md

```markdown
# Test Status — GAME_SHORT_NAME RTX Remix

Build-by-build test results. Updated after every test run.

| Build | Date | Result | Description | Key Finding |
|-------|------|--------|-------------|-------------|
| — | — | — | — | — |
```

---

## Phase 13: Knowledge Base Seed

Create `patches/GAME_SHORT_NAME/kb.h`:

```c
// Knowledge Base — GAME_DISPLAY_NAME
// Format: C types (no prefix), functions (@ prefix), globals ($ prefix)
//
// struct Foo { int x; float y; };
// @ 0x401000 void __cdecl ProcessInput(int key);
// $ 0x7C5548 Object* g_mainObject

// === D3D9 Types ===
// (populated by bootstrap.py)

// === Engine Types ===
// (populated during reverse engineering)

// === Functions ===
// (populated by analysis — decompiler, xrefs, traces)

// === Globals ===
// (populated by datarefs, livetools mem read)
```

---

## Phase 14: Findings Accumulator

Create `patches/GAME_SHORT_NAME/findings.md`:

```markdown
# Findings — GAME_SHORT_NAME

Subagent analysis output. Appended by static-analyzer and web-researcher agents.

---
```

---

## Phase 15: .gitignore

```
# Game-specific workspace (local artifacts)
patches/*/
!patches/*/proxy/
!patches/*/run.py
!patches/*/kb.h

# Build artifacts
*.obj
*.pdb
*.ilk
*.exp
*.lib
*.dll
!proxy/*.dll

# Python
__pycache__/
*.pyc
.venv/

# Logs
ffp_proxy.log
*.dmp

# OS
Thumbs.db
.DS_Store

# IDE
.vs/
*.suo
*.user
```

---

## Phase 16: .gitattributes

```
*.dll filter=lfs diff=lfs merge=lfs -text
*.exe filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text
*.bmp filter=lfs diff=lfs merge=lfs -text
*.jsonl filter=lfs diff=lfs merge=lfs -text
```

---

## Phase 17: README.md

```markdown
# GITHUB_REPO_NAME

RTX Remix compatibility project for **GAME_DISPLAY_NAME** (GAME_YEAR, GAME_DEVELOPER).

## What This Is

A D3D9 Fixed-Function Pipeline (FFP) proxy DLL that makes GAME_DISPLAY_NAME compatible with [NVIDIA RTX Remix](https://www.nvidia.com/en-us/geforce/rtx-remix/). The proxy intercepts DirectX 9 calls, reconstructs transformation matrices from vertex shader constants, and feeds them through the FFP — so RTX Remix sees the game as a native fixed-function title.

## DLL Chain

LAUNCHER_CHAIN

## Quick Start

1. Install Python dependencies: `pip install -r requirements.txt`
2. Verify toolkit: `python verify_install.py`
3. Build proxy: `cd proxy && build.bat`
4. Copy `d3d9.dll` + `proxy.ini` to game directory
5. Place RTX Remix's `d3d9_remix.dll` in game directory
6. Launch via `LAUNCHER_EXE`

## Status

See [WHITEBOARD.md](docs/status/WHITEBOARD.md) for current progress.

## Tools

| Tool | Purpose |
|------|---------|
| `retools/` | Offline PE static analysis (decompile, xrefs, RTTI, signatures) |
| `livetools/` | Frida-based live process analysis |
| `graphics/directx/dx9/tracer/` | Full-frame D3D9 API capture |
| `autopatch/` | Autonomous culling patch discovery |
| `gamepilot/` | Vision-guided game automation |

## License

See LICENSE file.
```

---

## Phase 18: Test Orchestrator

Create `patches/GAME_SHORT_NAME/run.py` — adapt from the toolkit's test orchestrator pattern. The script must:

1. Accept `test --build` CLI: build proxy, copy DLL+INI to game dir, run automated test
2. Accept `record` CLI: launch game for manual macro recording
3. Build proxy via `proxy/build.bat`
4. Copy `d3d9.dll` + `proxy.ini` to `GAME_DIR_NAME/`
5. Launch via `LAUNCHER_EXE` (or direct exe if no launcher)
6. Wait for game window
7. Phase 1: Hash debug screenshots (Remix debug view 277, gentle camera pan)
8. Phase 2: Clean render screenshots (debug view 0, same camera pan)
9. Phase 3: Livetools diagnostics (draw call census, patch integrity)
10. Phase 4: dx9tracer frame capture placeholder
11. Collect screenshots from NVIDIA capture folder at `SCREENSHOT_PATH`

Use the same structure as `patches/TombRaiderLegend/run.py` in the toolkit, substituting game-specific paths. Key constants:

```python
GAME_DIR = REPO_ROOT / "GAME_DIR_NAME"
GAME_EXE = GAME_DIR / "GAME_EXE"
LAUNCHER = GAME_DIR / "LAUNCHER_EXE"
PROXY_LOG = GAME_DIR / "ffp_proxy.log"
SCREENSHOTS_SRC = Path(r"SCREENSHOT_PATH")
```

---

## Phase 19: Trace Directory

Create `GAME_SHORT_NAME traces/README.md`:

```markdown
# GAME_SHORT_NAME Traces

Full-frame D3D9 API captures stored here. Each capture is a `.jsonl` file from the dx9tracer proxy.

## How to Capture

```bash
python -m graphics.directx.dx9.tracer trigger --game-dir "GAME_DIR_NAME" --frames 2
```

## How to Analyze

```bash
python -m graphics.directx.dx9.tracer analyze <capture.jsonl> --summary
python -m graphics.directx.dx9.tracer analyze <capture.jsonl> --draw-calls
python -m graphics.directx.dx9.tracer analyze <capture.jsonl> --shader-map
python -m graphics.directx.dx9.tracer analyze <capture.jsonl> --const-evolution vs:c0-c15
```
```

---

## Phase 20: Initial Analysis

After creating ALL files above, run the initial static analysis to discover the game's D3D9 usage. Run these commands and capture all output:

```bash
# 1. Verify toolkit
python verify_install.py

# 2. D3D9 analysis scripts (run ALL of these)
python rtx_remix_tools/dx/scripts/find_d3d_calls.py "GAME_DIR_NAME/GAME_EXE"
python rtx_remix_tools/dx/scripts/find_vs_constants.py "GAME_DIR_NAME/GAME_EXE"
python rtx_remix_tools/dx/scripts/decode_vtx_decls.py "GAME_DIR_NAME/GAME_EXE" --scan
python rtx_remix_tools/dx/scripts/find_render_states.py "GAME_DIR_NAME/GAME_EXE"
python rtx_remix_tools/dx/scripts/find_transforms.py "GAME_DIR_NAME/GAME_EXE"
python rtx_remix_tools/dx/scripts/classify_draws.py "GAME_DIR_NAME/GAME_EXE"
python rtx_remix_tools/dx/scripts/find_skinning.py "GAME_DIR_NAME/GAME_EXE"
python rtx_remix_tools/dx/scripts/find_blend_states.py "GAME_DIR_NAME/GAME_EXE"
python rtx_remix_tools/dx/scripts/find_matrix_registers.py "GAME_DIR_NAME/GAME_EXE"
python rtx_remix_tools/dx/scripts/find_texture_ops.py "GAME_DIR_NAME/GAME_EXE"
python rtx_remix_tools/dx/scripts/find_surface_formats.py "GAME_DIR_NAME/GAME_EXE"
```

**After running all scripts:**
1. Write ALL findings into CHANGELOG.md under a new `[DATE] INITIAL-ANALYSIS` section
2. Update the VS Constant Register Layout section in CLAUDE.md with whatever `find_vs_constants.py` and `find_matrix_registers.py` discovered
3. Update the Architecture Summary in CLAUDE.md with what `classify_draws.py` revealed (FFP vs shader-based rendering)
4. If the game uses SetTransform (FFP transforms), note that in CLAUDE.md — the proxy approach may differ
5. Delegate bootstrap to static-analyzer subagent in background:
   - `python -m retools.bootstrap "GAME_DIR_NAME/GAME_EXE" --project GAME_SHORT_NAME`

---

## Phase 21: Git Init and First Commit

```bash
cd GITHUB_REPO_NAME
git init
git add -A
git commit -m "bootstrap: RTX Remix workspace for GAME_DISPLAY_NAME

- FFP proxy template copied from vibe RE toolkit
- Claude Code config (agents, rules, skills, settings)
- Initial D3D9 analysis results in CHANGELOG.md
- Test orchestrator, WHITEBOARD, knowledge base seeded
- Ready for VS constant discovery and first proxy build

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

If a GitHub remote is configured, push.

---

## IMPORTANT RULES

1. **Do NOT skip any phase.** Create every file listed.
2. **Copy rules/agents/skills VERBATIM** from the toolkit — they are game-agnostic.
3. **The proxy template is the starting point** — copy it, don't rewrite it from scratch.
4. **Run ALL D3D9 analysis scripts** and populate CLAUDE.md with real findings, not placeholders.
5. **Placeholders marked [TO BE DISCOVERED]** stay until actual analysis reveals the answer.
6. **The test archive folder** pattern: `GAME_SHORT_NAME tests/build-NNN-description/`
7. **PASS builds** include "miracle" in the folder name.
8. **Every build — pass or fail — gets committed and pushed immediately.**
9. **Never retry a documented dead end without new evidence.**

## After setup, the workflow is:

1. **Discover** — VS constant register layout via static + live analysis
2. **Update** — Proxy defines in d3d9_device.c with correct register mappings
3. **Build** — `cd proxy && build.bat`, deploy to game dir
4. **Test** — Say "begin testing" for the full automated pipeline
5. **Diagnose** — Read proxy log, check screenshots, identify culling layers
6. **Patch** — NOP culling instructions at runtime via livetools, then promote to proxy source
7. **Document** — Every finding in CHANGELOG.md, every culling layer on WHITEBOARD.md
8. **Iterate** — Each build gets a test folder, dead ends get documented, progress tracked
9. **Never give up** — If one approach fails, document why and try the next hypothesis

---END---
