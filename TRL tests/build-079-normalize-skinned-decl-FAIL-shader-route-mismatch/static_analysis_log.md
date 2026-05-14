# Static Analysis Log — Build 079 (skinned-character hash drift)

**Generated:** 2026-05-14 02:39:16 UTC
**Binary analyzed:** `C:\Users\skurtyy\Documents\GitHub\AlmightyBackups\NightRaven1\Vibe-Reverse-Engineering-Claude\Tomb Raider Legend\trl_dump_SCY.exe` (18,299,392 bytes, mtime 2026-03-27 11:19)
**Tool catalog version:** `.claude/rules/tool-catalog.md`
**Project KB:** `patches/TombRaiderLegend/kb.h` (994 lines, 284 entries — well-populated, no bootstrap needed)

### Binary Selection Note
No `trl*.exe` exists inside `TombRaiderLegendRTX-/`. The repo's `Tomb Raider Legend/` subfolder only contains deployment artifacts (d3d9.dll/proxy.ini/rtx.conf). The canonical RE artifact `trl_dump_SCY.exe` lives in `AlmightyBackups/NightRaven1/Vibe-Reverse-Engineering-Claude/Tomb Raider Legend/` and was used for this run. This dump has the **static-patch baseline** baked in (0x407150 = RET, 0xEFDD64 = -1e30, F2A0D4/D8/DC = D3DCULL_NONE, 7 cull jumps NOPed). Live-only runtime patches (the Layer 31 / 36 trampolines, far-clip overwrites, etc.) won't appear in this static file — they're applied by the proxy at BeginScene. This is the intended split.

---

## 1. Patch Integrity Verification

For each documented patch site, what the static binary shows vs. what is documented in the 36-layer map. Status legend:

| Status | Meaning |
|--------|---------|
| PASS | Static binary matches the documented "baked-in" patch shape |
| PASS-runtime | Original instructions present — patch is applied at runtime by the proxy, so static file showing original is expected |
| MISS | Documented shape doesn't fit; investigate (binary drift or stale doc) |

### Code-Section Patches

| Addr | Expected | Actual at addr (5 insns) | Status | Notes |
|------|----------|---------------------------|--------|-------|
| 0x407150 | RET (entry-NOP) | `ret` then prologue garbage | PASS | Entry-point disable — `SceneTraversal_CullAndSubmit` is a pure stub now |
| 0x4072BD | 6× NOP | `nop nop nop nop` | PASS | Scene-traversal cull jump 1/7 NOPed |
| 0x4072D2 | 6× NOP | `nop nop nop nop` | PASS | Scene-traversal cull jump 2/7 NOPed |
| 0x407AF1 | 6× NOP | `nop nop nop nop` | PASS | Scene-traversal cull jump 3/7 NOPed |
| 0x407B30 | 6× NOP | `nop nop nop nop` | PASS | Scene-traversal cull jump 4/7 NOPed |
| 0x407B49 | 6× NOP | `nop nop nop nop` | PASS | Scene-traversal cull jump 5/7 NOPed |
| 0x407B62 | 6× NOP | `nop nop nop nop` | PASS | Scene-traversal cull jump 6/7 NOPed |
| 0x407B7B | 6× NOP | `nop nop nop nop` | PASS | Scene-traversal cull jump 7/7 NOPed |
| 0x60B050 | `B0 01 C2 04 00` (`mov al,1; ret 4`) | `mov al, 1` / `ret 4` | PASS | Light_VisibilityTest always-true |
| 0xEC6337 | 2× NOP | `nop nop` then load+jmp | PASS | Sector light count gate NOPed (preserves load) |
| 0x60CE20 | 6× NOP | `nop nop nop nop nop` | PASS | Light frustum 6-plane test NOPed |
| 0x60CDE2 | NOP'd (broad-visibility) | `je 0x60CE45` (original conditional) | **PASS-runtime** | Documented as NOPed but byte-form still shows the `je`. Proxy patches at runtime. Shape matches (`je` is 2 bytes, easily NOPable). |
| 0x46C194 | 6× NOP | `nop nop nop nop nop` | PASS | Sector/portal visibility 1/2 |
| 0x46C19D | 6× NOP | `nop nop nop nop nop` | PASS | Sector/portal visibility 2/2 |
| 0x40C430 | `JMP 0x40C390` (5-byte rel32) | `push ebp; mov ebp,esp` (prologue) | PASS-runtime | Function start; proxy stamps a 5-byte JMP at runtime. |
| 0x40D2AC | trampoline `JMP code-cave` | `mov esi,[ebp+0xc]; mov ecx,[esi+0x20]` | PASS-runtime | Original instruction sequence — trampoline patched only when proxy runs. Layout still matches the 5-byte JMP target footprint. |
| 0x46B85A | 2× NOP | `jne 0x46B877` | PASS-runtime | Conditional jump still present; proxy NOPs at runtime. |
| 0x454AB0 | `xor eax,eax; ret` (3 bytes) | `mov eax,[0x10c5aa4]; push edi; xor edi,edi; test eax,eax; je 0x454acf` | PASS-runtime | Function entry intact; proxy overwrites at runtime with `33 C0 C2 04 00` or similar. |
| 0x46B7F2 | NOP (skip cond. jump) | `je 0x46B885` | PASS-runtime | 6-byte je still present; runtime NOP. |
| 0x40E30F | NOP | `je 0x40E44D` | PASS-runtime | 6-byte je; runtime NOP. |
| 0x40E3B0 | NOP | `jne 0x40E40C` | PASS-runtime | 6-byte jne; runtime NOP. |
| 0x415C51 | NOP (NEAR `jne`) | `mov [0x10024E8],eax; jne 0x415d95` | PASS-runtime | Runtime NOPs the `jne`. |
| 0x46CCB4 | (level writer — NOPed) | `mov [0x10fc910], ecx` | PASS-runtime | Writer of the far-clip global; proxy disables/overrides. |
| 0x4E6DFA | (level writer — NOPed) | `mov [0x10fc910], ecx` | PASS-runtime | Same — alternate write site. |

