/*
 * Knowledge Base -- Tomb Raider Legend (trl.exe)
 * D3D8 game using dxwrapper (D3d8to9=1) to convert to D3D9
 * Shaders compiled with "D3DX9 Shader Compiler 5.04.00.2904"
 */

// ============================================================
// D3D9 vtable offsets used by the engine
// ============================================================
// 0x0E4 = SetRenderState          (method 57)
// 0x104 = SetTextureStageState    (method 65)
// 0x10C = SetSamplerState         (method 67)
// 0x114 = SetTexture              (method 69) -- actually CreateStateBlock area? double check
// 0x164 = SetFVF                  (method 89)
// 0x170 = SetVertexShader         (method 92)
// 0x178 = SetVertexShaderConstantF (method 94)
// 0x1AC = SetPixelShader          (method 107)

// ============================================================
// VS Constant Register Layout
// ============================================================
// c0-c3   (reg 0,  cnt 4): WorldViewProjection matrix (transposed, row0-row3)
//                            OR first 4 rows of combined 8-register upload
// c4-c7   (reg 4,  cnt 4): Fog / lighting parameters
// c6      (reg 6,  cnt 1): Fog distance {0, 0, fogEnd, epsilon} (standalone upload)
// c8-c11  (reg 8,  cnt 4): View matrix (transposed, from this+0x480 * this+0x4C0)
//                            First half of 8-register batch upload
// c12-c15 (reg 12, cnt 4): Projection-related (second half of 8-register batch)
//                            From this+0x500 copy
// c16+    (reg 16, cnt N): Per-object bone/skin matrices (variable count = bones*2)
// c17     (reg 17, cnt 1): Single per-draw constant
// c18     (reg 18, cnt 1): Ambient / material color
// c19     (reg 19, cnt 1): Light direction / color
// c21     (reg 21, cnt 1): Object-space camera or object data
// c22-c23 (reg 22, cnt 2): Normal map / additional lighting data
// c24-c27 (reg 24, cnt 4): Texture transform / UV animation matrix
// c28     (reg 28, cnt 1): Per-object parameter
// c30     (reg 30, cnt 1): Screen / viewport params (zNear, zFar related)
// c37     (reg 37, cnt 1): Light-related parameter {value, 0, 0, 0}
// c38     (reg 38, cnt 1): Scale / bias constant
// c39     (reg 39, cnt 1): Utility constants {2.0, 0.5, 0.0, 1.0} (set once at init)
// c40-c41 (reg 40, cnt 2): Camera position / parameters
// c44     (reg 44, cnt 1): Camera direction {x, y, z, 0.5}
// c48+    (reg 48, cnt N): Skinning / bone matrices (alternative slot, variable count)
// c96     (reg 96, cnt 1): Far clip / depth bias parameters

// ============================================================
// Renderer object layout (at offset from 'this')
// ============================================================
struct TRLRenderer {
    // ... (partial)
    void* vtable;                   // +0x00
    int pad1[2];                    // +0x04, +0x08
    IDirect3DDevice9* pDevice;      // +0x0C  *** D3D device — accessed as *(g_pEngineRoot+0x214)+0x0C
    int field_10;                   // +0x10
    int field_14;                   // +0x14
    // ...
    int field_68;                   // +0x68  current vertex shader
    // ...
    // render state cache starts around +0xEC
    int renderStateCache[0xD2];     // +0xEC .. ~+0x43C (0xD2 entries, initialized to -1)
    int field_460;                  // +0x460  = 10 (blend mode count?)
    int field_464;                  // +0x464  flags (bit 6 = 0x40 disables cull mode change)
    int field_468;                  // +0x468
    int field_46C;                  // +0x46C
    int blendMode;                  // +0x470  current blend mode (switch in ECBC20)
    int cullModeGlobalPtr;          // +0x474  last value written from g_cullMode_pass1/pass2
    // padding to +0x480
    float viewMatrix1[16];          // +0x480  first view-related matrix (input A to MatrixMultiply)
    float viewMatrix2[16];          // +0x4C0  second view-related matrix (input B to MatrixMultiply)
    float projMatrix1[16];          // +0x500  first projection-related matrix (input A)
    float projMatrix2[16];          // +0x540  second projection-related matrix (input B)
    char viewDirty;                 // +0x580  flag: view matrices need re-upload to c8-c15
    char projDirty;                 // +0x581  flag: projection matrices need re-upload to c0-c7
    // ...
    int alphaRef;                   // +0x584  alpha reference value for blend modes

