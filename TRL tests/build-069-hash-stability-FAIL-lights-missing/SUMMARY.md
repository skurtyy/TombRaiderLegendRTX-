# Build 069 — Hash Stability Test

## Result
**FAIL-lights-missing** — No red or green stage lights visible in any clean render screenshot.

## Test Configuration
- Level: Peru (Chapter 4, -NOMAINMENU)
- Camera: mouse pan only (300px left, 600px right)
- Debug view 277 (Phase 1), view 0 (Phase 2)
- All anti-culling patches active via proxy

## Phase 1: Hash Debug Analysis
- 3 screenshots captured (center, left, right)
- Center and left views nearly identical (minimal pan distance)
- Right view shows dramatically different perspective (wider scene with ground)
- Hash colors appear consistent within overlapping views
- No obvious hash color shifts between center/left views

## Phase 2: Light Anchor Analysis
- 3 screenshots captured (center, left, right)
- Camera confirmed moved — different buildings visible in each shot
- **No red lights visible in any screenshot**
- **No green lights visible in any screenshot**
- Scene lit only by neutral fallback light (rtx.fallbackLightRadiance = 1,1,1)
- Anchor geometry not being submitted = Remix loses light anchors

## Phase 3: Live Diagnostics

### Draw Call Census
- dipcnt failed to install ("Not installed" for all 3 positions)
- Draw counts from proxy log instead:
  - Cutscene: steady d=673
  - Gameplay start: spikes to d=2647
  - Rapidly drops: 2647 → 1390 → 911 → 673
  - Settles at ~670-694 during gameplay
  - **~75% of initial draws culled** — anchor geometry among them

### Patch Integrity
| Address | Expected | Actual | Status |
|---------|----------|--------|--------|
| 0xEFDD64 | -1e30 float | -1e30 float | OK |
| 0xF2A0D4/D8/DC | D3DCULL_NONE (1) | 0x01, 0x01, 0x01 | OK |
| 0x407150 | 0xC3 (RET) | 0x55 (PUSH EBP) | NOT PATCHED — proxy NOPs individual jumps instead |
| 0x60B050 | B0 01 C2 04 | B0 01 C2 04 | OK |

### Memory Watch
- SetWorldMatrix (0x413950): 43,188 hits in 15s — healthy call rate

### Function Collection
- Single address traced: 0x00413950 (SetWorldMatrix)
- Caller: 0x004150DF
- Consistent calling pattern

## Phase 4: Frame Capture Analysis
Skipped in this run.

### Draw Call Diff
N/A

### Constant Evolution
N/A

### Vertex Format Consistency
N/A

### Shader Map
N/A

## Phase 5: Static Analysis
Static analyzer subagent dispatched to verify on-disk patch sites (0x407150, 0x4070F0, 0x60B050). Results pending in findings.md.

## Phase 6: Vision Analysis
- Hash debug: center/left views show same colored blocks in same arrangement — stable
- Clean render: No colored lights visible. Only neutral ambient lighting from fallback light.

## Proxy Log Summary
- Build successful, all patches applied
- 11/11 cull jumps NOPed
- LightVisibilityTest patched to always-true
- Frustum threshold = -1e30
- Terrain cull gate NOPed at 0x40AE3E
- MeshSubmit_VisibilityGate patched at 0x454AB0
- Post-sector patches applied (bitmask, distance cull, stream gate)
- Sector_SubmitObject gates NOPed
- Mesh eviction NOPed
- Draw count drops from 2647 to ~673 after gameplay loads

## Brainstorming: New Hash Stability Ideas
1. The proxy applies ~40 patches but draw count still drops 75% — there are more culling gates
2. The draw count pattern (2647→673) suggests a culling system kicks in after initial scene load
3. s4 count stays at 421-429 during gameplay — S4 (vertex shader format 4) draws are stable
4. f3 count varies 200-272 — these FORMAT3 draws are the ones fluctuating

## Open Hypotheses
1. **TerrainDrawable path** (0x40ACF0) — separate terrain render with own culling, partially patched (0x40AE3E NOPed) but may have more gates
2. **LOD alpha fade** (0x446580) — 10 callers, may fade geometry at distance
3. **Scene graph sector early-outs** — unknown addresses, may gate geometry submission
4. **Draw count drop timing** — the rapid drop after gameplay start suggests a deferred culling system that takes a few frames to fully activate

## Next Steps
1. Investigate the draw count drop pattern — what triggers the 2647→673 transition
2. Fix dipcnt installation for proper per-position draw counting
3. Consider dx9tracer differential capture (near vs far) to identify exactly which draw calls disappear
4. Investigate remaining culling in the FORMAT3 draw category (fluctuates 200-272)
