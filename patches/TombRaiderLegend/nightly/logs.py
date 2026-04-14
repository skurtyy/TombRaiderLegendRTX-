"""Proxy log parsing and hard-gate extraction."""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path


_RE_PASSTHROUGH = re.compile(r"passthrough=(\d+)")
_RE_XFORM = re.compile(r"xformBlocked=(\d+)")
_RE_P_COMPACT = re.compile(r"^p=(\d+)$", re.MULTILINE)
_RE_Q_COMPACT = re.compile(r"^q=(\d+)$", re.MULTILINE)
_RE_CPU_MS = re.compile(r"FrameCpuMs(?:=|:)\s*([0-9]+(?:\.[0-9]+)?)")


@dataclass
class ProxyLogSummary:
    required_patch_hits: dict[str, bool] = field(default_factory=dict)
    passthrough_values: list[int] = field(default_factory=list)
    xform_blocked_values: list[int] = field(default_factory=list)
    sky_isolation_events: int = 0
    drawcache_replays: int = 0
    frame_cpu_ms: list[float] = field(default_factory=list)

    @property
    def all_required_patches_present(self) -> bool:
        return all(self.required_patch_hits.values()) if self.required_patch_hits else True

    @property
    def max_passthrough(self) -> int:
        return max(self.passthrough_values) if self.passthrough_values else 0

    @property
    def max_xform_blocked(self) -> int:
        return max(self.xform_blocked_values) if self.xform_blocked_values else 0

    @property
    def p95_cpu_ms(self) -> float:
        if not self.frame_cpu_ms:
            return float("inf")
        ordered = sorted(self.frame_cpu_ms)
        index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * 0.95)))
        return float(ordered[index])

    @property
    def median_cpu_ms(self) -> float:
        if not self.frame_cpu_ms:
            return float("inf")
        return float(statistics.median(self.frame_cpu_ms))


def parse_proxy_log(path: str | Path | None, required_patch_tokens: list[str]) -> ProxyLogSummary:
    summary = ProxyLogSummary(
        required_patch_hits={token: False for token in required_patch_tokens},
    )
    if path is None:
        return summary
    log_path = Path(path)
    if not log_path.exists():
        return summary

    text = log_path.read_text(encoding="utf-8", errors="replace")

    for token in required_patch_tokens:
        summary.required_patch_hits[token] = token in text

    summary.passthrough_values.extend(int(match.group(1)) for match in _RE_PASSTHROUGH.finditer(text))
    summary.xform_blocked_values.extend(int(match.group(1)) for match in _RE_XFORM.finditer(text))

    if not summary.passthrough_values:
        summary.passthrough_values.extend(int(match.group(1)) for match in _RE_P_COMPACT.finditer(text))
    if not summary.xform_blocked_values:
        summary.xform_blocked_values.extend(int(match.group(1)) for match in _RE_Q_COMPACT.finditer(text))

    summary.sky_isolation_events = text.count("SkyIso:") + text.count("SkyIsolation:")
    summary.drawcache_replays = text.count("DrawCache: replayed")
    summary.frame_cpu_ms.extend(float(match.group(1)) for match in _RE_CPU_MS.finditer(text))
    return summary