    // D3D render state cache (direct SetRenderState mirrors, checked before issuing call)
    // Offset = 0xEC + (stateEnum - base) * 4  (approximate — base is ~7)
    int cached_ZFUNC;               // +0x148  D3DRS_ZFUNC (23 = 0x17)  current value
    int cached_CULLMODE;            // +0x144  D3DRS_CULLMODE (22 = 0x16) current value
    int cached_STENCILENABLE;       // +0x1BC  D3DRS_STENCILENABLE (52 = 0x34) current value
    int cached_COLORWRITEENABLE;    // +0x3D0  D3DRS_COLORWRITEENABLE (185 = 0xB9) current value
    int cached_STENCILZFAIL;        // +0x1C4  D3DRS_STENCILZFAIL (54 = 0x36) current value
    int cached_STENCILPASS;         // +0x1C8  D3DRS_STENCILPASS (55 = 0x37) current value
    int cached_STENCILFAIL;         // +0x1CC  D3DRS_STENCILFAIL (56 = 0x38) current value
    int cached_STENCILREF;          // +0x1D4  D3DRS_STENCILREF (58 = 0x3A) current value
    int cached_STENCILMASK;         // +0x1D8  D3DRS_STENCILMASK (59 = 0x3B) current value
};

// ============================================================
// Matrix operation functions
// ============================================================

@ 0x005DD910 void __cdecl MatrixMultiply4x4(float* result, float* matA, float* matB);
@ 0x00402990 void __thiscall MatrixCopy4x4(float* this_dst, float* src);
@ 0x00ECBAA0 void __fastcall MatrixTranspose4x4(float* dst, float* src);

// ============================================================
// Renderer functions
// ============================================================

@ 0x00ECBA40 void __thiscall Renderer_SetVSConstantF(TRLRenderer* this, unsigned short startReg, void* data, unsigned short count);
@ 0x00ECBA60 void __thiscall Renderer_SetVertexShader(TRLRenderer* this, void* shader);
@ 0x00ECBB00 void __fastcall Renderer_UploadViewProjMatrices(TRLRenderer* this);
             //   Uploads: startReg=8, count=8 (c8-c15, viewMatrix1 * viewMatrix2)
             //   Then:    startReg=0, count=8 (c0-c7,  projMatrix1 * projMatrix2)
             //   Guarded by viewDirty (+0x580) and projDirty (+0x581) flags
             //   Call sites: 0x00ECBB89, 0x00ECBC01
@ 0x00413950 void __cdecl cdcRender_SetWorldMatrix(int startReg, float* matrix);
             //   Transposes matrix (game col-major → HLSL row-major) then calls
             //   Renderer_SetVSConstantF(startReg, transposed, 4)
             //   Called by many render-path functions with startReg=0x28 (c40) for secondary
             //   Call site in Renderer_SetVSConstantF wrapper: 0x00ECBA57
@ 0x00ECBC20 void __thiscall Renderer_SetBlendMode(TRLRenderer* this, int mode);
@ 0x00ECC160 void __thiscall Renderer_SetBlendMode_Wrapper(TRLRenderer* this, int mode);
@ 0x00ECC180 uint __fastcall Renderer_Init(TRLRenderer* this);
@ 0x0040E470 void __thiscall Renderer_SetRenderStateCached(TRLRenderer* this, int state, int value);
@ 0x0040EAB0 void __thiscall Renderer_ApplyRenderStateChanges(TRLRenderer* this, uint desiredStates);
@ 0x0040E980 void __cdecl SetTextureStageState_Cached(uint mask);  // uses g_pEngineRoot->[+0x214]->[+0xC] as device
@ 0x004072A0 void FrustumCull_SceneTraversal(int objectList);
@ 0x0060C7D0 void __thiscall RenderLights_FrustumCull(void* this);
             //   Iterates [ebx+0x1B0] lights, calls FUN_0060b050 for broad visibility,
             //   then 6-plane frustum dot-product test per light.
             //   Lights passing all 6 planes: drawn immediately with mode=1 via vtable[0x18].
             //   Lights failing any plane: deferred to array at 0x13107F4/FC, drawn later with mode=0.
             //   CULL JUMP 1: 0x60CDE2 (je +0x61, 2 bytes: 74 61) — skips light if FUN_0060b050 returns 0
             //   CULL JUMP 2: 0x60CE20 (jnp +0x18D, 6 bytes: 0F 8B 8D 01 00 00) — defers light on plane fail
             //   Vtable dispatch: [edx+0x14] = GetBoundingSphere (slot 5), [eax+0x18] = Draw (slot 6)
