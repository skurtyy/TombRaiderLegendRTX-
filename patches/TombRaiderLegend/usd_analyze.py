"""Lightweight RTX Remix USD capture analysis."""
from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_MESH_RE = re.compile(rb"mesh_([0-9A-Fa-f]{16})")
_MAT_RE = re.compile(rb"mat_([0-9A-Fa-f]{16})")
_TEX_RE = re.compile(rb"tex_([0-9A-Fa-f]{16})")
_SKEL_RE = re.compile(rb"skel_([0-9A-Fa-f]{16})")


@dataclass
class CaptureSummary:
    path: Path
    mesh_hashes: list[str]
    material_hashes: list[str]
    texture_hashes: list[str]
    skeleton_hashes: list[str]


def _read_bytes(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def _extract_hashes(pattern: re.Pattern[bytes], data: bytes) -> list[str]:
    return sorted({match.group(1).decode("ascii").upper() for match in pattern.finditer(data)})


def extract_mesh_hashes(path: str | Path) -> list[str]:
    return _extract_hashes(_MESH_RE, _read_bytes(path))


def extract_material_hashes(path: str | Path) -> list[str]:
    return _extract_hashes(_MAT_RE, _read_bytes(path))


def extract_texture_hashes(path: str | Path) -> list[str]:
    return _extract_hashes(_TEX_RE, _read_bytes(path))


def extract_skeleton_hashes(path: str | Path) -> list[str]:
    return _extract_hashes(_SKEL_RE, _read_bytes(path))


def summarize_capture(path: str | Path) -> CaptureSummary:
    capture_path = Path(path)
    return CaptureSummary(
        path=capture_path,
        mesh_hashes=extract_mesh_hashes(capture_path),
        material_hashes=extract_material_hashes(capture_path),
        texture_hashes=extract_texture_hashes(capture_path),
        skeleton_hashes=extract_skeleton_hashes(capture_path),
    )


def diff_captures(path_a: str | Path, path_b: str | Path) -> dict[str, list[str]]:
    meshes_a = set(extract_mesh_hashes(path_a))
    meshes_b = set(extract_mesh_hashes(path_b))
    return {
        "stable": sorted(meshes_a & meshes_b),
        "added": sorted(meshes_b - meshes_a),
        "removed": sorted(meshes_a - meshes_b),
    }


def analyze_capture_stability(captures_dir: str | Path) -> dict[str, object]:
    captures = sorted(Path(captures_dir).glob("capture_*.usd"))
    if not captures:
        raise FileNotFoundError(f"No capture_*.usd files found in {captures_dir}")

    counts: Counter[str] = Counter()
    for capture in captures:
        counts.update(extract_mesh_hashes(capture))

    capture_count = len(captures)
    stable = sorted([mesh for mesh, seen in counts.items() if seen == capture_count])
    transient = sorted([mesh for mesh, seen in counts.items() if 1 < seen < capture_count])
    unique = sorted([mesh for mesh, seen in counts.items() if seen == 1])

    return {
        "captures": [str(path) for path in captures],
        "capture_count": capture_count,
        "total_unique_meshes": len(counts),
        "stable_meshes": stable,
        "transient_meshes": transient,
        "unique_meshes": unique,
        "mesh_occurrences": dict(sorted(counts.items())),
    }


def _print_hashes(hashes: Iterable[str]) -> None:
    for mesh_hash in hashes:
        print(mesh_hash)


def _cmd_list(args: argparse.Namespace) -> int:
    summary = summarize_capture(args.capture)
    print("=== Capture Hash List ===")
    print(f"Capture: {summary.path}")
    print(f"Meshes:  {len(summary.mesh_hashes)}")
    _print_hashes(summary.mesh_hashes)
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    diff = diff_captures(args.capture_a, args.capture_b)
    print("=== Capture Diff ===")
    print(f"A: {args.capture_a}")
    print(f"B: {args.capture_b}")
    print(f"Stable:  {len(diff['stable'])}")
    print(f"Added:   {len(diff['added'])}")
    print(f"Removed: {len(diff['removed'])}")
    print("")
    print("Added hashes:")
    _print_hashes(diff["added"])
    print("")
    print("Removed hashes:")
    _print_hashes(diff["removed"])
    return 0


def _cmd_stability(args: argparse.Namespace) -> int:
    report = analyze_capture_stability(args.captures_dir)
    capture_count = report["capture_count"]
    total_unique = report["total_unique_meshes"]
    stable_count = len(report["stable_meshes"])
    transient_count = len(report["transient_meshes"])
    unique_count = len(report["unique_meshes"])
    print("=== Capture Stability Report ===")
    print(f"Captures analyzed: {capture_count}")
    print(f"Total unique meshes: {total_unique}")
    if total_unique:
        print(f"Stable (in all {capture_count}): {stable_count:4d}  ({stable_count / total_unique * 100:4.1f}%)")
        print(f"Transient:           {transient_count:4d}  ({transient_count / total_unique * 100:4.1f}%)")
        print(f"Unique to one:       {unique_count:4d}  ({unique_count / total_unique * 100:4.1f}%)")
    print("")
    print("Top transient hashes:")
    for mesh_hash in report["transient_meshes"][:20]:
        seen = report["mesh_occurrences"][mesh_hash]
        print(f"  mesh_{mesh_hash}  in {seen}/{capture_count} captures")
    return 0


def _cmd_summary(args: argparse.Namespace) -> int:
    summary = summarize_capture(args.capture)
    print("=== Capture Summary ===")
    print(f"Capture:   {summary.path}")
    print(f"Size:      {summary.path.stat().st_size} bytes")
    print(f"Meshes:    {len(summary.mesh_hashes)}")
    print(f"Materials: {len(summary.material_hashes)}")
    print(f"Textures:  {len(summary.texture_hashes)}")
    print(f"Skeletons: {len(summary.skeleton_hashes)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze RTX Remix USD captures without OpenUSD dependencies")
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="List mesh hashes referenced by a capture")
    list_p.add_argument("capture")
    list_p.set_defaults(func=_cmd_list)

    diff_p = sub.add_parser("diff", help="Diff mesh hashes between two captures")
    diff_p.add_argument("capture_a")
    diff_p.add_argument("capture_b")
    diff_p.set_defaults(func=_cmd_diff)

    stability_p = sub.add_parser("stability", help="Analyze mesh hash stability across all captures in a directory")
    stability_p.add_argument("--captures-dir", default="Tomb Raider Legend/rtx-remix/captures")
    stability_p.set_defaults(func=_cmd_stability)

    summary_p = sub.add_parser("summary", help="Summarize a capture's referenced assets")
    summary_p.add_argument("capture")
    summary_p.set_defaults(func=_cmd_summary)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
