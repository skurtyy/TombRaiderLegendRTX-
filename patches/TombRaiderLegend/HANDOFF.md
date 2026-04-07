# Session Handoff — 2026-04-07 (Session 2)

## What Was Accomplished This Session

### Light Anchor Hashes Re-captured (MAIN TASK)
The texcoord fix from the previous session changed all Remix mesh hashes. We did a fresh Remix scene capture and re-anchored the 5 mod lights to the new stable hashes.

**New hashes (in `C:\Users\skurtyy\Desktop\pee\mod.usda`):**

| Hash | Color | Vertices | Old Hash |
|------|-------|----------|----------|
| `mesh_2509CEDB7BB2FAFE` | Red | 365 | `mesh_C2C179B634F5514F` |
| `mesh_47AC93EAC3777CA5` | Red | 332 | `mesh_31348F166C43A6D2` |
| `mesh_DD7F8EE7F4F3969E` | Green | 315 | `mesh_165747062542D93A` |
| `mesh_CE011E8D334D2E48` | Green | 312 | `mesh_B4A7747EB715B894` |
| `mesh_2AF374CD4EA62668` | Red | 298 | `mesh_FC01B87FFE63D61B` |

Vertex counts match exactly between old and new captures — same Peru street building meshes, different hashes due to texcoord data.

### Hash Stability Confirmed Across Captures
Two captures taken (one without world transform, one with) — **2278/2278 meshes identical, zero drift**. Hashes are fully stable regardless of world transform state.

### Remix Capture Pipeline Fixed
Discovered and fixed two blockers preventing automated Remix scene captures:
1. **`rtx.captureShowMenuOnHotkey`** defaults to `True`, which opens a menu instead of capturing directly. Set to `False` in `rtx.conf`.
2. **`rtx.enableReplacementAssets`** must be `False` for capture to work. The `user.conf` was overriding `rtx.conf` back to `True`. Must disable in BOTH files for capture, then re-enable after.
3. **`client.DirectInput.forward.keyboardPolicy = 3`** set in `.trex/bridge.conf` to ensure keyboard input reaches the Remix server process (game was swallowing keys via DirectInput).

### Config Changes Made
- `Tomb Raider Legend/rtx.conf`: Added `rtx.captureShowMenuOnHotkey = False` (permanent, useful)
- `Tomb Raider Legend/.trex/bridge.conf`: Set `client.DirectInput.forward.keyboardPolicy = 3` (permanent, enables Remix hotkeys)
- `Tomb Raider Legend/user.conf`: Temporarily set `enableReplacementAssets = False` for capture, **restored to True**
- `.claude/rules/hash-stability-test.md`: Updated light anchor hash table with new hashes + vertex counts
- Memory files: Updated `project_trl_stage_light_hashes.md` with new hashes

## What Was NOT Done
- **Hash stability test was NOT run** — hashes are updated but the automated test (`run.py test --build`) has not been executed yet
- **Proxy was NOT rebuilt** — the DLL deployed in the game dir is from the previous session (11:06 build with texcoord fix), still current
- **Build.bat has a VS detection issue** — the `vswhere.exe` call doesn't find VS 18 Community properly. Manual build works with explicit path: `"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat"`

## What To Do Next

### 1. Run Hash Stability Test
Say "begin testing" to run the full automated test. This will verify:
- Hash debug screenshots show consistent colors across camera positions
- Clean render shows red AND green stage lights in all 3 positions
- Draw counts are stable
- Patches are holding

### 2. If Lights Don't Appear
The lights have diagnostic settings (intensity=100000, radius=5000, translate=0,0,0). If they still don't show:
- Check if `enableReplacementAssets = True` is set in user.conf (it should be)
- Verify the `pee` mod path is loaded (look for `Adding asset search path: ...mods/pee/` in Remix log)
- The hashes are confirmed stable, so if lights vanish on camera move, it's a culling issue (see Layer 3 below)

### 3. Layer 3 Frustum Culler (If lights vanish at distance)
An unpatched recursive frustum culler at `0x40C430` operates AFTER mesh submission. Options:
- Option A: Write FLT_MAX to `_level` at `0x10FC910` (far-plane boundary)
- Option B: Redirect `0x40C430` entry to `0x40C390` (skip frustum test)
Full findings in `patches/TombRaiderLegend/findings.md` (section "Draw Count Bottleneck Analysis").

## Current Proxy State
- SHORT4 -> FLOAT3 position expansion: WORKING
- SHORT2 -> FLOAT2 texcoord expansion (1/4096 scale): WORKING
- World matrix decomposition from WVP: WORKING
- 28+ culling patches: ALL APPLIED
- Draw cache anti-culling: ACTIVE (replays 3 culled draws)
- Textures: WORKING
- Lights: HASHES UPDATED, NOT YET TESTED
- `useVertexCapture = False`, `antiCulling = disabled`

## Key Files
- `patches/TombRaiderLegend/proxy/d3d9_device.c` — the proxy (all changes here)
- `patches/TombRaiderLegend/findings.md` — accumulated reverse engineering findings
- `patches/TombRaiderLegend/kb.h` — knowledge base with function/struct definitions
- `C:\Users\skurtyy\Desktop\pee\mod.usda` — Remix mod with light definitions (UPDATED THIS SESSION)
- `Tomb Raider Legend/rtx.conf` — Remix config (has `captureShowMenuOnHotkey = False`)
- `Tomb Raider Legend/.trex/bridge.conf` — Bridge config (has `keyboardPolicy = 3`)

## Remix Capture Procedure (for future hash updates)
1. Set `rtx.enableReplacementAssets = False` in BOTH `rtx.conf` AND `user.conf`
2. Launch game, get to Peru, skip cutscene
3. Press `Ctrl+Shift+Q` to capture (works because `captureShowMenuOnHotkey = False` and `keyboardPolicy = 3`)
4. Restore `enableReplacementAssets = True` in both files
5. Parse `Tomb Raider Legend/rtx-remix/captures/capture_<timestamp>.usd` with `pxr` module