@ 0x0060E2D0 void __thiscall RenderLights_Caller(void* this);
             //   Outer caller of RenderLights_FrustumCull. Sets up shadow/stencil state.
             //   Checks: [this+0x84] (light data ptr), [scene+0x166] (light enable),
             //   [renderer+0x444]&1 (light capability), [this+0x1B0] (light count).
             //   If light count > 0, calls RenderLights_FrustumCull.
             //   Gate at 0x60E3B1: JE 0x60E4B6 skips if no lights.
             //   Called from 0x603810.
@ 0x0060BCF0 void __thiscall RenderLights_PreSetup(void* this);
             //   Pre-light renderer setup, called before RenderLights_FrustumCull
@ 0x0060E150 void __thiscall RenderLights_ShadowSetup(void* this);
             //   Shadow/stencil setup, called conditionally if shadow flag is set
// ============================================================
// Light object class hierarchy (NO RTTI)
// ============================================================
// LightBase: outer vtable 0xF085D4, inner MI vtable 0xF085E8 at this+8
//   Constructor: 0x60B320, size=0x1D0, field +0x420 = enable flag
// LightGroup (container): vtable 0xF08618, secondary 0xF08614 at this+4
//   Constructor: 0x60C240, inherits from LightBase
//   +0x74 = type, +0x7C = param, +0x1B0 = light count, +0x1B8 = light obj ptr array
// LightVolume (individual light): vtable 0xF08740, secondary 0xF08738 at this+4
//   Constructor: 0x610170, size=0x1F0
//   vtable[5] (+0x14) = GetBoundingSphere (0x612C80)
//   vtable[6] (+0x18) = Draw (0x6124E0)
// SceneLight: vtable 0xF08688, secondary 0xF086A0
//   Set at 0x60F68D
// LightEffect: vtable 0xF087DC
//   Set at 0x611A53, no Draw implementation

@ 0x0060B320 void __thiscall LightBase_Constructor(void* this, void* param1, void* param2);
             //   Sets vtables: [this]=0xF085C0 -> 0xF085D4, [this+8]=0xF085E8
@ 0x0060C240 void __thiscall LightGroup_Constructor(void* this, void* param1, void* param2);
             //   Sets vtables: [this]=0xF085EC -> 0xF08618, [this+4]=0xF08614
@ 0x00610170 void __thiscall LightVolume_Constructor(void* this);
             //   Sets vtables: [this]=0xF08740, [this+4]=0xF08738
@ 0x006124E0 void __thiscall LightVolume_Draw(void* this, void* renderCtx, void* lightParams, int enabled);
             //   The per-light draw function called from RenderLights_FrustumCull vtable[6]
@ 0x00612C80 void* __thiscall LightVolume_GetBoundingSphere(void* this);
             //   Returns bounding sphere for frustum culling, called via vtable[5]

@ 0x0060B050 char __thiscall LightVisibilityCheck(void* this, void* lightData);
             //   Mode-dependent broad visibility check. thiscall with 1 stack arg, ret 4.
             //   Reads mode from [this+0x74]->[+0x448] (3-way switch):
             //   mode 0: calls 0x60AD20 (spotlight path)
             //   mode 1: calls 0x60AC80 + 0x5F9BE0 (pointlight AABB test -- DISTANCE DEPENDENT)
             //   mode 2: calls 0x60AC80 + 0x5F9A60 (directional AABB test)
             //   default (>=3): returns AL=1 (always visible)
             //   CRITICAL: This is the primary culling gate for lights at distance.
             //   Called at 0x60CDDB; result checked at 0x60CDE2 (je skips light if AL=0).
             //   Patch: B0 01 C2 04 00 (mov al,1; ret 4) to force all lights visible.
@ 0x0060AC80 void __thiscall LightVisibility_ComputeAABB(void* this, float radius, float scaling);
             //   Computes AABB for light visibility check (modes 1 and 2)
