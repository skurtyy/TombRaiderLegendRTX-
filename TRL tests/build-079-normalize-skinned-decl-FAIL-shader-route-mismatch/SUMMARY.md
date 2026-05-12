# Build 079 — Normalize Skinned Decl (FAIL: shader-route mismatch)

## Result

**FAIL — Lara hash colors still drift.** World remains stable. The fix as implemented does not engage for Lara because she takes the **shader route**, not the null-VS path where my decl swap is wired.

## What Changed This Build

Added a normalized-decl path for skinned draws (Lara). The proxy now:

1. **Caches a clone of every skinned decl** with `BLENDWEIGHT` and `BLENDINDICES` elements removed (offsets/types preserved for everything else). Mirrors the existing `BuildStrippedDeclIfNeeded` infrastructure. New helper: `BuildSkinnedNormalizedDecl()` near [proxy/d3d9_device.c:4240](proxy/d3d9_device.c).
2. **In the FLOAT3 null-VS draw path** (lines 3651-3666): swaps to the normalized decl around the FFP-facing `DrawIndexedPrimitive`, restores the original after. Tight scope, mirrors the existing VS-null/restore pattern.
3. **In `WD_SetVertexDeclaration`** (~line 4366): when `curDeclIsSkinned`, builds the normalized clone and stashes it in `self->curNormalizedSkinnedDecl`. First 8 unique skinned decls are dumped to `ffp_proxy.log` (always-on log, not gated by `DIAG_ENABLED`).
4. **Cache fields + INI toggle** added to `WrappedDevice` struct: `skinnedNormDecl{Orig,Fixed}[64]`, `curNormalizedSkinnedDecl`, `normalizeSkinnedDecl` (default 1, INI key `[FFP] NormalizeSkinnedDecl=1`), `skinnedDeclsLogged`.
5. **Cleanup hooks** added in `~WrappedDevice` (line 3055 area) and `Reset` (line 3229 area) to release normalized decls when the device dies or resets.
6. **`proxy.ini`** updated with the `NormalizeSkinnedDecl=1` entry under `[FFP]` plus a comment explaining the toggle.

DLL size: 50,176 bytes (was 48,640 in build 078).

## Proxy Log Summary

> **Caveat:** the log shipped in this folder was generated under the **old build 078** — the user's test ran before correct deployment. The deployment workflow was the immediate cause of the wasted cycle, not the fix itself.

Even so, the old log proved the key fact we needed about the route. Key lines:

```
Float3Route effective: shader      ← Lara's FLOAT3 draws take SHADER route
Float3RoutingMode: auto             ← default
SkyIsolation: 1
useVertexCapture (rtx.conf): 1     ← drives auto-mode to shader route
```

Latched-scene draw mix:
```
 d=600        ← total processed draws
 s4=579       ← SHORT4 (mostly world geometry via S4 cache path)
 f3=21        ← FLOAT3
```

No `SKINNED decl=` lines (those are introduced by *this* build; absence confirms old DLL was loaded).

## User Observations

User ran the test in-game, hash-debug "geometry view" enabled, two camera positions.

- **World geometry**: solid color blocks, stable between frames. ✓
- **Lara**: per-vertex colored gradients across her body, completely different palette between frames. ✗
- **Distant NPC (small silhouette behind Lara)**: solid color block, but **also different colors between frames** — confirms the instability is not unique to Lara, it affects skinned characters generally.

Screenshot artifacts are at the camera positions; both meshes (Lara + the distant NPC) drift; world does not.

## Workspace Deployment Rule (NEW)

`proxy/d3d9.dll` and `proxy/proxy.ini` **must** be auto-deployed after every build to:

```
C:\Users\skurtyy\Documents\GitHub\AlmightyBackups\NightRaven1\Vibe-Reverse-Engineering-Claude\Tomb Raider Legend\
```

(Sibling of the repo, NOT the `Tomb Raider Legend/` stub *inside* the repo, which contains only `d3d9.dll`/`rtx.conf`/`rtx-remix/` and no `trl.exe`.) Saved to project memory at `memory/feedback_proxy_deployment.md`.

## Retools Findings

