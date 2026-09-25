from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PluginRuntimePlan:
    enabled: bool
    copied: int
    reason: str


@dataclass(frozen=True)
class PluginRuntime:
    source_root: Path
    csgo_root: Path
    enabled: bool

    def apply(self) -> PluginRuntimePlan:
        if not self.enabled:
            return PluginRuntimePlan(enabled=False, copied=0, reason="disabled")
        if not self.source_root.exists():
            return PluginRuntimePlan(enabled=True, copied=0, reason="source_missing")
        copied = _copy_tree(self.source_root, self.csgo_root)
        copied += _normalize_metamod_vdf(self.csgo_root)
        return PluginRuntimePlan(enabled=True, copied=copied, reason="applied")


def _normalize_metamod_vdf(csgo_root: Path) -> int:
    path = csgo_root / "addons" / "metamod_x64.vdf"
    desired = '"Plugin"\n{\n\t"file"\t"addons/metamod/bin/server"\n}\n'
    if path.exists() and path.read_text() == desired:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desired)
    return 1


def _copy_tree(source: Path, target: Path) -> int:
    copied = 0
    for item in sorted(source.rglob("*")):
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(item.read_bytes())
        copied += 1
    return copied
