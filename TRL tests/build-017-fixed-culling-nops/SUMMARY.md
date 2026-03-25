# Build 017 — Fixed Culling NOPs + BeginScene Re-stamp

**Date:** 2026-03-25
**Build:** Shader passthrough + transform override + 3-layer anti-culling (fixed)
**Result: FAIL — Stage lights disappear after D strafe, hash colors shift between positions**

## What Changed (vs Build 016)

| Change | Before (016) | After (017) |
|--------|-------------|-------------|
| Frustum threshold value | 1e30 (WRONG — skips everything) | 0.0 (correct — skips nothing) |
| Scene traversal cull NOPs | Applied via ASI patcher (external) | 7 jumps NOPed directly in proxy source |
| BeginScene re-stamp | Comment in code, no implementation | Per-frame `0xEFDD64 = 0.0f` in BeginScene |
| VK_MAP `]` key | Missing (NVIDIA screenshots never captured) | Added (0xDD) — screenshots now work |
| Test procedure | Multiple random bursts 1-10s | Single A press + single D press, 1-10s each |

## Configuration

| Setting | Value |
|---------|-------|
| Resolution | 1024x768 |
| Proxy mode | Shader passthrough (shaders stay active, transforms overridden) |
| Skinning | Disabled (`ENABLE_SKINNING=0`) |
| Frustum culling | 3-layer disable: `0x407150→ret`, threshold `0.0`, 7 NOP jumps, per-frame re-stamp |
| Asset hash rule | `indices,texcoords,geometrydescriptor` (excludes positions) |
| Generation hash rule | `positions,indices,texcoords,geometrydescriptor,vertexlayout,vertexshader` |
| Vertex capture | Enabled (`rtx.useVertexCapture = True`) |
| Fused world-view | Disabled (`rtx.fusedWorldViewMode = 0`) |
| Replacement assets | Enabled (`rtx.enableReplacementAssets = True`) |
| Backface culling | Forced `D3DCULL_NONE` via SetRenderState hook |

## Anti-Culling Patches Applied

| Layer | Target | Patch | Purpose |
|-------|--------|-------|---------|
| 1. Per-object frustum test | `0x407150` | `ret` (0xC3) | Skip entire per-object visibility marking |
| 2a. Distance threshold | `0xEFDD64` | Set to `0.0f` | Objects skip when `distance <= threshold`; 0.0 = skip nothing |
| 2b. Distance cull jumps | `0x4072BD`, `0x4072D2`, `0x407AF1` | NOP (6 bytes each) | Scene traversal distance-check conditionals |
| 2c. Screen boundary jumps | `0x407B30`, `0x407B49`, `0x407B62`, `0x407B7B` | NOP (6 bytes each) | Viewport boundary culling in scene traversal |
| 2d. Per-frame re-stamp | `0xEFDD64` in BeginScene | `0.0f` every scene | Game recomputes threshold per-frame from camera params |
| 3. D3D backface culling | SetRenderState hook | Force `D3DCULL_NONE` | All backfaces visible for ray tracing |

## Test Parameters

| Parameter | Value |
|-----------|-------|
| A strafe duration | 9.6 seconds (random 1-10s) |
| D strafe duration | 7.4 seconds (random 1-10s) |
| Screenshots per phase | 3 (baseline, after A, after D) |
| Phases | Phase 1: `debugViewIdx=277` (asset hash), Phase 2: `debugViewIdx=0` (clean render) |

## Proxy Log Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Frustum threshold | 0.0 | CORRECT |
| Cull function ret | Applied (0x407150) | OK |
| NOP cull jumps | 7/7 | OK |
| Scene draws (scene 120) | 1,416 total | Stable |
| processed | 1,416 | 100% |
| vpValid | 1 | PASS |
| passthrough | 0 | PASS — all draws processed |
| xformBlocked | 0 | PASS |
| skippedQuad | 0 | OK |
| Crash | None | PASS |

## Hash Stability Analysis

### Method

Two-phase automated test via `run.py test --randomize`. Phase 1 captures asset hash debug view (index 277), Phase 2 captures clean render. Both phases replay the same macro: menu navigation → level load → baseline screenshot → A strafe → screenshot → D strafe → screenshot.

### Screenshots

| File | Phase | Description | Position |
|------|-------|-------------|----------|
| `01-hash-baseline.png` | Hash debug | Standing position after level load | Start |
| `02-hash-after-A.png` | Hash debug | After 9.6s A (left) strafe | Left of start |
| `03-hash-after-D.png` | Hash debug | After 7.4s D (right) strafe | Right of start |
| `04-clean-baseline.png` | Clean render | Standing position after level load | Start |
| `05-clean-after-A.png` | Clean render | After 9.6s A strafe | Left of start |
| `06-clean-after-D.png` | Clean render | After 7.4s D strafe | Right of start |

### Hash Debug View Analysis

#### Baseline (01) vs After A Strafe (02)

| Geometry | Color in 01 | Color in 02 | Match? |
|----------|------------|------------|--------|
| Ground plane (center) | Tan/dark-yellow | Tan/dark-yellow | SAME |
| Ground plane (left) | Yellow-green | Yellow-green | SAME |
| Orange fern foliage | Orange | Orange | SAME |
| Lara character model | Cyan/green | Cyan/green | SAME |
| Rock faces (left) | Maroon/dark red | Maroon/dark red | SAME |
| Pink/magenta plants | Pink | Pink | SAME |

