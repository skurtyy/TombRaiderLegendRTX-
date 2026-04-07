# LEGACY — replaced by hash-stability-test.md

# "Autopatch" Trigger (LEGACY)

**This workflow is LEGACY. Do NOT activate on "start autopatch", "run autopatch", "autopatch test", or "autonomous test". Those triggers now use hash-stability-test.md.** To run this legacy autopatch, the user must explicitly say **"run legacy autopatch"**.

## What This Is

Autopatch is the **fully autonomous** light visibility solver. Unlike the other two test procedures ("begin testing" = automated 3-phase test, "begin testing manually" = human-controlled), autopatch runs the ENTIRE loop — diagnose, hypothesize, patch, test, evaluate — with zero human input.

## Workflow

1. **Run autopatch**: `python -m autopatch`

   The system handles everything automatically:
   - **Phase 1: Diagnostic capture** — deploys the dx9 tracer DLL (swapping out the proxy), launches the game twice (Lara near stage, Lara far from stage), captures full frame JSONL at each position, diffs the two to find which draw calls disappear at distance, then restores the proxy DLL
   - **Phase 2: Hypothesis generation** — decompiles the calling functions of missing draws, extracts conditional jumps, ranks them by proximity and type, filters out the 37+ addresses already tried in builds 001-044
   - **Phase 3: Patch & test loop** — for each hypothesis: launches game with proxy, attaches livetools, applies runtime NOP patch via `mem write`, runs a 3-position movement macro with screenshots, evaluates screenshots for red+green light visibility using pixel heuristics, records results
   - **Phase 4: Promotion** — if a runtime patch passes, promotes it to proxy C source (`TRL_ApplyMemoryPatches` in `d3d9_device.c`), rebuilds the proxy, and deploys

2. **Monitor output**: The system prints progress for each iteration:
   ```
   Iteration iter_045: NOP 6-byte je at 0x40ACF0 (near caller 0x40AD12)
     Applying patch: 0x40ACF0 <- 909090909090
     Running 3-position evaluation macro...
     Verdict: passed=False, red=[True, True, False], green=[True, True, False]
   ```

3. **Stopping conditions**:
   - **PASS**: Both red+green lights visible in all 3 positions → promotes, rebuilds, done
   - **Exhaustion**: 10 consecutive failures → pauses with summary for human review
   - **No hypotheses**: All candidate addresses already tried → manual analysis needed

## Variants

| Command | What it does |
|---------|-------------|
| `python -m autopatch` | Full run (diagnostic + patch loop) |
| `python -m autopatch --skip-diagnosis` | Skip diagnostic capture, use existing data in `autopatch/diagnostic_captures/` |
| `python -m autopatch --dry-run` | Validate evaluator calibration only, no game launch |

## If the user says "skip diagnosis"

Run with `--skip-diagnosis` flag. This reuses the existing `autopatch/diagnostic_captures/diagnostic_report.json` and jumps straight to hypothesis generation + patch loop. Use this when diagnostic data was already captured in a previous run.

## Key Differences from Other Test Procedures

| Aspect | "begin testing" | "begin testing manually" | "autopatch" |
|--------|----------------|--------------------------|-------------|
| Human input | None (automated macro) | User plays the game | **None (fully autonomous)** |
| What it patches | Nothing (tests current build) | Nothing | **Runtime patches via livetools** |
| Iterations | Single test run | Single session | **Up to 10 automatic iterations** |
| Diagnosis | None | None | **Differential frame capture** |
| Goal | Evaluate current proxy | Evaluate current proxy | **Find and apply the winning patch** |

## Output

- `autopatch/knowledge.json` — iteration history (what was tried, what passed/failed/crashed)
- `autopatch/diagnostic_captures/` — near/far frame JSONL and diagnostic report
- If PASS: proxy source updated, rebuilt, deployed. Run `python patches/TombRaiderLegend/run.py test --build --randomize` for final verification.

## No Questions

Do not ask the user to launch the game, copy files, or confirm anything. The entire pipeline is automated. Just run it and report results.
