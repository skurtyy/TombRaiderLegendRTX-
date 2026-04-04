#include "std_include.hpp"
#include "renderer.hpp"

#include "imgui.hpp"
#include "diagnostics.hpp"
#include "shared/common/ffp_state.hpp"

namespace comp
{
	namespace tex_addons
	{
		bool initialized = false;
		LPDIRECT3DTEXTURE9 icon = nullptr;

		void init_texture_addons(bool release)
		{
			if (release)
			{
				if (tex_addons::icon) tex_addons::icon->Release();
				return;
			}

			const auto dev = shared::globals::d3d_device;
			const char* icon_path = "rtx_comp\\textures\\icon.png";

			// Only load if the file exists — no icon is shipped by default
			if (GetFileAttributesA(icon_path) != INVALID_FILE_ATTRIBUTES)
			{
				HRESULT hr = D3DXCreateTextureFromFileA(dev, icon_path, &tex_addons::icon);
				if (FAILED(hr))
					shared::common::log("Renderer", std::format("Failed to load {}", icon_path), shared::common::LOG_TYPE::LOG_TYPE_ERROR, true);
			}

			tex_addons::initialized = true;
		}
	}


	// ----

	drawcall_mod_context& setup_context(IDirect3DDevice9* dev)
	{
		auto& ctx = renderer::dc_ctx;
		ctx.info.device_ptr = dev;
		return ctx;
	}


	// ----

	HRESULT renderer::on_draw_primitive(IDirect3DDevice9* dev, const D3DPRIMITIVETYPE& PrimitiveType, const UINT& StartVertex, const UINT& PrimitiveCount)
	{
		// PURE PASSTHROUGH — crash isolation test
		return dev->DrawPrimitive(PrimitiveType, StartVertex, PrimitiveCount);
	}


	// ----

	HRESULT renderer::on_draw_indexed_prim(IDirect3DDevice9* dev, const D3DPRIMITIVETYPE& PrimitiveType, const INT& BaseVertexIndex, const UINT& MinVertexIndex, const UINT& NumVertices, const UINT& startIndex, const UINT& primCount)
	{
		// PURE PASSTHROUGH — crash isolation test
		return dev->DrawIndexedPrimitive(PrimitiveType, BaseVertexIndex, MinVertexIndex, NumVertices, startIndex, primCount);
	}

	// ---

	void renderer::manually_trigger_remix_injection(IDirect3DDevice9* dev)
	{
		if (!m_triggered_remix_injection)
		{
			auto& ctx = dc_ctx;

			dev->SetRenderState(D3DRS_FOGENABLE, FALSE);

			ctx.save_vs(dev);
			dev->SetVertexShader(nullptr);
			ctx.save_ps(dev);
			dev->SetPixelShader(nullptr);

			ctx.save_rs(dev, D3DRS_ZWRITEENABLE);
			dev->SetRenderState(D3DRS_ZWRITEENABLE, FALSE);

			IDirect3DVertexDeclaration9* saved_decl = nullptr;
			dev->GetVertexDeclaration(&saved_decl);
			dev->SetFVF(D3DFVF_XYZRHW | D3DFVF_DIFFUSE);

			struct CUSTOMVERTEX
			{
				float x, y, z, rhw;
				D3DCOLOR color;
			};

			const auto color = D3DCOLOR_COLORVALUE(0, 0, 0, 0);
			const auto w = -0.49f;
			const auto h = -0.495f;

			CUSTOMVERTEX vertices[] =
			{
				{ -0.5f, -0.5f, 0.0f, 1.0f, color },
				{     w, -0.5f, 0.0f, 1.0f, color },
				{ -0.5f,     h, 0.0f, 1.0f, color },
				{     w,     h, 0.0f, 1.0f, color }
			};

			dev->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, vertices, sizeof(CUSTOMVERTEX));

			if (saved_decl)
			{
				dev->SetVertexDeclaration(saved_decl);
				saved_decl->Release();
			}

			ctx.restore_vs(dev);
			ctx.restore_ps(dev);
			ctx.restore_render_state(dev, D3DRS_ZWRITEENABLE);
			m_triggered_remix_injection = true;
		}
	}


	renderer::renderer()
	{
		p_this = this;

		// Initialize FFP state tracker
		shared::common::ffp_state::get().init(shared::globals::d3d_device);

		// GAME-SPECIFIC: Create hooks as required.
		// See documentation for per-object hook examples.

		m_initialized = true;
		shared::common::log("Renderer", "Module initialized.", shared::common::LOG_TYPE::LOG_TYPE_DEFAULT, false);
	}

	renderer::~renderer()
	{
		tex_addons::init_texture_addons(true);
		p_this = nullptr;
	}
}