**Result: Appears stable between baseline and A strafe.**

#### After A Strafe (02) vs After D Strafe (03)

| Geometry | Color in 02 | Color in 03 | Match? |
|----------|------------|------------|--------|
| Ground plane | Tan/yellow-green | Tan/peach | **SHIFTED** |
| Rock faces | Maroon/teal | Multi-color (olive, pink, magenta) | **SHIFTED** |
| Foliage | Orange/blue | Purple/blue | **SHIFTED** |
| Lara character model | Cyan/green | Cyan/green | SAME |
| Sky/background | Maroon/dark | Black void | **DIFFERENT** |

**Result: FAIL — Level geometry colors shifted significantly after D strafe. Lara's model stayed consistent but world geometry hashes changed. This indicates either:**
- **Geometry streaming**: different mesh data loaded at the D-strafe position (different geometry = different hash = different color)
- **Hash instability**: same geometry producing different hashes depending on camera/position
- **LOD switching**: lower/higher detail meshes swapped in, producing different hashes

### Clean Render Analysis — Stage Lights

| Screenshot | Red Light | Green Light | Verdict |
|------------|-----------|-------------|---------|
| 04-clean-baseline.png | **VISIBLE** (bright red, left side) | **VISIBLE** (bright green, right side) | **PASS** |
| 05-clean-after-A.png | **VISIBLE** (bright red, left side) | **VISIBLE** (bright green, right side) | **PASS** |
| 06-clean-after-D.png | **NOT VISIBLE** | **NOT VISIBLE** | **FAIL** |

**Result: FAIL — Both stage lights disappear after D strafe.** This confirms either:
1. The geometry the lights are anchored to (`mesh_ECD53B85CBA3D2A5` red, `mesh_AB241947CA588F11` green) is being culled or unloaded at the D-strafe position
2. The mesh hashes changed at that position, so the lights no longer match any rendered geometry

## Key Observations

1. **Frustum threshold fix was necessary but not sufficient.** Changing from 1e30 to 0.0 fixed the inverted logic (game skips when `distance <= threshold`), but geometry still disappears at certain positions.

2. **Anti-culling has at least one unpatched path.** Despite patching the frustum function to `ret`, NOPing 7 cull jumps, and re-stamping the threshold per-frame, geometry still unloads. Likely causes:
   - **Level streaming/sector system**: TRL may load/unload entire level chunks based on player position, independent of frustum culling
   - **LOD alpha fade** at `0x446580` (10 callers across codebase) — may fade geometry to invisible
   - **Scene graph sector boundaries** — the scene traversal at `0x407150` may have sector-based early-outs we haven't patched

3. **Lara's hash is stable.** Her character model consistently shows cyan/green in the hash view regardless of position. The instability is in world/level geometry only.

4. **The `]` key fix was critical.** Previous tests captured zero screenshots because `]` (VK 0xDD) was missing from the VK_MAP in gamectl.py. All prior "PASS" results for build 016 were based on manually captured screenshots, not automated test results.

5. **Per-frame re-stamp is working.** The proxy log confirms threshold is 0.0, and the BeginScene hook reapplies it every scene. The game's per-frame recomputation is being overridden.

## What This Means

The 3-layer anti-culling approach addresses frustum-based visibility but misses at least one other geometry removal system. The next build needs to investigate:
- Scene graph sector/room loading (separate from frustum culling)
- LOD fade system at `0x446580`
- Whether the `0x407150→ret` patch is actually helping or causing issues (it prevents the entire scene traversal function from running — maybe some geometry depends on it for submission)

## Matrix Verification (from proxy log)

```
View (0x010FC780):  0.75  0.00  0.00  0.00 | 0.00 -0.10  0.99  0.00 | 0.00 -1.16 -0.08  0.00 | -0.00  0.00  0.00  1.00
Proj (0x01002530):  2.00  0.00  0.00  0.00 | 0.00 -2.28  0.00  0.00 | 0.00  0.00  1.00  1.00 | 0.00  0.00 -16.00  0.00
VP (computed):      1.50  0.00  0.00  0.00 | 0.00  0.23  0.99  0.99 | 0.00  2.65 -0.08 -0.08 | 0.00  0.00 -16.00  0.00
World (applied):    1.33  0.00  0.00  0.00 | 0.00 -0.07 -0.85  0.00 | 0.00  0.99 -0.08  0.00 | 0.00  0.00  0.00  1.00
```

## Stage Light Mesh Hashes (from mod.usda)

| Mesh Hash | Light Color | Intensity | Radius |
|-----------|-------------|-----------|--------|
| `mesh_ECD53B85CBA3D2A5` | Red | 200 | 40 |
| `mesh_AB241947CA588F11` | Green | 100 | 40 |

## Files

- `d3d9_device.c` — proxy source with 3-layer anti-culling
- `screenshots/` — 6 captures (3 hash debug + 3 clean render)
- `SUMMARY.md` — this analysis

## Mistakes to Avoid in Future Builds

- **Do NOT set frustum threshold to 1e30** — the game's check is `skip if distance <= threshold`, so 1e30 culls everything
- **Do NOT assume hash view alone confirms anti-culling** — culling happens behind the camera, stage lights are the definitive test
- **Do NOT assume `0x407150→ret` is safe** — it prevents the entire scene traversal/submit function from running; some geometry may depend on this function for submission
- **Do NOT change the test procedure** — only the random A/D hold times vary between tests
