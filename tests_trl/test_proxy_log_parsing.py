import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pathlib import Path

from patches.TombRaiderLegend.nightly.logs import parse_proxy_log
from patches.TombRaiderLegend.nightly.manifests import load_nightly_config


def test_proxy_log_parses_required_patch_markers(tmp_path: Path) -> None:
    config = load_nightly_config()
    log_path = tmp_path / "ffp_proxy.log"

    # Generate mock log content
    lines = list(config.required_patch_tokens)
    lines.extend(["DrawCache: replayed", "DrawCache: replayed", "p=0", "q=0"])
    log_content = "\n".join(lines) + "\n"

    log_path.write_text(log_content, encoding="utf-8")
    summary = parse_proxy_log(log_path, config.required_patch_tokens)

    assert summary.all_required_patches_present
    assert summary.max_passthrough == 0
    assert summary.max_xform_blocked == 0
    assert summary.drawcache_replays >= 1


def test_proxy_log_parses_compact_passthrough_and_xform_values(tmp_path: Path) -> None:
    log_path = tmp_path / "ffp_proxy.log"
    log_path.write_text("p=0\\nq=0\nFrameCpuMs=6.4\\n", encoding="utf-8")

    summary = parse_proxy_log(log_path, [])

    assert summary.max_passthrough == 0
    assert summary.max_xform_blocked == 0
    assert summary.p95_cpu_ms == 6.4