@ 0x0060AD20 void __thiscall LightVisibility_SpotlightTest(void* this, float param1, float param2);
             //   Spotlight visibility test (mode 0)
@ 0x005F9BE0 char __cdecl AABB_IntersectionTest(void* aabbA, void* aabbB);
             //   AABB intersection test, returns bool. Used by LightVisibilityCheck mode 1.
@ 0x005F9A60 char __cdecl AABB_IntersectionTest_Alt(void* aabbA, void* aabbB);
             //   Alternate AABB intersection test. Used by LightVisibilityCheck mode 2.
@ 0x00402DA0 void __cdecl TransformObjectToScreen(void* output, void* input);
@ 0x00406240 void __cdecl SubmitBillboard(void* billboard);
@ 0x00406DA0 void __cdecl SubmitAxisAlignedSprite(float x, float y, float w, float h, float z, int color);
@ 0x00406ED0 void __cdecl SubmitRotatedSprite(float x, float y, float w, float h, float z, int color);
@ 0x00406EF0 void __cdecl FrustumCull_ExpandBounds(void* bounds);
@ 0x00ECB900 void __thiscall Renderer_SetSamplerState(TRLRenderer* this, int sampler, int value);

// ============================================================
// Scene traversal / visibility pipeline
// ============================================================

// Scene node linked-list element (EBX in SceneTraversal_CullAndSubmit)
struct SceneNode {
    void* vtable_or_type;       // +0x00
    SceneNode* next;            // +0x04  linked list next pointer
    uint32_t flags;             // +0x08  bit 4=skip, bit 10=alt path, bit 7=negative sign check
    uint16_t meshId;            // +0x0C  mesh/object ID passed to submit functions
    float posX;                 // +0x10
    float posY;                 // +0x14
    float posZ;                 // +0x18
    // gap
    uint16_t renderFlags;       // +0x2E  bits: &7=type switch, bit 4=alt submit
    uint8_t extraFlags;         // +0x2F  bit 6=orientation flag
    // gap
    uint32_t sortKey;           // +0x3C  stored/restored across iterations
    // gap
    RenderContext* ctx;          // +0x8C  render/transform context — CAN BE NULL (crash source)
    // gap
    uint8_t lodLevel;           // +0xB7  LOD blend factor
};

// Render context sub-object (at SceneNode +0x8C)
struct RenderContext {
    // +0x00 .. +0x0F: unknown
    float matrix[16];           // +0x10  4x4 transform matrix
    float posX;                 // +0x40  copied from SceneNode.posX
    float posY;                 // +0x44  copied from SceneNode.posY
    float posZ;                 // +0x48  copied from SceneNode.posZ
    float posW;                 // +0x4C  always 1.0f (0x3F800000)
};

@ 0x00407150 void __cdecl SceneTraversal_CullAndSubmit(void* sceneGraph);
             //   4049 bytes, traverses two linked lists from sceneGraph:
             //   List 1 ([arg+0x24]): SceneNode chain via +0x04, copies position to RenderContext
             //   List 2 ([arg+0x2C]): second node chain with frustum culling and mesh submission
             //   CRASH BUG: [node+0x8C] (RenderContext*) can be NULL — no null check before
             //   dereferencing at 0x4071E2 (mov [edx+0x40], eax). Nodes with flags bit 4 set
             //   are skipped safely; nodes without the flag but with NULL ctx crash.
             //   RET patch at entry (0xC3) prevents crash and disables all scene culling.
@ 0x00443C20 void __cdecl RenderScene(void* sceneData, void* cameraMatrix);  // calls matrix setup -> scene traversal -> post-process
@ 0x00450B00 void __cdecl RenderFrame(void* frameData);  // mid-level render loop, world object iteration, calls RenderScene
@ 0x00450DE0 void __cdecl RenderFrame_TopLevel(void* context);  // entry point with fade-in/out logic
@ 0x00442D40 void __cdecl RenderScene_PostProcess(void* data);  // called after scene traversal
@ 0x00402B10 void __cdecl CopyMatrixToGlobal(void* srcMatrix);  // copies 4x4 matrix to g_cameraMatrix (0xF3C5C0)
@ 0x00407010 void __fastcall ComputeProjectedSize(void* sizeParams);  // computes screen-space projection, clamps to bounds
@ 0x00446580 uint __cdecl LOD_AlphaBlend(uint baseColor, uint lodDistance);  // LOD fade: returns ARGB with alpha based on distance. esi=blend factor (0-0x1000)
@ 0x00406640 void __cdecl SubmitMesh_WithFlags(int flags, int meshData, void* bounds, int lodColor);  // mesh submission with oriented bounds
@ 0x00604BE0 void __cdecl SubmitMesh_Generic(int flags, int meshData, void* bounds, int count);  // generic mesh submission