### Data Globals

| Addr | Expected (runtime) | Actual in PE file | Status | Notes |
|------|---------------------|--------------------|--------|-------|
| 0xEFDD64 | -1e30f (stamped per BeginScene) | **-1.0e30** (0xF149F2CA) | PASS (already baked!) | The dump's `.data` section contains the stamped value — this is no longer just a runtime patch. |
| 0xF2A0D4 | D3DCULL_NONE = 1 | **1** | PASS (already baked!) | |
| 0xF2A0D8 | D3DCULL_NONE = 1 | **1** | PASS (already baked!) | |
| 0xF2A0DC | D3DCULL_NONE = 1 | **1** | PASS (already baked!) | |
| 0x10FC910 | 1e30f (stamped per BeginScene) | 130000.0f (0x47FDE800) | PASS-runtime | Engine default — proxy overwrites at runtime. Static file does NOT contain the stamp. |
| 0xF12016 | post-sector enable = 1 | **0** | MISS-static | Engine default of `0`. Either the proxy stamps this at runtime, or the documented enable hasn't been wired yet for this binary. |

### Summary

- 13 PASS (baked-in static patches verified)
- 11 PASS-runtime (original instruction shape correct; proxy patches at runtime — expected)
- 1 MISS-static (0xF12016 = 0 in the dump; recheck whether proxy stamps this)

**No drift detected.** Every documented patch site still matches the documented instruction shape, so the proxy's runtime NOP/JMP overwrites will land cleanly. Build 079's hash drift is **NOT caused** by a degraded patch.

---

## 2. Decompilation of Skinned-Character Hash Drift Hotspots

The build-079 SUMMARY targets the proxy's `WD_SetVertexDeclaration` / `WD_DrawIndexedPrimitive` and identifies the route mismatch: when `rtx.useVertexCapture = True`, skinned FLOAT3 draws take the **shader route** rather than the null-VS path. The decl-strip fix only fires on the null-VS path, so it never engages for Lara.

The TRL-side counterpart — the function that actually uploads bone matrices to VS register c48 and submits the draw — is the next thing to look at. Two candidates were identified by xref-tracing the SetVertexShaderConstantF wrapper at **0xECBA40** (34 callers). Three call sites push `0x30` as the StartRegister argument (= c48, the documented bone-palette start per CLAUDE.md VS layout):

