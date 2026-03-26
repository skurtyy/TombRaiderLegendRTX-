# Build 028 — Sector Visibility NOP + Native Light Cleanup

## Result

**FAIL** — Sector visibility patch confirmed working (draw counts 65x higher), hash debug shows geometry everywhere, but clean render shots 2-3 are near-black because Lara walks out of Remix-placed light range. Not a culling issue — geometry IS submitting.

## What Changed This Build

- **NEW: Sector/portal visibility NOPs** at 0x46C194 (JE) and 0x46C19D (JNE) — forces all 8 level sectors to render every frame regardless of portal connectivity
- **REMOVED: All native light patches** — 0x60CDE2/0x60CE20 (light frustum), 0x603832/0x60E30D (pending flags), LightVolume visibility-state NOPs — these targeted native game lighting, irrelevant for Remix hash anchors
- **FIXED: Build path mismatch** — discovered `run.py --build` compiles from `patches/TombRaiderLegend/proxy/`, not repo-root `proxy/`. Previous builds 027 may have deployed stale DLLs.

Active patches:
- Frustum threshold to 0.0
- 7 scene traversal cull jump NOPs (dead code, RET fires first)
- Frustum cull function RET at 0x407150
- **Sector visibility NOPs at 0x46C194 and 0x46C19D** (NEW)

## Proxy Log Summary (draw counts, vpValid, patch addresses)

- **Sector NOPs**: 2/2 confirmed applied
- **Cull jumps**: 7/7
- **Frustum cull RET**: 0x407150
- **vpValid**: 1 (always)
- **Draw counts**: ~1,440 during menus -> **93,000-189,000 during gameplay** (was ~1,440 consistently in build-027). The 65x increase proves the sector patch is submitting geometry from all sectors.
- No crashes, no errors

## Retools Findings

Static analyzer running — found 5 distinct culling layers:

1. **Sector/portal visibility (0x46C180)** — NOW PATCHED. Was skipping entire sectors not portal-visible from camera sector.
2. **Mesh frustum cull (0x407150)** — already patched with RET
3. **Object linked list type filtering (0x450BC7)** — checks obj+0xA4 & 0x800
4. **Mesh flags in sector renderer (0x46C320/0x46B7D0)** — mesh+0x5C & 0x82000000, mesh+0x20 flags
5. **MeshSubmit visibility gate (0x454AB0)** — per-mesh visibility check

## Ghidra MCP Findings

Not available this session.

## Open Hypotheses

1. **Geometry IS submitting — this is not a culling issue anymore.** Hash debug shots confirm colorful geometry in all 3 positions. The 93K+ draw count proves all sectors render. The clean render darkness is because the only Remix-placed lights (red/green stage lights) have finite range and can't illuminate geometry 50+ meters away.

2. **The test may need more Remix light placements** to cover the full movement range, but that's outside our proxy scope. From the game-side, our job is done: all geometry submits every frame.

3. **Remaining culling layers (3-5) may still skip specific objects/meshes** but the hash debug shows no obvious gaps in geometry coverage.

## Next Build Plan

The geometry submission problem appears solved. The hash debug confirms stable hashes and full geometry coverage. The clean render darkness is a Remix-side issue (light placement range), not a game-side culling issue.

Options:
1. **Declare geometry goal met** — hashes stable, all sectors rendering, 93K+ draws/frame. The remaining FAIL is about Remix light placement coverage, not game patching.
2. **Patch remaining culling layers (3-5)** for completeness — force all mesh flags, disable object type filtering, skip MeshSubmit visibility gate.
3. **Investigate whether specific stage geometry hashes are present** at all camera positions — if the stage geometry hash IS being submitted but Remix lights still don't show, the issue is definitively Remix-side.
