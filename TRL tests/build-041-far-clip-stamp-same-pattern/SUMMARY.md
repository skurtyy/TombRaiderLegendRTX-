# Build 041 — Far Clip Distance Stamp (FAIL — Same Pattern)

## Result

**FAIL** — Same pattern as build 039. Shot 1: both lights. Shot 2: fallback only. Shot 3: green only. Far clip stamp had no effect.

## What Changed This Build

Added per-scene stamping of `g_farClipDistance` at 0x10FC910 to 1e30f in BeginScene. This ensures the far clip distance check (even outside SceneTraversal_CullAndSubmit) always passes.

## Proxy Log Summary

Same as build-040. Draw counts ~190K. All 11 NOPs active. No crashes.

## Open Hypotheses

The consistent pattern across builds 039-041 suggests:
1. The strafes send Lara far enough to enter different sectors
2. In the starting sector, both anchor meshes are drawn (both lights)
3. In the far-left sector, neither anchor mesh is drawn (fallback only)
4. In the far-right sector, the green anchor mesh IS drawn (green light works)
5. The red anchor meshes exist only in the starting sector's draw list

**Next: Need upstream caller analysis from static-analyzer to understand sector object lists.**

## Next Build Plan

Wait for static-analyzer to return the upstream caller chain of SceneTraversal_CullAndSubmit. The sector iteration at 0x46C180 likely controls which objects are passed per sector. Need to find and NOP the per-sector object list filter.
