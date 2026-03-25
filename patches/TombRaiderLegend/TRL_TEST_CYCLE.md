# TRL RTX Remix — Test Cycle Guide

Instructions for Claude Opus sessions working on Tomb Raider Legend RTX Remix proxy development.

## What This Project Does

We're building a D3D9 proxy DLL (`proxy/d3d9_device.c`) that intercepts TRL's rendering calls to make them compatible with RTX Remix (NVIDIA's path tracing injector). The proxy must:
1. Produce **stable asset hashes** so Remix can identify geometry consistently
2. **Disable all culling** so Remix has all geometry available for ray tracing (culling happens behind the camera — the game unloads geometry based on position)

## Test Procedure

Run this after every proxy code change:

```bash
python patches/TombRaiderLegend/run.py test --build --randomize
```

This does:
1. Builds the proxy DLL and deploys to game directory
2. Phase 1: Launches game with `debugViewIdx = 277` (asset hash debug view), replays macro (menu nav → level load → baseline screenshot → A strafe 1-10s → screenshot → D strafe 1-10s → screenshot), collects screenshots
3. Phase 2: Same but with `debugViewIdx = 0` (clean render), captures screenshots showing actual lighting

**NEVER modify the test procedure** except the random A/D hold time range (1-10 seconds). The test must be consistent across builds.

## Pass/Fail Criteria

**A build PASSES only when ALL of these are true:**

1. **Both red AND green stage lights visible in ALL 3 clean render screenshots** (baseline, after A, after D). The mod has sphere lights anchored to specific mesh hashes — if hashes shift or geometry is culled, lights disappear.
2. **Hash debug view colors do NOT shift** — same geometry keeps same color across all 3 positions.
3. **No crash** during either phase.
4. **Proxy log shows all patches applied** (frustum threshold, NOP jumps, etc.)

If ANY clean screenshot is missing a stage light, the build **FAILS**.

## What To Do With Results

### On FAIL:
1. Read the proxy log (`patches/TombRaiderLegend/ffp_proxy.log`) — check patch counts, draw stats
2. View ALL screenshots — identify what's wrong (dark = culling, color shift = hash instability)
3. Upload to GitHub as failed build:
   - Create `TRL tests/build-NNN-<description>/` with SUMMARY.md, screenshots/, d3d9_device.c
   - Commit and push to `main` branch on `origin` (skurtyyskirts/TombRaiderLegendRTX-)
4. Diagnose the root cause (see Known Issues below)
5. Fix the proxy source code
6. Test again

### On PASS:
1. Upload to GitHub with **"miracle"** in the build title
2. Celebrate — this means stable hashes + working anti-culling confirmed

## Upload Format (GitHub)

Each build gets a folder in `TRL tests/`:
```
TRL tests/build-NNN-<description>/
  SUMMARY.md          — detailed test results (see template below)
  screenshots/        — all captured screenshots (hash debug + clean render)
  d3d9_device.c       — proxy source at time of test
```

Push via `git push origin main` (we're on the `main` branch tracking `origin/main`).

Commit message format:
```
test: build-NNN <description> — hashes <STABLE/UNSTABLE>, lights <PASS/FAIL>
```

For passing builds:
```
test: build-NNN miracle — <description> — hashes STABLE, lights PASS
```

## SUMMARY.md Template

Every build SUMMARY.md must include ALL of these sections. See `TRL tests/build-017-fixed-culling-nops/SUMMARY.md` for a full example.

```markdown
# Build NNN — <Description>
**Date:** YYYY-MM-DD
**Build:** <proxy mode description>
**Result: <PASS/FAIL> — <one-line summary>**

## What Changed (vs Build NNN-1)
Table: | Change | Before | After |

## Configuration
Table: Resolution, proxy mode, skinning, culling patches, hash rules, vertex capture, fused world-view, replacement assets, backface culling

## Anti-Culling Patches Applied
Table: | Layer | Target | Patch | Purpose |

## Test Parameters
Table: A strafe duration, D strafe duration, screenshots per phase

## Proxy Log Metrics
Table: | Metric | Value | Status |
Include: frustum threshold, NOP count, scene draws, vpValid, passthrough, xformBlocked, skippedQuad, crash

## Hash Stability Analysis
### Method — describe how test was run
### Screenshots — table of all files with phase/description/position
### Frame-by-Frame Analysis
For each pair of consecutive screenshots, table comparing specific geometry elements:
| Geometry | Color in shot A | Color in shot B | Match? |
Call out SAME or SHIFTED for each element.

### Clean Render Analysis — Stage Lights
| Screenshot | Red Light | Green Light | Verdict |
Each screenshot gets VISIBLE or NOT VISIBLE for each light.

## Key Observations
Numbered list of important findings, root cause analysis, what was learned.

## Mistakes to Avoid in Future Builds
Bullet list of things NOT to repeat, based on what went wrong or what was discovered.

## Files
List of included artifacts.
```

## Mistakes From Previous Builds (DO NOT REPEAT)

- **Frustum threshold 1e30 is WRONG** (build 016) — game check is `skip if distance <= threshold`, so 1e30 culls everything. Must be `0.0f`.
- **Hash view alone does NOT confirm anti-culling** — culling happens behind the camera. Stage lights are the only definitive test.
- **`0x407150→ret` may be too aggressive** (build 017) — it prevents the entire scene traversal function from running. Some geometry may depend on this function for submission, not just visibility marking.
- **VK_MAP must include `]`** (build 016-017) — without `0xDD` in gamectl.py VK_MAP, NVIDIA overlay screenshots are never captured and tests appear to pass with zero evidence.
- **`user.conf` overrides `rtx.conf`** (build 016) — Remix loads config layers in order. `rtx.enableReplacementAssets = False` in user.conf silently disables all mod lights/materials.
- **Do NOT change the test procedure** — only the random A/D hold time (1-10s) varies. One A press, one D press, screenshots at each position.
- **Do NOT batch-push test results** without actual code changes between runs.

## Known Issues & Fix Areas

### Hash instability (colors shift in debug view)
- Check `rtx.geometryAssetHashRuleString` in rtx.conf — must exclude `positions`
- Check vertex data being submitted — any per-frame varying data in the hash input causes instability
- Check if skinning introduces position variation

### Stage lights disappearing (culling)
- **Frustum threshold**: must be `0.0f`, NOT `1e30f`. Game check is `skip if distance <= threshold`.
- **Per-frame re-stamp**: game recomputes threshold every frame — BeginScene must re-stamp `0xEFDD64 = 0.0f`
- **Scene traversal cull jumps**: 7 conditional jumps inside `0x407150` must be NOPed (6 bytes each)
- **0x407150 ret patch**: patches the per-object frustum test function to return immediately
- **D3DCULL_NONE**: SetRenderState forces backface culling off

### Proxy source location
- Source: `proxy/d3d9_device.c`, `proxy/d3d9_main.c`, `proxy/d3d9_wrapper.c`
- Build: `proxy/build.bat` (MSVC x86, no CRT)
- Config: `proxy/proxy.ini`
- Game dir: `Tomb Raider Legend/`
- RTX config: `Tomb Raider Legend/rtx.conf`

## Key Addresses (TRL.exe)

| Address | Purpose |
|---------|---------|
| `0x010FC780` | View matrix (row-major, 16 floats) |
| `0x01002530` | Projection matrix (row-major, 16 floats) |
| `0x00EFDD64` | Frustum distance threshold (float) |
| `0x00407150` | SceneTraversal_CullAndSubmit (4049 bytes) |
| `0x004072BD` | Distance cull jump 1 (6-byte conditional) |
| `0x004072D2` | Distance cull jump 2 |
| `0x00407AF1` | Distance cull jump 3 |
| `0x00407B30` | Screen boundary jump 1 |
| `0x00407B49` | Screen boundary jump 2 |
| `0x00407B62` | Screen boundary jump 3 |
| `0x00407B7B` | Screen boundary jump 4 |

## Stage Light Mesh Hashes (from mod.usda)

| Mesh Hash | Light Color |
|-----------|-------------|
| `mesh_ECD53B85CBA3D2A5` | Red (intensity 200, radius 40) |
| `mesh_AB241947CA588F11` | Green (intensity 100, radius 40) |

Both must be visible in all clean screenshots for a PASS.
