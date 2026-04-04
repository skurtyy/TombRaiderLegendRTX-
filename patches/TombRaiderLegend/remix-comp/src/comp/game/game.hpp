#pragma once
#include "structs.hpp"

namespace comp::game
{
	extern void init_game_addresses();
	extern void apply_memory_patches();
	extern void per_frame_stamps();
}
