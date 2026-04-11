# Tomb Raider Legend — RTX Remix Port

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Platform: Windows x86](https://img.shields.io/badge/Platform-Windows%20x86-blue)
![Game: TRL 2006](https://img.shields.io/badge/Game-Tomb%20Raider%3A%20Legend%20(2006)-red)
![Builds](https://img.shields.io/badge/Builds-075-orange)
![Status](https://img.shields.io/badge/Status-In%20Progress-yellow)

Reverse-engineering Tomb Raider: Legend (2006) to run under NVIDIA RTX Remix — full path-traced lighting, stable geometry hashes, and complete scene visibility via a custom D3D9 FFP proxy DLL.

**75 builds completed · All 31 culling layers patched · Replacement asset pipeline confirmed end-to-end (build 075) · Fresh mesh hash capture needed to anchor stage lights**

---

## The Problem

TRL renders exclusively through **programmable vertex shaders**. RTX Remix requires the D3D9 **Fixed-Function Pipeline (FFP)** to assign stable geometry hashes, inject path-traced lights, and resolve material replacements. Shader-bound draws produce unstable hashes because Remix cannot decode VS constant semantics.

Remix also anchors scene lights to geometry draw calls. When TRL's culling systems hide geometry, Remix loses the anchor points and the lights vanish.

## The Solution

A custom `d3d9.dll` proxy that sits between TRL and Remix:

1. Intercepts every `DrawIndexedPrimitive` call
2. Reads TRL's vertex shader constants to reconstruct the W/V/P matrices
3. Calls `SetTransform` so Remix sees the draw as a native FFP call
4. Patches **31 culling layers** at runtime so all geometry is submitted regardless of camera position

---

## DLL Chain

```
NvRemixLauncher32.exe
        │
        ▼
    trl.exe  (game)
        │
        ▼
 dxwrapper.dll
        │
        ▼
    d3d9.dll  ◄── this project (FFP proxy)
        │
        ▼
 d3d9_remix.dll  (RTX Remix)
```

---

## Project Status

| Milestone | Status | Build |
|-----------|--------|-------|
| FFP proxy DLL — builds and chains to Remix | ✅ Done | 001 |
| Transform pipeline (View / Proj / World) | ✅ Done | 001 |
| Asset hash stability (static + moving camera) | ✅ Done | 028 |
| Automated two-phase test pipeline | ✅ Done | 018 |
| All 31 culling layers patched | ✅ Done | 072 |
| SHORT4 → FLOAT3 vertex buffer expansion | ✅ Done | 045 |
| Content fingerprint VB cache | ✅ Done | 046 |
| Character draws — Lara visible in RTX | ✅ Done | 071b |
| Replacement asset pipeline (mod lights, materials) | ✅ Confirmed end-to-end | 075 |
| **Both stage lights stable at all positions** | 🔄 In progress — fresh hash capture needed | — |

**Current status:** No full stage-light PASS yet — `build-019` showed both lights but was later confirmed a false positive (wrong screenshots evaluated; see build 020).

**Build 075 — breakthrough:** `user.conf` had `enableReplacementAssets=False`, silently disabling all mod content in every build since 016. Fixed. A purple test light anchored to `mesh_574EDF0EAD7FC51D` appeared immediately, held stable across all 3 camera positions, and shifted correctly with camera movement — confirming the entire pipeline works end-to-end.

> **Current focus:** Stage lights are absent only because the 8 anchor mesh hashes in `mod.usda` are stale (captured under a previous Remix config). All geometry is rendering (3749 draw calls/scene). Next step: capture a fresh frame with the Remix Toolkit near the Peru stage, extract current building mesh hash IDs, and update `mod.usda`.

Full status and decision tree: [`docs/status/WHITEBOARD.md`](docs/status/WHITEBOARD.md)

---

## How the Proxy Works

### Hooked D3D9 Methods

| Method | What it does |
|--------|-------------|
| `SetVertexShaderConstantF` | Captures VS constants into a per-draw register bank |
| `DrawIndexedPrimitive` | Reconstructs W/V/P matrices, calls `SetTransform`, chains to Remix |
| `SetRenderState` | Intercepts `D3DRS_CULLMODE` — forces `D3DCULL_NONE` |
| `BeginScene` | Stamps anti-culling globals (frustum threshold, cull mode, far clip) |
| `Present` | Logs diagnostics every 120 frames |

### VS Constant Register Layout (TRL-specific)

TRL packs matrices into fixed shader constant registers. View and Projection are **separate** — not a fused ViewProj.

```
c0  – c3    World matrix (transposed, row-major)
c8  – c11   View matrix
c12 – c15   Projection matrix
c48+        Skinning bone matrices (3 registers / bone)
```

### Runtime Patches — Applied at Proxy Attach

| Address | Patch | Effect |
|---------|-------|--------|
| `0x407150` (+ 11 internal sites) | NOP 6-byte branches | Disables all scene-traversal cull exits |
| `0x46C194`, `0x46C19D` | NOP | Sector/portal visibility gates — 65× draw count increase |
| `0x46B85A` | NOP | Camera-sector proximity filter |
| `0x60B050` | `mov al,1; ret 4` | `Light_VisibilityTest` always returns TRUE |
| `0x60CE20`, `0x60CDE2` | NOP | Light frustum 6-plane test + broad visibility check |
| `0x60E3B1` | NOP | RenderLights gate |
| `0x603AE6` | NOP | Sector light count clear per frame |
| `0xEC6337` | NOP | Sector light count gate |
| `0xEFDD64` | `-1e30f` | Frustum distance threshold (was `16.0f`) |
| `0xF2A0D4/D8/DC` | `D3DCULL_NONE` | Cull mode globals |
| `0x10FC910` | `1e30f` | Far clip distance |
| `0xEDF9E3` | Trampoline | Null-check guard (prevents crash on uninitialized pointer) |
| `0x40AE3E` terrain gate | NOP | Terrain distance/sector cull flag |
| `MeshSubmit_VisibilityGate` | `return 0` | Mesh visibility pre-check always passes |
| `0x415C51` stream unload | NOP | Prevents mesh stream eviction on camera movement |
| Mesh eviction (3 sites) | NOP | `SectorEviction` × 2 + `ObjectTracker_Evict` |
| `0x40C430` | JMP → `0x40C390` | Redirects BVH frustum culler to no-cull path (Layer 31, build 072) |

Full 31-layer culling map: [`docs/status/WHITEBOARD.md`](docs/status/WHITEBOARD.md)

---

## Quick Start

```bash
# Install Python dependencies
pip install -r requirements.txt

# Verify all tools are working
python verify_install.py

# Full build + test pipeline
python patches/TombRaiderLegend/run.py test --build

# Autonomous patch-and-test loop
python -m autopatch
```

**Pass criteria:** Both red and green stage lights visible in all 3 clean render screenshots, lights shift position as Lara strafes, hashes stable, no crash.

---

## Repository Layout

| Path | Description |
|------|-------------|
| [`proxy/`](proxy/) | D3D9 FFP proxy DLL — MSVC x86, no-CRT, the core of this project |
| [`retools/`](retools/) | Offline static analysis — decompile, xrefs, CFG, RTTI, signatures, crash dump analysis |
| [`livetools/`](livetools/) | Frida-based live analysis — tracing, breakpoints, memory r/w, D3D9 call counting |
| [`graphics/directx/dx9/tracer/`](graphics/directx/dx9/tracer/) | Full-frame D3D9 API capture — all 119 methods, with offline analysis |
| [`autopatch/`](autopatch/) | Autonomous hypothesis-test-patch loop |
| [`automation/`](automation/) | Screenshot automation and test replay infrastructure |
| [`docs/`](docs/) | Full documentation — research, reference, guides, session notes |
| [`TRL tests/`](TRL%20tests/) | Test build archive — every build with `SUMMARY.md`, screenshots, proxy log, source |
| [`TRL traces/`](TRL%20traces/) | Full-frame D3D9 API captures for offline analysis |

---

## Test Build Archive

Every test run produces a numbered folder in [`TRL tests/`](TRL%20tests/):

```
TRL tests/
└── build-NNN-<description>/
    ├── SUMMARY.md                     # Result, what changed, proxy log, findings, next plan
    ├── phase1-hash-debug-posN.png     # Hash debug view — geometry colored by asset hash
    ├── phase2-clean-render-posN.png   # Clean RTX render
    ├── ffp_proxy.log                  # Proxy diagnostics
    └── proxy/                         # Proxy source snapshot at time of test
```

PASS builds include `miracle` in the folder name. Every build — pass or fail — is committed and pushed immediately. See [`TRL tests/README.md`](TRL%20tests/README.md) for the full phase-by-phase archive.

> **Note:** Builds 003–015, 034, 043, and 048–063 were not preserved.

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/status/WHITEBOARD.md`](docs/status/WHITEBOARD.md) | **Live status** — 31-layer culling map, full build history narrative, decision tree, key addresses |
| [`docs/status/TEST_STATUS.md`](docs/status/TEST_STATUS.md) | Build-by-build pass/fail table, what's done, what remains |
| [`CHANGELOG.md`](CHANGELOG.md) | Cross-session development log — findings, patches, dead ends, next steps |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to contribute — setup, conventions, code review checklist |

---

## Developer Workflow

1. Read [`docs/status/WHITEBOARD.md`](docs/status/WHITEBOARD.md) — current culling map, build history, decision tree
2. Read [`docs/status/TEST_STATUS.md`](docs/status/TEST_STATUS.md) — build-by-build results and open items
3. Check the latest build folder in [`TRL tests/`](TRL%20tests/) and its `SUMMARY.md`
4. Read `patches/TombRaiderLegend/kb.h` — accumulated address map and struct layouts
5. Run `python patches/TombRaiderLegend/run.py test --build` to execute the full automated test pipeline

**Important:** `user.conf` in the game directory overrides `rtx.conf`. Always verify `rtx.enableReplacementAssets=True` is set in `user.conf` before testing mod content (the Remix developer menu regenerates this file and resets it to `False`).

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup instructions, coding conventions, and how to add a new culling layer patch.