// ============================================================
// Globals
// ============================================================

$ 0x01392E18 void* g_pEngineRoot       // pointer to engine base object
                                       // g_pEngineRoot + 0x000 = vtable
                                       // g_pEngineRoot + 0x00C = ref count (decremented by FUN_00ec72d0)
                                       // g_pEngineRoot + 0x020 = pointer to draw submitter object
                                       // g_pEngineRoot + 0x214 = pointer to TRLRenderer
$ 0x00F2A0D4 int g_cullMode_pass1      // D3DRS_CULLMODE value for first render pass (opaque)
                                       // 1=D3DCULL_NONE, 2=D3DCULL_CW, 3=D3DCULL_CCW
                                       // To disable all culling: write 1 here and to g_cullMode_pass2
$ 0x00F2A0D8 int g_cullMode_pass2      // D3DRS_CULLMODE value for second render pass (transparent/stencil)
$ 0x00EFDD64 float g_frustumDistanceThreshold  // = 16.0f, .rdata, used at 0x407162 for initial scale (16.0 * 1/512)
$ 0x00EFD404 float g_screenBoundsMin           // = -1.0, NDC left/bottom cull boundary
$ 0x00EFD40C float g_screenBoundsMax           // = 1.0, NDC right/top cull boundary
$ 0x010FC910 float g_farClipDistance            // far clip plane distance, varies per level
$ 0x00EFDD60 float g_smallObjectThreshold      // = 0.00390625 (1/256), min screen-space size before clamp
$ 0x00EFDD4C float g_lodFadeDistance           // = 5000.0, used for LOD fade offset
$ 0x00EFD8E4 float g_sceneScaleFactor          // = 0.001953 (1/512), multiplied with g_frustumDistanceThreshold
$ 0x00F11D0C float g_viewDistance              // = 512.0, base view distance
$ 0x00F0ECFC float g_zeroConstant              // = 0.0, comparison constant
$ 0x00F3C5C0 float[16] g_cameraMatrix          // current camera/view matrix (copied by 0x402B10)
$ 0x00F127E0 uint g_cachedTextureStageStateMask
$ 0x00F127E4 uint g_lastTextureStageStateMask
$ 0x00FFA720 uint g_currentDesiredRenderStates  // bitfield: bit21=cullmode, bit20=zwrite, bit12=alphatest, etc.
$ 0x013107F4 int g_deferredLightCount         // count of lights deferred by frustum cull
$ 0x013107F8 int g_deferredLightCapacity      // capacity of deferred light array
$ 0x013107FC int* g_deferredLightIndices      // pointer to array of deferred light indices
$ 0x01310800 int g_deferredLightInitFlag       // bit 0: set once during first RenderLights call
$ 0x010E537C void* g_pCurrentScene             // current scene/level object pointer
$ 0x010E5380 void* g_pPostProcessData          // passed to RenderScene_PostProcess
$ 0x01089E40 void* g_pSpecialRenderCallback1   // if non-null, calls 0x446920 after scene
$ 0x01089E44 void* g_pSpecialRenderCallback2   // if non-null, calls 0x4495C0 after scene

// ============================================================
// Sector/Portal Visibility System
// ============================================================