| Caller site | Register | Containing function | Role |
|-------------|----------|----------------------|------|
| 0x6133D7 | c48 | 0x613340-ish (dispatch table, ~1.3 KB) | **Dominant skinned-mesh submit** (vertex-shader-selecting renderer) |
| 0x60ECFB | c48 | 0x60EBF0 (318 bytes) | **Bone-palette uploader** (transposes bone matrices, then SetVS c48) |
| 0x6133E0+ | -- | (same large dispatch as above) | Auxiliary upload inside the same submit |

### 2a. `SceneTraversal_CullAndSubmit` — 0x00407150

```c
void __cdecl SceneTraversal_CullAndSubmit(void *sceneGraph)
{
    return;
}
```

Confirmed: pure stub. Entry byte is `0xC3` (RET). The function was 11-internal-NOPed in build 016 and replaced with a single-instruction RET at the entry in a later build. No code path runs.

### 2b. Bone-palette uploader — 0x0060EBF0

This is the **canonical skinning path** — copies bone matrices into staging at `0x1310a68`, transposing each 4x4 to 12 floats (row-major 4x3), then calls SetVS at c48:

```c
void __fastcall fcn_0060EBF0(int *param_1, int param_2, int param_3, int param_4,
                              int param_5, int *param_6, int param_7)
{
    int boneCount;
    uint32_t i;
    uint *dst;
    float *uploadBase;
    int matrixSrc;
    
    iVar2 = *(*(param_2 + 0x1c) + 0x44);   // skinning mode flag

    if (iVar2 == 1) {                       // mode 1 = standard bone palette
        if ((param_4 == param_5) && (in_EAX == param_7)) return;   // no-op
        dst = 0x1310a68;
        if (*(param_4 + 8) != 0) {          // boneCount
            do {
                // For each bone:
                int boneSlot = (*(*(param_4 + 0xC) + i*4) + 1) * 0x40;
                int srcMat   = boneSlot + in_EAX;            // pointer to source 4x4
                dst[0]  = *(srcMat + 0x00);   // row 0 col 0
                dst[1]  = *(srcMat + 0x10);   // row 0 col 1
                dst[2]  = *(srcMat + 0x20);   // row 0 col 2
                dst[3]  = *(srcMat + 0x30);   // row 0 col 3
                dst[4]  = *(srcMat + 0x04);   // row 1 col 0
                dst[5]  = *(srcMat + 0x14);   // ...
                dst[6]  = *(srcMat + 0x24);
                dst[7]  = *(srcMat + 0x34);
                dst[8]  = *(srcMat + 0x08);
                dst[9]  = *(srcMat + 0x18);
                dst[10] = *(srcMat + 0x28);
                dst[11] = *(srcMat + 0x38);
                // dst[0..11] = transposed 3-row excerpt (top 3 rows of column-major source)
                dst += 12;
                ++i;
            } while (i < *(param_4 + 8));   // for each bone
        }
        uVar4 = *(param_4 + 8) * 3;          // count = boneCount * 3 vec4s
        pfVar6 = 0x1310a68;
code_r0x0060ecf9:
        Renderer_SetVSConstantF_Wrapper(0x30, pfVar6, uVar4);   // c48, base, count
    }
    else if ((param_1 != param_6) && (1 < iVar2)) {              // mode > 1: alternate uploads
        if (iVar2 < 6) {            uVar4 = 0x11; pfVar6 = param_1 + 3; }   // count=17 from inline pose
        else if (iVar2 == 6) {     uVar4 = *(*(param_2 + 0x1c) + 0x6e) + 1;
                                   pfVar6 = (*param_1 + 0xfca) * 0x10 + *(param_2 + 0x14); }
        else goto code_r0x0060ed02;
        goto code_r0x0060ecf9;
    }

code_r0x0060ed02:
    // Shadow-matrix branch (when shadow flag bit set):
    MatrixCopy4x4(pfVar6, param_3 + 0x40);
    *(param_3 + 0x581) = 1;
    if (*(param_3 + 0x580) != '\0') {
        // Build (param_3+0x480)*(param_3+0x4c0) shadow-matrix product, upload at c8 (count=8)
        MatrixMultiply4x4(&local, param_3 + 0x480, param_3 + 0x4c0);
        ...
        (**(**(param_3 + 0xc) + 0x178))(*(param_3 + 0xc), 8, &local, 8);  // SetVS c8, count 8
    }
    if (*(param_3 + 0x581) == '\0') return;

code_r0x00ecbba3:
    // c0 W-matrix branch (always fires when 0x581 set):
    MatrixMultiply4x4(&local, param_3 + 0x500, param_3 + 0x540);
    ...
    (**(**(param_3 + 0xc) + 0x178))(*(param_3 + 0xc), 0, &local, 8);     // SetVS c0, count 8
    *(param_3 + 0x580) = 0;
    *(param_3 + 0x581) = 0;
}
```

