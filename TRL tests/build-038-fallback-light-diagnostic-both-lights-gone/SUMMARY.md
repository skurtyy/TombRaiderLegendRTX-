# Build 038 — Fallback Light Diagnostic (FAIL — BOTH Lights Gone)

## Result

**FAIL** — BOTH stage lights (red AND green) disappear when Lara walks away from stage. Previous builds' "red light" at distance was actually the fallback light (`rtx.fallbackLightRadiance = 3, 0.3, 0.3`).

## What Changed This Build

- Changed `rtx.fallbackLightRadiance` from `3, 0.3, 0.3` (red-biased) to `1, 1, 1` (neutral white) to diagnose whether distant "red" was a stage light or fallback
- No proxy code changes

## Proxy Log Summary

Same as build-037 — all 10 patches active, vpValid=1, no crashes.

## Retools Findings (from static-analyzer subagent)

N/A — diagnostic build, no new static analysis needed.

## Ghidra MCP Findings

N/A — diagnostic build.

## Open Hypotheses (what we think is still wrong and why)

**CONFIRMED: The "red light" at distance in builds 019-037 was the fallback light, not the red stage light.** With neutral fallback (1,1,1), distant positions show flat gray/desaturated lighting with zero colored light. BOTH Remix-placed lights disappear simultaneously.

This reframes the entire problem:
- **Light function patches are irrelevant.** The engine's light culling functions (RenderLights_FrustumCull, Light_VisibilityTest, etc.) control the engine's native lights, not Remix-placed lights.
- **Remix lights are attached to geometry hashes.** When the underlying geometry hash is not submitted as a draw call, the Remix light placement disappears.
- **The root cause is geometry culling**, not light culling. The geometry meshes that the Remix lights are placed on are not being drawn when Lara is far from stage.

Despite all our culling patches (frustum RET, 7 cull NOPs, sector visibility NOPs, light gates, etc.), some geometry is still not being submitted at distance. The engine likely has another culling mechanism — possibly LOD-based, sector-based draw list filtering, or instance visibility flags — that prevents distant geometry from reaching `DrawIndexedPrimitive`.

## Next Build Plan (what to change next and what result to expect)

1. **Identify which geometry hashes the Remix lights are placed on** — check the Remix mod files (`.usd` or light placement configs) for the anchor hash values
2. **Add draw call logging to the proxy** — log all unique geometry hashes submitted per frame at the near-stage position vs the far position. Diff the two lists to identify which hashes disappear.
3. **Trace the geometry submission path** — the draw call originates from `InstanceDrawable::Draw()` or `TERRAIN_DrawUnits()`. Tracing these at both positions will reveal what filters out the stage geometry.
4. **Check if the issue is sector-scoped draw lists** — if sector data structures contain per-sector mesh lists, meshes in the stage sector may not be in other sectors' lists. This would be a data-level issue, not a code-level culling gate.