None this build — the question was a Remix-pipeline question, not a static-analysis question. Future investigation should use `dx9tracer` once the new build is correctly deployed, specifically `--vtx-formats` and `--diff-frames 0 1` filtered to skinned draws.

## Open Hypotheses

1. **Skinned FLOAT3 (or SHORT4) draws are routed through the shader path (vertex-capture) and asset-hash drift is a property of that path for skinned meshes.** The shader route hands Remix the VS *output*, which is post-bone-skinning. Even though the asset hash rule excludes `positions`, something in how Remix computes `geometrydescriptor` (or another component) for VS-captured skinned draws drifts per-frame. **Strongest hypothesis given the data.**

2. **The "debug geometry view" the user is looking at may be the *generation* hash visualization, not the *asset* hash.** Generation hash includes positions and is expected to flicker for skinned meshes by Remix's design (per build-073 TECHNICAL_ANALYSIS.md and the Rosetta Stone doc). Need to confirm which view the user is actually toggling. If it's generation hash, the colors WILL drift on Lara forever — fix would be to point the user at the asset-hash visualization instead.

3. **Lara may not be FLOAT3 skinned at all — she may be SHORT4 skinned.** The build-071b SUMMARY references "FLOAT3 character draws" but that may describe one specific draw type, not all of Lara. The latched-scene draw mix in the old log shows 579 SHORT4 vs 21 FLOAT3 — most of the renderable world (likely including character meshes) is SHORT4. If so, the right hook is `TRL_ShouldShaderRouteAnimatedShort4Draw` (line ~1044), not the FLOAT3 null-VS branch.

4. **The fix is correct in principle but needs to fire on the shader route too.** Swapping the decl on the *shader* route is risky — the game's bound VS expects to read `BLENDWEIGHT`/`BLENDINDICES` from the VB, and stripping them from the decl would feed the VS zeros for those slots → Lara renders bind-pose / collapsed / broken. Two viable variants:
   - Force `Float3Route = null_vs` for skinned FLOAT3 draws only (override at draw-routing time). Tradeoff: Lara through Remix renders bind-pose since VS is null'd; game-side animation invisible to Remix.
   - Issue Lara as TWO submissions: one shader-route for the visible draw, one null-VS for Remix's hash anchor. Doubles cost; Remix may see her twice.

## Next Build Plan

**Before pivoting the fix**, confirm hypothesis #2: ask the user to verify they're looking at the asset-hash debug visualization in Remix and not the generation-hash one. If the asset-hash view is itself stable, no proxy change is needed — the user's anchor workflow just needs to use asset hashes.

If asset-hash IS drifting on Lara (true positive), then in the next build:

1. **Deploy this build's DLL correctly** to the sibling game dir. Have the user retest with the new build so the always-on `SKINNED decl=` log entries actually fire.
2. **Read `SKINNED decl=` lines** in the resulting log — they'll tell us:
   - Whether Lara is FLOAT3 or SHORT4 (decl element types)
   - How many unique skinned decls exist (LOD variants? one or many?)
   - Whether the normalized clones are being created (`normalized=` value non-null)
3. **Branch on the answer**:
   - If Lara is SHORT4 → extend `shaderRouteShort4` path with the same decl swap, but ONLY when going through `S4_ExpandAndDraw` (the SHORT4-CPU-expand path that's already null-VS for world). That keeps animation working.
   - If Lara is FLOAT3 → add a per-draw override that pushes skinned FLOAT3 through `FLOAT3_ROUTE_NULL_VS` regardless of `useVertexCapture`. Lara visual through Remix becomes bind-pose (known tradeoff). Use a new INI toggle `[FFP] SkinnedFloat3Route=null_vs|shader` defaulting to `shader` so the experiment is opt-in.

## Out of scope (DO NOT)

- Do NOT enable `ENABLE_SKINNING` or touch `proxy/d3d9_skinning.h` — per `.claude/rules/dx9-ffp-port.md`.
- Do NOT remove `positions` from `rtx.geometryAssetHashRuleString` — Dead End #10.
- Do NOT null VS for ALL draws — Dead End #9 (view-space FLOAT3 breaks).