// Sector table: 8 entries of 0x5C bytes at fixed address
// Per entry: [+0]=sectorIndex(dword), [+4]=type(byte, 2=active), [+5]=flags(byte, bit3=visible)
// [+0x37..0x3D]=bounding box (4 shorts: x,y,w,h), [+0x3F]=sectorType(dword, 1=standard, 2=fullscreen)
$ 0x011582F8 char[0x2E0] g_sectorTable       // 8 sector entries, 0x5C bytes each
$ 0x010C5AA4 void* g_pObjectListHead          // head of active scene object linked list (next at +8)
$ 0x010E5384 uint32 g_renderFlags             // bit 20 = skip entire object loop rendering
$ 0x010E5438 void* g_pCameraSectorData        // current camera sector data (from GetCameraSector)
$ 0x010FCAE8 void* g_pPlayerCamera            // player/camera struct (sector index at +0xB2)
$ 0x010E5458 int g_fallbackSectorIndex        // fallback sector index when primary lookup fails
$ 0x010FC900 float[4] g_sectorScissorRect     // current sector viewport scissor (x_min, x_max, y_min, y_max)
$ 0x010FC920 float g_sectorMinWidth           // minimum sector width threshold for rendering
$ 0x010FC924 float g_sectorMinHeight          // minimum sector height threshold for rendering
$ 0x010E579C void* g_pCameraOverrideObj       // camera override object (vtable[0x28] = GetSectorIndex)
$ 0x00FFA718 uint32 g_postSectorVisibilityMask  // bitmask: bit N = post-sector object N is visible
$ 0x00F17904 byte g_sectorBypassFlag           // if set, 0x5C3C50 called instead of RenderVisibleSectors
$ 0x010E5424 int g_frameCounter                // incremented each RenderFrame call
$ 0x01117560 void* g_pCutsceneObject           // if non-null, calls 0x44B7A0 for cutscene rendering
$ 0x0010024E8 int g_postSectorLoopDisable      // if non-zero, post-sector object loop at 0x40E2C0 is skipped
$ 0x00EFDE58 float g_maxObjectDrawDistance     // max draw distance for post-sector objects
$ 0x00EFDDB0 float g_nearLODThreshold         // near LOD threshold for post-sector objects
$ 0x00EFDE50 float g_farLODThreshold          // far LOD threshold for post-sector objects
$ 0x00F12016 byte g_postSectorLoopEnable       // if 0, entire post-sector object loop at 0x40E2C0 is skipped
$ 0x011397C0 void* g_pSectorDataBase           // base of sector data structure
             //   +0x3854: sector command buffer start (scanned by 0x5BE540)
             //   +0x33D8: 0x47C-byte per-sector visibility bitfield (checked by 0x5BE7B0)
$ 0x011397CC void* g_pSectorCommandBufferEnd   // end pointer for sector command buffer scan

@ 0x0046C180 void __cdecl SectorVisibility_RenderVisibleSectors(void* sceneData);
             //   Iterates g_sectorTable[0..7]. Per sector: checks [+5]&8 (visible flag) and [+4]==0 (enabled).
             //   Sectors failing = SKIPPED. Type 1 sectors render via Sector_RenderMeshes (0x46B7D0),
             //   type 2 via Sector_RenderFullscreen (0x46B890).
             //   CULL GATE 1: je at 0x46C194 (6 bytes) -- skips if visibility flag not set
             //   CULL GATE 2: jne at 0x46C19D (6 bytes) -- skips if enabled byte != 0
@ 0x0046B7D0 void __cdecl Sector_RenderMeshes(void* sectorData);
             //   Renders meshes in a sector. Checks mesh flags [+0x20]&1 (disabled), &0x20000, &0x200000.
             //   Inner mesh submission via 0x412F20 then 0x458630.
@ 0x0046B890 void __cdecl Sector_RenderFullscreen(void* sectorData);
             //   Alternate sector render for type 2 (fullscreen) sectors.
@ 0x0046C320 void __cdecl Sector_IterateMeshArray(void* meshArray, void* sceneCtx);
             //   Iterates mesh array, checks [mesh+0x5C]&0x82000000 cull flags. Calls 0x458630.
@ 0x0046C4F0 void __cdecl SetupCameraSector(void* sceneData);
             //   Builds camera frustum from camera's current sector. Accesses g_pCurrentScene and g_pPlayerCamera.
@ 0x00450A80 void* __cdecl GetCameraSector(void);
             //   Returns sector data for camera position. Uses g_pCameraOverrideObj vtable[0x28],
             //   or falls back to Sector_FindByIndex via player struct sector index at +0xB2.
@ 0x005D4870 void* __cdecl Sector_FindByIndex(int sectorIndex);
             //   Linear search of g_sectorTable for entry with [+4]==2 (active) and [+0]==sectorIndex.
@ 0x00458630 void __cdecl MeshSubmit(void* meshEntry, short sectorIdx, char forceVisible);
             //   Per-mesh draw submission. Calls MeshSubmit_VisibilityCheck (0x454AB0) first.
             //   If that returns nonzero and forceVisible==0, mesh is skipped.
