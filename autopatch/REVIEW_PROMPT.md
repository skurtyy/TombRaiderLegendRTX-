# Autopatch Review — New Chat Handoff

## What to tell the new Claude session

Copy-paste this as your first message:

---

I just built an autonomous patching system called `autopatch/` for solving an RTX Remix compatibility issue with Tomb Raider Legend. Before I run it live, I need you to review every module for correctness, missed edge cases, and alignment with the existing codebase patterns.

## Context

The project makes Tomb Raider Legend work with NVIDIA RTX Remix via a D3D9 proxy DLL (`proxy/d3d9_device.c`). The proxy intercepts draw calls, decomposes fused WVP matrices, and patches 30+ culling gates in the game's memory. There's a full test pipeline (`patches/TombRaiderLegend/run.py`) that builds the proxy, launches the game, replays movement macros, captures screenshots, and evaluates pass/fail.

**The blocker:** Two Remix-placed stage lights (red + green) in the Bolivia level disappear when Lara walks away from them. The lights are anchored to geometry hashes — when the anchor geometry is culled by the game engine, the hash vanishes and the Remix light disappears. 44 manual builds have tried NOPing various culling gates without reliably solving this.

**What autopatch does:** Instead of blind patching, it diagnoses which specific draw calls disappear at distance using the dx9 tracer (differential frame capture), then generates targeted NOP hypotheses for the conditional jumps that gate those draws. It tests each hypothesis at runtime via livetools `mem write` (no rebuild needed), evaluates screenshots with pixel heuristics, and promotes winning patches to proxy C source.

## What I need you to review

Please read these files and check for:

1. **`autopatch/evaluator.py`** — Screenshot analysis via pixel heuristics. Does the grid-based red/green dominance detection make sense? Are the thresholds reasonable? Does it handle edge cases (black screenshots, partial lights)?

2. **`autopatch/knowledge.py`** — Iteration history persistence. Is the seed address list complete (cross-reference with `proxy/d3d9_device.c` defines)? Does the dedup logic correctly prevent re-trying failed addresses?

3. **`autopatch/safety.py`** — Backup/rollback. Is it sufficient? Missing any files that should be backed up?

4. **`autopatch/diagnose.py`** — Differential frame capture. This deploys the dx9 tracer DLL (`graphics/directx/dx9/tracer/bin/d3d9.dll`) to the game dir, captures frames at two positions, and diffs draw calls. Key questions:
   - Does `_fingerprint_draw()` create stable fingerprints that match the same geometry across two separate game launches?
   - Does the tracer work without the proxy (it needs to capture the game's NATIVE draw calls, not proxy-modified ones)?
   - Is the tracer's `proxy.ini` format correct (`[Capture]\nCaptureFrames=1`)?
   - Does `_launch_and_capture()` handle the setup dialog? (The game shows a setup dialog on first launch with a new d3d9.dll — the tracer DLL has a different hash than the proxy.)

5. **`autopatch/hypothesis.py`** — Patch candidate generation. Does `_extract_conditional_jumps()` correctly parse retools disassembly output? Are the confidence rankings reasonable?

6. **`autopatch/patcher.py`** — Runtime and source patching. Does `promote_to_source()` correctly find and insert into `TRL_ApplyMemoryPatches()` in `d3d9_device.c`? Does it follow the existing code pattern (VirtualProtect + write + log_str)?

7. **`autopatch/orchestrator.py`** — Main loop. Does the flow make sense? Are there race conditions (game launch timing, screenshot collection timing, livetools attach timing)?

8. **`autopatch/macros.json`** — Movement macros. Do the step sequences make sense for navigating Bolivia? The `]` key is the NVIDIA screenshot hotkey.

Also check:
- **Integration with `patches/TombRaiderLegend/run.py`** — does autopatch reuse its functions correctly or duplicate logic unnecessarily?
- **Integration with `livetools/`** — are the subprocess calls to livetools correct (command syntax, argument format)?
- **The design spec** at `docs/superpowers/specs/2026-04-03-autopatch-light-solver-design.md` — does the implementation match the spec?

## Critical concern

The BIGGEST risk is in `diagnose.py`: the tracer DLL replaces the proxy in the game directory. If the tracer's `proxy.ini` format doesn't match what the tracer expects, or if the tracer doesn't produce output without RTX Remix loaded, the diagnostic phase silently fails. Cross-reference with `graphics/directx/dx9/tracer/src/` to verify the INI section name and key names.

Also: the setup dialog. When a new d3d9.dll is deployed (the tracer), the game detects the changed adapter identifier and shows the setup dialog. `run.py` handles this with `dismiss_setup_dialog()`, but `diagnose.py`'s `_launch_and_capture()` does NOT call it — it only checks `find_hwnd_by_exe`. This will likely hang waiting for a window that never appears because the setup dialog blocks game startup.

---

## Files to read (in order)

1. `autopatch/orchestrator.py` — start here, it shows the full flow
2. `autopatch/diagnose.py` — the diagnostic capture logic
3. `autopatch/evaluator.py` — screenshot analysis
4. `autopatch/hypothesis.py` — patch generation
5. `autopatch/patcher.py` — patch application
6. `autopatch/knowledge.py` — persistence
7. `autopatch/safety.py` — backups
8. `autopatch/macros.json` — movement sequences
9. `proxy/d3d9_device.c` lines 1-160 (defines) and 2410-2650 (TRL_ApplyMemoryPatches)
10. `patches/TombRaiderLegend/run.py` lines 134-400 (dismiss_setup_dialog, launch_game, build_proxy)
11. `graphics/directx/dx9/tracer/cli.py` (trigger mechanism)
12. `docs/superpowers/specs/2026-04-03-autopatch-light-solver-design.md` (design spec)
