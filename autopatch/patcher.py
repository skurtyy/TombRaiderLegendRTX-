"""Patch application — runtime (livetools mem write) and source (C edit)."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROXY_DIR = REPO_ROOT / "patches" / "TombRaiderLegend" / "proxy"
PROXY_SRC = PROXY_DIR / "d3d9_device.c"

sys.path.insert(0, str(REPO_ROOT))
from config import GAME_DIR  # noqa: E402
from patches.TombRaiderLegend.run import build_proxy_bundle  # noqa: E402


def apply_runtime(addr: int, patch_bytes: bytes) -> bool:
    """Write patch bytes to a running process via livetools.

    Assumes livetools is already attached. Returns True if successful.
    """
    hex_str = patch_bytes.hex()
    result = subprocess.run(
        [sys.executable, "-m", "livetools", "mem", "write", hex(addr), hex_str],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=10,
    )
    success = result.returncode == 0 and "error" not in result.stdout.lower()
    if success:
        print(f"[patcher] Runtime patch applied: {hex(addr)} <- {hex_str}")
    else:
        print(
            f"[patcher] Runtime patch FAILED at {hex(addr)}: {result.stdout} {result.stderr}"
        )
    return success


def revert_runtime(addr: int, original_bytes: bytes) -> bool:
    """Restore original bytes at a runtime address."""
    return apply_runtime(addr, original_bytes)


def attach_livetools(target: str = "trl.exe") -> bool:
    """Attach livetools to the target process."""
    result = subprocess.run(
        [sys.executable, "-m", "livetools", "attach", target],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    success = result.returncode == 0
    if success:
        print(f"[patcher] Attached to {target}")
    else:
        print(f"[patcher] Failed to attach: {result.stdout} {result.stderr}")
    return success


def detach_livetools() -> None:
    """Detach livetools from the current process."""
    subprocess.run(
        [sys.executable, "-m", "livetools", "detach"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=10,
    )
    print("[patcher] Detached")


def promote_to_source(addr: int, patch_bytes: bytes, description: str) -> bool:
    """Add a patch to TRL_ApplyMemoryPatches() in d3d9_device.c.

    Inserts a new NOP/write block following the existing pattern, just before
    the closing brace of TRL_ApplyMemoryPatches.
    """
    source = PROXY_SRC.read_text()

    size = len(patch_bytes)

    if size <= 6 and all(b == 0x90 for b in patch_bytes):
        # NOP patch
        nop_lines = "\n".join(f"            p[{i}] = 0x90;" for i in range(size))
        patch_block = f"""
    /* Autopatch: {description} */
    {{
        unsigned char *p = (unsigned char *){hex(addr)};
        if (VirtualProtect(p, {size}, PAGE_EXECUTE_READWRITE, &oldProtect)) {{
{nop_lines}
            VirtualProtect(p, {size}, oldProtect, &oldProtect);
            log_str("  Autopatch NOP at {hex(addr)}\\r\\n");
        }}
    }}
"""
    else:
        # Arbitrary byte write
        byte_lines = "\n".join(
            f"            p[{i}] = 0x{b:02X};" for i, b in enumerate(patch_bytes)
        )
        patch_block = f"""
    /* Autopatch: {description} */
    {{
        unsigned char *p = (unsigned char *){hex(addr)};
        if (VirtualProtect(p, {size}, PAGE_EXECUTE_READWRITE, &oldProtect)) {{
{byte_lines}
            VirtualProtect(p, {size}, oldProtect, &oldProtect);
            log_str("  Autopatch bytes at {hex(addr)}\\r\\n");
        }}
    }}
"""

    # Insert before the last closing brace of TRL_ApplyMemoryPatches
    # Find the function and its last }
    func_match = re.search(
        r"(static void TRL_ApplyMemoryPatches\(.*?\{)",
        source,
        re.DOTALL,
    )
    if not func_match:
        print("[patcher] ERROR: Could not find TRL_ApplyMemoryPatches in source")
        return False

    # Find the function's end — look for the next function definition or end of
    # the patch section. The function ends with a } at column 0.
    func_start = func_match.start()
    # Find all top-level closing braces after the function start
    remaining = source[func_start:]
    brace_depth = 0
    func_end_offset = None
    for i, ch in enumerate(remaining):
        if ch == "{":
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
            if brace_depth == 0:
                func_end_offset = func_start + i
                break

    if func_end_offset is None:
        print("[patcher] ERROR: Could not find end of TRL_ApplyMemoryPatches")
        return False

    # Insert patch block before the closing brace
    new_source = source[:func_end_offset] + patch_block + source[func_end_offset:]
    PROXY_SRC.write_text(new_source)
    print(f"[patcher] Promoted patch to source: {hex(addr)} ({description})")
    return True


def build_and_deploy() -> bool:
    """Build the proxy DLL and deploy to the game directory."""
    try:
        build_proxy_bundle(
            proxy_dir=PROXY_DIR,
            proxy_ini_path=PROXY_DIR / "proxy.ini",
            rtx_conf_path=REPO_ROOT / "patches" / "TombRaiderLegend" / "rtx.conf",
            game_dir=GAME_DIR,
        )
    except Exception as exc:
        print(f"[patcher] BUILD FAILED:\n{exc}")
        return False
    print("[patcher] Built and deployed proxy to game directory")
    return True
