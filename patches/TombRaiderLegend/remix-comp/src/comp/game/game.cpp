#include "std_include.hpp"
#include "shared/common/flags.hpp"

/*
 * Tomb Raider Legend — game-specific memory patches.
 *
 * TRL has multiple layers of culling that hide geometry from Remix:
 *   1. Per-object frustum/distance culling in SceneTraversal_CullAndSubmit
 *   2. Sector portal visibility (only camera-reachable sectors render)
 *   3. Per-light frustum rejection and distance checks
 *   4. Sector light count clearing per-frame
 *   5. Render flags that skip post-sector object loops
 *
 * All patches disable culling so Remix sees all geometry and lights.
 */

namespace comp::game
{
	// -- Addresses --

	constexpr uintptr_t FRUSTUM_THRESHOLD        = 0x00EFDD64;
	constexpr uintptr_t FAR_CLIP_STAMP           = 0x010FC910;

	constexpr uintptr_t CULL_MODE_PASS1          = 0x00F2A0D4;
	constexpr uintptr_t CULL_MODE_PASS2          = 0x00F2A0D8;
	constexpr uintptr_t CULL_MODE_PASS2_INV      = 0x00F2A0DC;

	constexpr uintptr_t LIGHT_FRUSTUM_REJECT     = 0x0060CE20;
	constexpr uintptr_t LIGHT_VISIBILITY_TEST    = 0x0060B050;
	constexpr uintptr_t SECTOR_LIGHT_GATE        = 0x00EC6337;
	constexpr uintptr_t RENDER_LIGHTS_GATE       = 0x0060E3B1;
	constexpr uintptr_t LIGHT_COUNT_CLEAR        = 0x00603AE6;
	constexpr uintptr_t LIGHT_CULLING_FLAG       = 0x01075BE0;

	constexpr uintptr_t SECTOR_VIS_JE            = 0x0046C194;
	constexpr uintptr_t SECTOR_VIS_JNE           = 0x0046C19D;
	constexpr uintptr_t SECTOR_OBJ_PROXIMITY     = 0x0046B85A;

	constexpr uintptr_t RENDER_FLAGS             = 0x010E5384;

	constexpr uintptr_t NULL_CHECK_SITE          = 0x004071D9;
	constexpr uintptr_t NULL_CHECK_CAVE          = 0x00EDF9E3;
	constexpr uintptr_t NULL_CHECK_SKIP          = 0x004078CD;
	constexpr uintptr_t NULL_CHECK_CONT          = 0x004071DF;

	constexpr uintptr_t PENDING_REMOVAL_JE1      = 0x00436740;
	constexpr uintptr_t PENDING_REMOVAL_JE2      = 0x004367CD;

	constexpr uintptr_t CULL_JUMPS[] = {
		0x004072BD, 0x004072D2, 0x00407AF1, 0x00407B30,
		0x00407B49, 0x00407B62, 0x00407B7B, 0x004071CE,
		0x00407976, 0x00407B06, 0x00407ABC,
	};

	// -- Helpers --

	static bool patch_bytes(uintptr_t addr, const uint8_t* bytes, size_t len)
	{
		DWORD old_protect;
		if (!VirtualProtect(reinterpret_cast<void*>(addr), len, PAGE_EXECUTE_READWRITE, &old_protect))
			return false;
		std::memcpy(reinterpret_cast<void*>(addr), bytes, len);
		VirtualProtect(reinterpret_cast<void*>(addr), len, old_protect, &old_protect);
		return true;
	}

	static bool nop_bytes(uintptr_t addr, size_t len)
	{
		DWORD old_protect;
		if (!VirtualProtect(reinterpret_cast<void*>(addr), len, PAGE_EXECUTE_READWRITE, &old_protect))
			return false;
		std::memset(reinterpret_cast<void*>(addr), 0x90, len);
		VirtualProtect(reinterpret_cast<void*>(addr), len, old_protect, &old_protect);
		return true;
	}

	static bool write_float(uintptr_t addr, float value)
	{
		DWORD old_protect;
		if (!VirtualProtect(reinterpret_cast<void*>(addr), 4, PAGE_EXECUTE_READWRITE, &old_protect))
			return false;
		*reinterpret_cast<float*>(addr) = value;
		VirtualProtect(reinterpret_cast<void*>(addr), 4, old_protect, &old_protect);
		return true;
	}

	static bool write_uint32(uintptr_t addr, uint32_t value)
	{
		DWORD old_protect;
		if (!VirtualProtect(reinterpret_cast<void*>(addr), 4, PAGE_EXECUTE_READWRITE, &old_protect))
			return false;
		*reinterpret_cast<uint32_t*>(addr) = value;
		VirtualProtect(reinterpret_cast<void*>(addr), 4, old_protect, &old_protect);
		return true;
	}

	// -- Public API --

	void init_game_addresses()
	{
		shared::common::log("Game", "TRL addresses initialized (static, no ASLR)", shared::common::LOG_TYPE::LOG_TYPE_DEFAULT, false);
	}

