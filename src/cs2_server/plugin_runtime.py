from __future__ import annotations

import json
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
    admin_steam_ids: tuple[str, ...] = ()
    admin_flags: tuple[str, ...] = ("@css/rcon",)

    def apply(self) -> PluginRuntimePlan:
        if not self.enabled:
            return PluginRuntimePlan(enabled=False, copied=0, reason="disabled")
        if not self.source_root.exists():
            return PluginRuntimePlan(enabled=True, copied=0, reason="source_missing")
        copied = _copy_tree(self.source_root, self.csgo_root)
        copied += _normalize_metamod_vdf(self.csgo_root)
        copied += _patch_gameinfo_for_metamod(self.csgo_root)
        copied += _write_css_admins(self.csgo_root, self.admin_steam_ids, self.admin_flags)
        copied += _write_gamemodes_server(self.csgo_root)
        return PluginRuntimePlan(enabled=True, copied=copied, reason="applied")


def _normalize_metamod_vdf(csgo_root: Path) -> int:
    path = csgo_root / "addons" / "metamod_x64.vdf"
    desired = '"Plugin"\n{\n\t"file"\t"addons/metamod/bin/server"\n}\n'
    if path.exists() and path.read_text() == desired:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desired)
    return 1


def _patch_gameinfo_for_metamod(csgo_root: Path) -> int:
    path = csgo_root / "gameinfo.gi"
    marker = "Game\tcsgo/addons/metamod"
    fallback_marker = "Game    csgo/addons/metamod"
    if not path.exists():
        return 0
    text = path.read_text()
    if marker in text or fallback_marker in text:
        return 0
    lines = text.splitlines(keepends=True)
    insert_at = None
    indent = "\t\t\t"
    for index, line in enumerate(lines):
        if "Game_LowViolence" in line:
            insert_at = index + 1
            indent = line[: len(line) - len(line.lstrip())]
            break
    if insert_at is None:
        for index, line in enumerate(lines):
            if "SearchPaths" in line:
                insert_at = index + 2
                indent = "\t\t\t"
                break
    if insert_at is None:
        return 0
    lines.insert(insert_at, f"{indent}Game\tcsgo/addons/metamod\n")
    path.write_text("".join(lines))
    return 1


def _write_css_admins(csgo_root: Path, admin_steam_ids: tuple[str, ...], admin_flags: tuple[str, ...]) -> int:
    if not admin_steam_ids:
        return 0
    path = csgo_root / "addons" / "counterstrikesharp" / "configs" / "admins.json"
    desired = {
        f"admin-{index + 1}": {
            "identity": steam_id,
            "immunity": 100,
            "flags": list(admin_flags),
        }
        for index, steam_id in enumerate(admin_steam_ids)
    }
    rendered = json.dumps(desired, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text() == rendered:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered)
    return 1


def _write_gamemodes_server(csgo_root: Path) -> int:
    path = csgo_root / "gamemodes_server.txt"
    desired = '''"GameModes_Server.txt"
{
  "mapgroups"
  {
    "mg_active"
    {
      "name" "mg_active"
      "maps"
      {
        "de_mirage" ""
        "de_dust2" ""
        "de_inferno" ""
        "de_nuke" ""
        "de_vertigo" ""
        "de_ancient" ""
        "de_anubis" ""
        "de_train" ""
        "de_overpass" ""
        "cs_office" ""
        "cs_italy" ""
      }
    }
  }
}
'''
    if path.exists() and path.read_text() == desired:
        return 0
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
