# Build 073 — useVertexCapture=True

## Result
**FAIL-lights-missing** — No distinctly colored red/green stage lights visible. Small bright white dots present (possibly overexposed lights). Lara visible in hash debug. Draw counts stable ~3651.

## Test Configuration
- Level: Peru (Chapter 4)
- Camera: Mouse pan only
- Mod: 8 mesh hashes
- **Changed: `rtx.useVertexCapture = True`** (was False in build 072)
- RenderQueue_FrustumCull bypass active (from build 072)

## What Changed This Build
- Toggled `rtx.useVertexCapture = True` in rtx.conf
- No proxy code changes

## Phase 1: Hash Debug Analysis
- Lara visible in all 3 screenshots
- Camera clearly panned between shots
- Hash colors appear consistent
- More hash color variety visible (vertex capture changes how Remix sees geometry)

## Phase 2: Light Anchor Analysis
- Scene very dark (same as build 072)
- Small bright dots visible in screenshots — appear WHITE, not distinctly red/green
- Dots present in multiple shots at slightly different positions
- Could be the stage lights at extreme overexposure (intensity=10000000, exposure=20)
- Or could be specular highlights / other artifacts

## Phase 3: Live Diagnostics
- Draw counts: ~3651 (similar to 3657 in build 072)
- SetWorldMatrix calls: 21,181 in 15s (down from 36,905 — Remix GPU vertex capture reduces CPU calls)
- All patches verified active

## Proxy Log Summary
- All patches applied including RenderQueue_FrustumCull redirect
- Stable draw counts ~3651
- No crash, no GPU errors

## Observation: Are the White Dots Actually the Lights?
The mod's sphere lights have `intensity = 10000000` and `exposure = 20`. At these extreme values, any colored light would appear as a pure white dot — the color channels are so far into HDR that tonemapping clips them to white. If the lights ARE appearing but at max brightness:
1. Lower intensity to ~1000 and exposure to ~5
2. Or increase fallback light radiance to make the scene brighter so the colored lights stand out

## Next Steps
1. **Lower mod light intensity** to see if the white dots become colored
2. **Increase fallback light radiance** for better scene visibility
3. **Fresh Remix capture** to compare current hashes with mod
