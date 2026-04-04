#include "std_include.hpp"

#include "modules/imgui.hpp"
#include "modules/renderer.hpp"
#include "modules/diagnostics.hpp"
#include "modules/skinning.hpp"
#include "modules/tracer.hpp"
#include "shared/common/remix_api.hpp"
#include "shared/common/config.hpp"
#include "game/game.hpp"

// see comment in main()
//#include "shared/common/dinput_hook_v1.hpp"
//#include "shared/common/dinput_hook_v2.hpp"

namespace comp
{
	void on_begin_scene_cb()
	{
		// Memory patches disabled for crash isolation test
		//static bool patches_applied = false;
		//if (!patches_applied)
		//{
		//	game::apply_memory_patches();
		//	patches_applied = true;
		//}

		if (!tex_addons::initialized) {
			tex_addons::init_texture_addons();
		}

		// Per-frame stamps disabled for crash isolation test
		//game::per_frame_stamps();

		// Note: manually_trigger_remix_injection removed — crashes with dxwrapper's D3D8-to-D3D9 layer.
		// Remix should detect the camera from SetTransform calls in the draw routing.

		// Fake camera (ImGui debug)
		const auto& im = imgui::get();
		if (im->m_dbg_use_fake_camera)
		{
			D3DXMATRIX rotation, translation, view_matrix, proj_matrix;
			D3DXMatrixRotationYawPitchRoll(&rotation,
				D3DXToRadian(im->m_dbg_camera_yaw),
				D3DXToRadian(im->m_dbg_camera_pitch),
				0.0f);
			D3DXMatrixTranslation(&translation,
				-im->m_dbg_camera_pos[0],
				-im->m_dbg_camera_pos[1],
				-im->m_dbg_camera_pos[2]);
			D3DXMatrixMultiply(&view_matrix, &rotation, &translation);
			D3DXMatrixPerspectiveFovLH(&proj_matrix,
				D3DXToRadian(im->m_dbg_camera_fov),
				im->m_dbg_camera_aspect,
				im->m_dbg_camera_near_plane,
				im->m_dbg_camera_far_plane);

			shared::globals::d3d_device->SetTransform(D3DTS_WORLD, &shared::globals::IDENTITY);
			shared::globals::d3d_device->SetTransform(D3DTS_VIEW, &view_matrix);
			shared::globals::d3d_device->SetTransform(D3DTS_PROJECTION, &proj_matrix);
		}
	}


	void main()
	{
		// MINIMAL TEST: Only renderer, no Remix API, no ImGui, no diagnostics.
		// If this doesn't crash, the d3d9 wrapper is compatible with dxwrapper.
		shared::common::loader::module_loader::register_module(std::make_unique<renderer>());

		shared::common::log("Main", "Minimal module load (renderer only)", shared::common::LOG_TYPE::LOG_TYPE_DEFAULT, false);
		MH_EnableHook(MH_ALL_HOOKS);
	}
}