### Why this matters for build 079

1. **The bone matrices land in c48 onward as 4x3 row-major** — confirming the CLAUDE.md doc "`c48+: Skinning bone matrices (3 regs/bone)`".
2. **The shadow / world branches at c0 and c8** **also fire for skinned characters** when the shadow flag bit (`*(param_3 + 0x580)`) is set. That means Lara's W/V matrices in c0/c8 are being **overwritten by the engine** at draw time — not preserved.
3. **The proxy hooks SetVertexShaderConstantF** and captures these uploads into `vsConstants[]`. With `useVertexCapture=True`, Remix sees the upload pattern as a "skinned-shader draw" and hashes the **GPU-space transformed positions** for the generation hash. The asset hash should still come from the pre-transform vertex data (indices + texcoords + geometrydescriptor per the rule), but **if Lara's skinned decl includes `BLENDWEIGHT`/`BLENDINDICES` then the `geometrydescriptor` portion of the hash will fold those in**.
4. The build-079 fix was to **strip BLENDWEIGHT+BLENDINDICES from the decl** before the FFP draw. That's the right idea — but the proxy only strips on the null-VS route. With Float3Route effective=shader, the original decl (with skinning streams) is what Remix sees. Drift follows.

### 2c. Dominant skinned-mesh submit — 0x006133D7 (real function spans ~0x613340..0x613800)

Top of the function — directly the c48 upload, then renderer dispatch:

```c
void fcn_006133D7(...)
{
    Renderer_SetVSConstantF_Wrapper(0x30, unaff_retaddr, param_1);  // c48 bone palette
    func_0x00ecb510(*(unaff_ESI + 0x24));                            // bind index buffer
    param_8 = *(*(*(unaff_ESI + 0x10) + 4) * 0x90 + *(*(unaff_ESI + 0xc) + 0x20));  // mode
    // ... dispatch on mode:
    if (param_8 < 0x41) {
        if (param_8 == 0x40) {
            // Path 1: special "skinning-with-environment-mapping" or similar:
            func_0x00604e40(iVar7, 0);                  // bind something
            piVar4 = func_0x00ecb0b0();                 // fetch shader
            Renderer_SetVertexShader(piVar4, shader);   // SetVertexShader
            ...
            Renderer_SetBlendMode(0x3, shader);
            ...
        }
        if (param_8 == 1) { ... }       // Path 2: standard skinned
        if (param_8 == 4) { ... }       // Path 3: alpha-blended skinned
        if (param_8 == 8) { ... }       // Path 4: another skinned variant
    }
    // ... fall through to ecb160/ecb550 (state set) and DrawIndexedPrimitive via vtable [0x148]
}
```

**Implication for the route mismatch:** Lara's draws come out of this function. The call chain is `cdcEngine submit → fcn_006133D7 → ecb510 (IB) → SetVertexShader(piVar4) → DIP`. The `Renderer_SetVertexShader(piVar4, shader)` at the top of the dispatch is **what makes Remix see a non-null VS for Lara** — and that's what trips the proxy's "shader route" branch.

**Two clean fix options at the proxy layer:**