@ 0x00454AB0 int __cdecl MeshSubmit_VisibilityCheck(void* meshEntry);
             //   Returns nonzero if mesh should be culled (not visible).
@ 0x0040C650 void __cdecl Sector_SubmitObject(void* meshBase, void* objectEntry);
             //   Object submission called from Sector_RenderMeshes (0x46B7D0) after flag filters pass
@ 0x0040D290 void __cdecl PostSector_SubmitObject(void* timestamp, void* lodData, void* sectorBase, int flags, int handle, void* morphData);
             //   Object submission called from post-sector object loop (0x40E2C0)
             //   CRASH BUG: lodData (param2) can be NULL when anti-culling patches force submission.
             //   Crash at 0x40D2AF: mov ecx,[esi+0x20] with esi=NULL. Needs null guard.
@ 0x0040D7E0 void __cdecl PostSector_PrepareObject(void* timestamp, int objIndex, void* arrayBase);
             //   Pre-submission setup in post-sector loop
@ 0x0040DA40 void __cdecl PostSector_FinishObject(void* timestamp, int objIndex, void* arrayBase);
             //   Post-submission cleanup in post-sector loop
@ 0x0040E2C0 void __cdecl PostSector_ObjectLoop(void* objectArray);
             //   Post-sector moveable object iteration loop. Checks bitmask at 0xFFA718,
             //   walks linked list at [entry+0x110] -> [+0x228]/[+0x22C],
             //   filters by flags [+0xA4]&0x800, [+0xA8]&0x10000, distance against 0xEFDE58/0xEFDDB0.
             //   Entries spaced 0x130 bytes. Part of RenderVisibleSectors tail code.
@ 0x00455A50 float __cdecl Object_ComputeDistance(void* obj);
             //   Computes distance from camera to object, used by post-sector distance culling
@ 0x00531B10 int __cdecl Object_HasComponentType(void* obj, short typeId);
             //   Checks [obj+0x1C0] for magic 0xB00B at word[+4] and matching typeId at word[+2].

// ============================================================
// Render state bitfield (ebp in ApplyRenderStateChanges)
// ============================================================
// Bit 11 (0x800):      D3DRS_SHADEMODE (8)
// Bit 12 (0x1000):     Alpha test enable/disable (via 0x40EA10)
// Bit 20 (0x100000):   D3DRS_ZWRITEENABLE (28)
// Bit 21 (0x200000):   D3DRS_CULLMODE (22) -- 0=D3DCULL_NONE, 1=D3DCULL_CW
// Bit 22 (0x400000):   Sampler min filter
// Bit 23 (0x800000):   Sampler mag filter
// Bit 29 (0x20000000): D3DRS_DESTBLEND (55)
// Bit 30 (0x40000000): D3DRS_ALPHATESTENABLE (56)
// Bit 31 (0x80000000): D3DRS_FILLMODE (24)

// ============================================================
// LightVolume vtable methods (vtable-dispatched, no direct xrefs)
// ============================================================
@ 0x6124E0 void __thiscall LightVolume_UpdateVisibility(int materialFilter, float alpha);
@ 0x612810 void __thiscall LightVolume_UpdateColors(int materialFilter, uint8_t channelIdx, float* colorRGBA);
@ 0x611EB0 void __thiscall LightVolume_EnsureRenderSlots(void);
@ 0x611990 void __thiscall LightVolume_InitRenderData(void* lightVol);
@ 0x6101C0 void* __cdecl TransientHeap_Alloc(void);
@ 0x600060 void* __thiscall TransientHeap_AllocBlock(int size);
@ 0x5DA0C0 void __cdecl TransientHeap_Panic(const char* msg);

$ 0xEFD40C float g_fOne = 1.0f
$ 0xF0ECFC float g_fZero = 0.0f
$ 0xEFDDD0 const char* g_szOutOfTransientHeap = "Out of transient heap space!"

// ============================================================
// Code caves in .text section (INT3 padding between functions)
// ============================================================
// 0xEDF9E3: 29 bytes CC padding (0xEDF9E3-0xEDF9FF) -- used for null-check trampoline
// 0xEE2602: 30 bytes CC padding (0xEE2602-0xEE261F) -- spare cave

