# Build 001 — Baseline Passthrough

**Date:** 2026-03-24
**Build:** Shader passthrough + transform override
**Result: PASS — Asset hashes STABLE across movement and sessions**

## Configuration

| Setting | Value |
|---------|-------|
| Resolution | 1024x768 |
| Proxy mode | Shader passthrough (shaders stay active, transforms overridden) |
| Skinning | Disabled (`ENABLE_SKINNING=0`) |
| Frustum culling | Patched (threshold=1e30, cull function returns immediately) |
| Asset hash rule | `indices,texcoords,geometrydescriptor` (excludes positions) |
| Generation hash rule | `positions,indices,texcoords,geometrydescriptor,vertexlayout,vertexshader` |
| Vertex capture | Enabled (`rtx.useVertexCapture = True`) |
| Fused world-view | Disabled (`rtx.fusedWorldViewMode = 0`) |

## Proxy Log Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Scene summaries | 9 | OK |
| vpValid | 1 (all frames) | PASS |
| passthrough | 0 (all frames) | PASS — 100% draws processed |
| xformBlocked | 0 | PASS |
| skippedQuad | 0 | OK |
| Crash | None | PASS |

Draw calls stable at 1,440 per 120-frame batch during gameplay, dropping to 834→119 during menu transition.

## Hash Stability Analysis

### Method
Geometry Hash debug view enabled via Remix menu (X key → Developer Settings → Debug View → Geometry Hash). Screenshots captured at 3 positions:
1. Standing (initial position after level load)
2. After D-strafe right (HOLD:D:2000 — 2 seconds)
3. After A-strafe left (HOLD:A:3000 — 3 seconds)

### Screenshots

| File | Description | Timestamp |
|------|-------------|-----------|
| `01-normal-view.png` | Normal rendered view (Bolivia cave) | 15:42:14 |
| `02-hash-standing.png` | Hash debug — initial position | 15:42:34 |
| `03-hash-strafe-right.png` | Hash debug — after D-strafe | 15:42:37 |
| `04-hash-strafe-left.png` | Hash debug — after A-strafe | 15:42:41 |

### Frame-by-Frame Analysis

#### Standing → D-Strafe Right (screenshots 02 vs 03)

| Geometry | Color in 02 | Color in 03 | Match? |
|----------|-------------|-------------|--------|
| Ground plane (center) | Tan/dark-yellow | Tan/dark-yellow | SAME |
| Ground plane (left) | Yellow-green | Yellow-green | SAME |
| Orange fern foliage | Orange | Orange | SAME |
| Blue leaf clusters | Blue | Blue | SAME |
| Dark teal bushes | Dark teal | Dark teal | SAME |
| Maroon rock face (top-left) | Dark red/maroon | Dark red/maroon | SAME |
| Lara's body | Cyan/green | Cyan/green | SAME |
| Pink hanging plants | Pink/magenta | Pink/magenta | SAME |

**Result: 8/8 tracked elements — ALL STABLE**

#### D-Strafe Right → A-Strafe Left (screenshots 03 vs 04)

Significant camera movement (~5 seconds of lateral movement). New geometry enters view while some exits.

| Geometry | Color in 03 | Color in 04 | Match? |
|----------|-------------|-------------|--------|
| Lara's character model | Cyan/green | Cyan/green | SAME |
| Ground mesh tiles | Green tones consistent | Green (different tile, same palette) | CONSISTENT |
| Rock faces | Purple/teal/green | Purple/teal/green | SAME |
| Foliage (ferns) | Orange/yellow | Orange/yellow | SAME |

**Result: All tracked elements — STABLE. No color shifting during movement.**

#### Cross-Session Verification

Compared screenshots from run at 15:36 to run at 15:42 (completely separate game launches):
- Ground planes: **SAME colors** across sessions
- Foliage: **SAME colors** across sessions
- Lara: **SAME cyan/green** across sessions
- Rock faces: **SAME colors** across sessions

**Result: Hashes are reproducible across game restarts.**

### Key Observations

1. **Static world geometry**: All ground tiles, rock faces, and foliage maintain their hash colors through lateral camera movement. The asset hash rule excluding positions is working correctly.

2. **Character model (Lara)**: Despite being a rigged/skinned mesh (submitted with BLENDWEIGHT/BLENDINDICES vertex elements), Lara's hash color is stable. With `ENABLE_SKINNING=0`, her mesh passes through without bone transform expansion, and the hash is computed on the raw vertex data which doesn't change.

3. **No flickering**: Zero color changes detected on any piece of geometry between frames. This is the primary indicator of hash stability.

4. **Cross-session reproducibility**: The same geometry produces the same hash color when the game is restarted. This means the hash computation is deterministic — critical for material replacement assignments in Remix.

### What This Means for RTX Remix

- Material replacements (PBR textures, enhanced materials) can be assigned to geometry by hash and will persist across sessions
- Light placements anchored to geometry hashes will remain correct
- Asset replacements (mesh swaps) will target the right geometry consistently
- The proxy's transform override approach (reading View/Proj from game memory, computing World via WVP decomposition) does not introduce hash instability

## Matrix Verification (from proxy log)

```
View (0x010FC780):  valid rotation matrix
Proj (0x01002530):  valid perspective projection
VP (computed):      View * Proj correct
World (applied):    WVP decomposition successful
```

Frustum culling patched at both threshold (`0x00EFDD64` → 1e30) and function level (`0x407150` → ret).

## Files

- `d3d9_device.c` — proxy source snapshot
- `ffp_proxy.log` — full diagnostic output
- `screenshots/` — 4 captures with descriptive names
- `SUMMARY.md` — this analysis