	void apply_memory_patches()
	{
		using shared::common::log;
		using shared::common::LOG_TYPE;

		log("Game", "Applying TRL memory patches...", LOG_TYPE::LOG_TYPE_DEFAULT, false);

		// 1. Frustum threshold → -1e30
		write_float(FRUSTUM_THRESHOLD, -1e30f);
		log("Game", "  Frustum threshold -> -1e30", LOG_TYPE::LOG_TYPE_DEFAULT, false);

		// 2. NOP 11 scene traversal cull jumps (6 bytes each)
		int nop_count = 0;
		for (auto addr : CULL_JUMPS)
			if (nop_bytes(addr, 6)) nop_count++;
		log("Game", std::format("  NOPed cull jumps: {}/11", nop_count), LOG_TYPE::LOG_TYPE_DEFAULT, false);

		// 3. Null-check trampoline for SceneTraversal (prevents crash on NULL RenderContext)
		{
			uint8_t cave[] = {
				0x8B, 0x93, 0x8C, 0x00, 0x00, 0x00,  // mov edx, [ebx+0x8C]
				0x85, 0xD2,                            // test edx, edx
				0x75, 0x05,                            // jnz +5
				0xE9, 0x00, 0x00, 0x00, 0x00,          // jmp skip_node
				0xE9, 0x00, 0x00, 0x00, 0x00           // jmp continue
			};
			*reinterpret_cast<int32_t*>(cave + 11) = static_cast<int32_t>(NULL_CHECK_SKIP - (NULL_CHECK_CAVE + 15));
			*reinterpret_cast<int32_t*>(cave + 16) = static_cast<int32_t>(NULL_CHECK_CONT - (NULL_CHECK_CAVE + 20));
			patch_bytes(NULL_CHECK_CAVE, cave, sizeof(cave));

			uint8_t jmp_to_cave[6] = { 0xE9, 0, 0, 0, 0, 0x90 };
			*reinterpret_cast<int32_t*>(jmp_to_cave + 1) = static_cast<int32_t>(NULL_CHECK_CAVE - (NULL_CHECK_SITE + 5));
			patch_bytes(NULL_CHECK_SITE, jmp_to_cave, 6);
			log("Game", "  Null-check trampoline at 0x4071D9", LOG_TYPE::LOG_TYPE_DEFAULT, false);
		}

		// 4. ProcessPendingRemovals crash guard: JE → JMP
		{
			uint8_t jmp = 0xEB;
			patch_bytes(PENDING_REMOVAL_JE1, &jmp, 1);
			patch_bytes(PENDING_REMOVAL_JE2, &jmp, 1);
			log("Game", "  ProcessPendingRemovals crash guard", LOG_TYPE::LOG_TYPE_DEFAULT, false);
		}

		// 5. Force all sectors visible
		{
			int s = 0;
			if (nop_bytes(SECTOR_VIS_JE, 6)) s++;
			if (nop_bytes(SECTOR_VIS_JNE, 6)) s++;
			nop_bytes(SECTOR_OBJ_PROXIMITY, 2);
			log("Game", std::format("  Sector visibility NOPs: {}/2 + proximity", s), LOG_TYPE::LOG_TYPE_DEFAULT, false);
		}

		// 6. Cull mode globals → D3DCULL_NONE
		{
			DWORD old_protect;
			if (VirtualProtect(reinterpret_cast<void*>(CULL_MODE_PASS1), 12, PAGE_EXECUTE_READWRITE, &old_protect))
			{
				*reinterpret_cast<uint32_t*>(CULL_MODE_PASS1) = 1;
				*reinterpret_cast<uint32_t*>(CULL_MODE_PASS2) = 1;
				*reinterpret_cast<uint32_t*>(CULL_MODE_PASS2_INV) = 1;
				VirtualProtect(reinterpret_cast<void*>(CULL_MODE_PASS1), 12, old_protect, &old_protect);
			}
			log("Game", "  Cull mode globals -> D3DCULL_NONE", LOG_TYPE::LOG_TYPE_DEFAULT, false);
		}

		// 7. Light culling patches
		nop_bytes(LIGHT_FRUSTUM_REJECT, 6);
		{
			uint8_t vis_patch[] = { 0xB0, 0x01, 0xC2, 0x04, 0x00 };  // mov al,1; ret 4
			patch_bytes(LIGHT_VISIBILITY_TEST, vis_patch, 5);
		}
		nop_bytes(SECTOR_LIGHT_GATE, 2);
		nop_bytes(RENDER_LIGHTS_GATE, 6);
		nop_bytes(LIGHT_COUNT_CLEAR, 6);
		write_uint32(LIGHT_CULLING_FLAG, 1);
		log("Game", "  Light culling fully disabled (6 patches)", LOG_TYPE::LOG_TYPE_DEFAULT, false);

		log("Game", "TRL memory patches complete.", LOG_TYPE::LOG_TYPE_DEFAULT, false);
	}

	void per_frame_stamps()
	{
		// Re-stamp values the game overwrites every frame
		*reinterpret_cast<float*>(FRUSTUM_THRESHOLD) = -1e30f;
		*reinterpret_cast<float*>(FAR_CLIP_STAMP) = 1e10f;
		*reinterpret_cast<uint32_t*>(CULL_MODE_PASS1) = 1;
		*reinterpret_cast<uint32_t*>(CULL_MODE_PASS2) = 1;
		*reinterpret_cast<uint32_t*>(CULL_MODE_PASS2_INV) = 1;
		*reinterpret_cast<uint32_t*>(RENDER_FLAGS) &= ~0x00100000u;
	}
}