// ============================================================
// Terrain rendering path — PATCHED
// ============================================================
// Separate from SceneTraversal_CullAndSubmit and SectorVisibility paths.
@ 0x0040ACF0 void* __thiscall TerrainDrawable_Ctor(void* this, void* pMeshBlock, void* pTerrainData, void* pFlags, void* pContext);
             //   Constructor for terrain draw descriptor (0x30 bytes at this/esi).
             //   Sets vtables [this]=0xEFDE08, [this+4]=0xF12864.
             //   Copies mesh flags from [pMeshBlock] to [this+0x1C].
@ 0x0040ADF0 void __thiscall TerrainDrawable_Submit(void* this, void* pPrevDrawable);
             //   Dispatch: calls vtable[0] on the allocated batch at [this+0x28].
             //   Increments global draw counter at 0x10024CC.
@ 0x0040AE20 void __thiscall TerrainDrawable_Execute(void* this, int mode, void* pPrevDrawable);
             //   Actual terrain rendering: matrix setup, batch draw, LOD selection.
             //   CULL GATE: 0x40AE3E — 6-byte JNE, skips when flag 0x20000 set AND mode==0x1000.
             //   NULL GATE: 0x40B0F4 — 6-byte JE, skips when [0x1392E18+0x20]==NULL.
             //   Called via vtable (0 direct xrefs). 0x40AE20 is [vtable+0] for terrain objects.
             //   Calls 0x414280 (shader selection), 0xECB0B0 (VB lookup).
             //   Returns descriptor ptr. NO culling jumps — pure setup.
             //   Called from terrain loop at 0x40C0E9 (single call site).
             //   ret 0x10 at 0x40ADED.
@ 0x0040AE20 void __thiscall TerrainDrawable_Dispatch(void* this, int drawMode, void* prevDesc);
             //   Terrain draw dispatch — the actual rendering function.
             //   CULL JUMP 1: 0x40AE3E (jne 0x40B1A6, 6 bytes: 0F 85 62 03 00 00)
             //     Skips draw if drawMode==0x1000 AND [this+0x1C]&0x20000.
             //   NULL CHECK: 0x40B0F4 (je 0x40B1A6, 6 bytes) — DO NOT NOP (crash).
             //   Sets world matrix via FPU 4x4 multiply loop at 0x40AFB0-0x40B06C.
             //   Final draw via 0xEC91B0 or vtable [eax+0x148].
             //   ret 8 at 0x40B1AC.
@ 0x0040ADF0 void __thiscall TerrainDrawable_Submit(void* this, void* meshData);
             //   Small thiscall that calls 0x413D70 -> 0xEC9DC0, then vtable dispatch
             //   [ecx]->[edx] to submit the terrain descriptor. ret 4 at 0x40AE16.
@ 0x00454AB0 int __fastcall MeshSubmit_VisibilityGate(void* meshEntry);
             //   Per-mesh visibility check. ESI = meshEntry on entry.
             //   Walks linked list at g_pObjectListHead (0x10C5AA4), comparing
             //   [node+0x1D0] to mesh sector ID [esi+0x54].
             //   Fallback 1: sub_5BE540 scans sector command buffer.
             //   Fallback 2: sub_5BE7B0 checks per-sector visibility bitfield
             //     at [0x11397C0+0x33D8+idx/8], bit (idx%8).
             //   Returns 1 = CULL (sets [esi+0x5C] |= 0x80000000).
             //   Returns 0 = VISIBLE.
             //   PATCH: 33 C0 C3 at 0x454AB0 (xor eax,eax; ret) forces all visible.
             //   Single caller: MeshSubmit at 0x458641.
@ 0x005BE540 int __cdecl SectorCommandBuffer_Search(int sectorId);
             //   Scans sector command buffer at [0x11397C0+0x3854] for matching
             //   sector ID. Word-aligned entries, type 3 checks word [+0xA],
             //   type 4 checks [+0xC]>>15 & 0x7FFF. Returns nonzero if found.
@ 0x005BE7B0 int __cdecl SectorVisibility_BitfieldCheck(void* meshEntry);
             //   Reads sector index from [obj+0x54], bounds-checks 0..0x3FFF,
             //   tests bit in 0x47C-byte bitfield at [0x11397C0+0x33D8].
             //   Returns 1 if bit SET (sector already rendered = cull to avoid double-draw).
             //   Returns 0 if bit CLEAR (sector unvisited = should draw).
