# Build 073 — CONTENDER: First Stable Geometry Hashes

## Result
**PASS — STABLE GEOMETRY HASHES** (first ever confirmed)

In RTX Remix debug view 277 (Geometry/Asset Hash), world geometry maintains consistent hash colors across all camera positions. The same building, street, terrain mesh always gets the same hash regardless of where the camera points. This is the fundamental prerequisite for RTX Toolkit mesh replacement, material assignment, and light anchoring.

## What Made This Build Work

Two changes, layered on top of 28 previously patched culling layers:

### 1. RenderQueue_FrustumCull Bypass (Build 072)
**Address:** `0x40C430` → JMP to `0x40C390`

The engine's recursive BVH frustum culler was silently dropping entire geometry subtrees before they reached Remix. By redirecting to the engine's own "NoCull" path, all geometry is always submitted. This was Layer 30 — the last unpached culling layer and the prime suspect identified in the project docs.

### 2. useVertexCapture = True (Build 073)
**Config:** `rtx.useVertexCapture = True`

With the proxy providing stable FFP transforms and expanded FLOAT3 vertices, enabling GPU vertex capture gives Remix the stable vertex data it needs for consistent hash computation.

## Evidence
- Hash debug screenshots: same geometry shows same colors across center/left/right camera positions
- User confirmed in-game: "the hashes on the whole world don't change color"
- All 8 mod mesh hashes confirmed present in fresh Remix capture
- Draw counts stable at ~3,651 per frame
- No crash, no GPU errors

## What's Not Stable (And Why It's OK)
- Lara's character model hashes change per-frame due to skeletal animation
- This only affects animated meshes, not world geometry
- RTX Toolkit targets world geometry, not animated characters

## Configuration
- Proxy: `patches/TombRaiderLegend/proxy/d3d9_device.c` (30 culling patches)
- RTX config: `rtx.conf` (useVertexCapture=True, asset hash rule with positions)
- Mod: `pee/mod.usda` (8 light anchor hashes — all confirmed present)

## Metrics
| Metric | Value |
|--------|-------|
| Draw calls/frame | ~3,651 |
| SHORT4→FLOAT3 draws | ~3,413 |
| Culling layers patched | 30/30 |
| World hash stability | Stable ✓ |
| Character hash stability | Unstable (expected) |
| Crash | None |
| GPU errors | None |

## See Also
- `TECHNICAL_ANALYSIS.md` — full technical deep-dive (30-layer map, hash mechanics, proxy architecture)