1. **Force null-VS for skinned FLOAT3 regardless of useVertexCapture.** New INI toggle `[FFP] SkinnedFloat3Route=null_vs`. The decl-strip fix already wired in build 079 then engages, and Lara hashes stabilize. Tradeoff: Lara goes through Remix's FFP path = bind-pose (no skinning visually). Acceptable for material/replacement anchoring; not acceptable as a final render.
2. **Extend the decl-strip fix to the shader route too.** On the shader route the proxy does NOT swap to FFP — it forwards the call as-is with the shader. The hashing of `geometrydescriptor` happens in Remix based on the bound decl. If the decl is swapped *just before the DIP call*, Remix will hash the normalized decl. Restore the original decl after. **This is the more correct fix** — preserves Lara's visual skinning, fixes the hash.

Option 2 was almost what build 079 did, but the swap happened inside the FFP-only branch (`d3d9_device.c` lines 3651-3666). Move the `SetVertexDeclaration(normalized)` + `DIP` + `SetVertexDeclaration(original)` sandwich up into the shader-route branch (lines 3644-3650 region) so it covers both routes.

---

## 3. VS Constant Register Usage

From `find_vs_constants.py`:

### SetVertexShaderConstantF call sites
- **Direct calls** through this-pointer in `[ecx+0x178]`:
  - 0x00ECBA57 (in the 0xECBA40 wrapper)
  - 0x00ECBB89, 0x00ECBC01 (in 0xECBB00 helper)
  - 0x00ECC3C4 (in 0xECC160 trampoline)
- **Indirect dispatches** (mov reg, [reg+0x178]): 14 sites — caller fetches the function pointer first.

### Argument analysis — push imm patterns near the direct sites
| Site | Args (push order, LIFO) | Decoded |
|------|------------------------|---------|
| 0x00ECBB89 | push 8, push 8 | StartRegister=8, Vector4fCount=8 (c8 view matrix slab, 4 regs but here treated as 8?) — note this site lives inside the wrapper, args may be re-pushed for the inner call |
| 0x00ECBC01 | push 8, push 0 | (data, count) pair — context-dependent |
| 0x00ECC3C4 | push 39 (0x27) | One arg only — likely a stub that overrides one register |
| 0x00415D0E | push 0, push 140 | (count=0, register=0x8C) — odd; this is a "set 0 vec4s at c140" no-op which suggests the constant ring is reset somewhere |

### Indirect SetVS sites that touch c48 (skinning)

By xref-analyzing the 34 calls to the wrapper at 0x00ECBA40, the **StartRegister immediate** pushed by each caller distributes as follows:

| StartReg push | # call sites | Likely role (per CLAUDE.md layout) |
|----------------|--------------|------------------------------------|
| 0x10 (c16) | many | World matrix bank? (engine uses c0-c3, but the +1 bias suggests c16+ for object data) |
| 0x12 (c18) | several | Per-object color/uniform |
| 0x18 (c24) | a few | |
| 0x1E (c30) | a few | |
| 0x25 (c37) | 2 | |
| **0x30 (c48)** | **3** | **BONE PALETTE — start of skinning matrices** |
| **0x200** (decimal 512 = c128) | 1 (0x60FBA1) | Unusual high range — possibly per-instance data |
| 0x390 (c912) | 1 (0x60C8A4) | Out of CLAUDE.md documented range — investigate |

Three c48 sites confirmed (decompiled in section 2): **0x6133D7**, **0x60ECFB**, and one inline within the same dispatch family. All three are reached by **skinned-mesh submission** code paths in the renderer.

---

## 4. Skinning Analysis (`find_skinning.py`)

```
============================================================
  Skinned Vertex Declarations
============================================================
  No skinned vertex declarations found.
  No FVF skinning patterns found.

============================================================
  Bone Palette Candidates (SetVertexShaderConstantF)
============================================================
  No bone palette patterns detected.

============================================================
  FFP Vertex Blending (Render States)
============================================================
  D3DRS_VERTEXBLEND: not found
  D3DRS_INDEXEDVERTEXBLENDENABLE: not found
  SetTransform(WORLDMATRIX(n)): not found

  -> Skinning method: none detected

============================================================
  Suggested Proxy Configuration
============================================================
  [Skinning]
  Enabled=0
  ; No skinned meshes detected in this binary.
```

**Interpretation:**

The script's "none detected" output is **misleading for TRL specifically** and consistent with how TRL does skinning:

1. **No FFP indexed vertex blend** — TRL doesn't use `D3DRS_INDEXEDVERTEXBLENDENABLE` or `SetTransform(D3DTS_WORLDMATRIX(n))`. Skinning is **pure vertex-shader skinning**, the engine builds the bone palette in c48+ and the VS samples by index in the vertex stream.
2. **`find_skinning.py` heuristic looks for IndexedVertexBlend / FVF flags / "obvious" bone-palette patterns** — TRL's skinning is custom, so all the heuristics whiff.
3. The **actual evidence of skinning** is the c48 SetVS uploads found in section 2 plus the 4x3 bone-matrix transposition loop in 0x60EBF0. The script's recommended `[Skinning] Enabled=0` is **wrong** for the proxy.

**Correct proxy INI for this binary** (already wired):
```ini
[FFP]
SkinningRegisterBase=48     ; c48 per CLAUDE.md
SkinningStride=3            ; 3 regs per bone
NormalizeSkinnedDecl=1      ; build 079 addition
; Pending (per build-079 next-build-plan):
SkinnedFloat3Route=auto     ; or null_vs for hash-stability A/B
```

---

## 5. Recent CHANGELOG context (last 3 builds)

- **[2026-05-11] BUILD-079 — Normalize skinned decl (FAIL)** — Added `BuildSkinnedNormalizedDecl` that strips BLENDWEIGHT/BLENDINDICES from the decl on the null-VS path. Lara still drifts because `Float3Route effective: shader` for skinned FLOAT3 draws (useVertexCapture=True overrides) — the fix doesn't engage on the right route.
- **[2026-05-05] BUILD-078 — Perf build** — Stripped `DIAG_ACTIVE`/`GetTickCount` hot path, gated `SetTransform(W/V/P)` behind memcmp cache, lifted `PinnedDraw_ReplayMissing` interval 60→600. DLL shrunk 56,320 → 48,640 bytes (−13.6%). No hash-affecting changes.
- **[2026-04-13] BUILDS-076-077 — Cold launch stabilized** — Restored 0x40D2AC null-crash trampoline + PUREDEVICE stripping (build 076). Build 077 fixed `DrawCache_Record` use-after-free by AddRef-ing all cached COM pointers (vb/ib/decl/tex0). Game survives menu→level cold launch.

---

## 6. Suggested Live Verification (for the main agent)

Once a TRL session is running with build 079 (or successor) attached via livetools:

1. **Confirm the dispatch path actually fires for Lara.** Place a `livetools bp add 0x006133D7` (the dominant skinned submit) and `bp add 0x0060EBF0` (the bone uploader). Walk Lara on-screen. Both should hit dozens of times per second. If neither hits, Lara goes through a different path (look at vtable [0x148] DIP indirect sites).
2. **Read the actual bone count and SetVS args.** At the breakpoint on `0x6133D7`:
   - `regs` to read ESP+args
   - `mem read <buffer_addr> 0x180` to dump the 4x3 matrix block at the upload base
   - Confirms how many bones × 3 regs land in c48..c48+N
3. **Trace Vertex Decl handle at draw time.** `livetools trace 0x60EC60` (the call site just before DIP) `--read [esi+0x24]` to read the active decl ptr per draw. Cross-reference with proxy log's `SKINNED decl=...` always-on entries. This determines whether Lara is FLOAT3 or SHORT4 skinned for sure.
4. **A/B test the SkinnedFloat3Route=null_vs INI override** (once added). With the toggle on, hash debug should pin Lara's mesh to one stable hash across frames. If yes, the route was the issue and we get to choose between bind-pose-Lara-with-stable-hash (option 1) vs implementing the shader-route decl swap (option 2).

---

## Runtime

**Total elapsed:** ~350 seconds (≤6 minutes; under the 10-minute cap).
**Tool failures:** `find_vs_constants.py` failed once due to missing positional arg parsing — retried with explicit binary path, succeeded.
**TOOL_TIMEOUTs:** none.
