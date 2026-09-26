from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MAPS = (
    "de_mirage",
    "de_dust2",
    "de_inferno",
    "de_nuke",
    "de_vertigo",
    "de_ancient",
    "de_anubis",
    "de_train",
    "de_overpass",
    "cs_office",
    "cs_italy",
)

MAP_GROUPS = {
    "mg_active": DEFAULT_MAPS,
    "mg_dm": DEFAULT_MAPS,
    "mg_multicfg": DEFAULT_MAPS,
    "mg_retake": DEFAULT_MAPS,
}


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
    disabled_plugins: tuple[str, ...] = ()

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
        copied += _write_gamemode_manager_config(self.csgo_root)
        copied += _remove_disabled_plugins(self.csgo_root, self.disabled_plugins)
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
    lines = ['"GameModes_Server.txt"', "{", '  "mapgroups"', "  {"]
    for group_name, maps in MAP_GROUPS.items():
        lines.extend(
            [
                f'    "{group_name}"',
                "    {",
                f'      "name" "{group_name}"',
                '      "maps"',
                "      {",
            ]
        )
        lines.extend(f'        "{map_name}" ""' for map_name in maps)
        lines.extend(["      }", "    }"])
    lines.extend(["  }", "}", ""])
    desired = "\n".join(lines)
    if path.exists() and path.read_text() == desired:
        return 0
    path.write_text(desired)
    return 1


def _write_gamemode_manager_config(csgo_root: Path) -> int:
    path = csgo_root / "addons" / "counterstrikesharp" / "configs" / "plugins" / "GameModeManager" / "GameModeManager.json"
    desired = {
        "Version": 12,
        "RTV": {
            "Enabled": True,
            "PerMap": False,
            "HideHud": False,
            "MinRounds": 1,
            "MinPlayers": 1,
            "VoteDuration": 30,
            "OptionsToShow": 10,
            "VotePercentage": 51,
            "OptionsInCoolDown": 3,
            "EndOfMapVote": True,
            "IncludeModes": False,
            "IncludeExtend": False,
            "MaxExtends": 0,
            "ExtendTime": 15,
            "ExtendRounds": 5,
            "ModePercentage": 40,
            "EnabledInWarmup": False,
            "HideHudAfterVote": False,
            "NominationEnabled": True,
            "MaxNominationWinners": 1,
            "ChangeImmediately": True,
            "TriggerKillsBeforeEnd": 13,
            "TriggerRoundsBeforeEnd": 2,
            "TriggerSecondsBeforeEnd": 120,
        },
        "Maps": {"Mode": 0, "Delay": 5, "Default": "de_mirage"},
        "Votes": {"Enabled": False, "Maps": False, "GameModes": False, "GameSettings": False},
        "Settings": {"Enabled": False, "Folder": "settings"},
        "Warmup": {"Enabled": False, "Time": 60, "PerMap": False, "Default": None, "List": []},
        "Commands": {"Map": True, "Maps": True, "Mode": True, "Modes": True, "TimeLeft": True, "TimeLimit": True},
        "Rotation": {
            "Enabled": False,
            "Cycle": 0,
            "MapGroups": ["mg_dm"],
            "WhenServerEmpty": False,
            "CustomTimeLimit": 900,
            "ModeRotation": False,
            "ModeInterval": 4,
            "ModeSchedules": False,
            "Schedule": [],
        },
        "GameModes": {
            "Default": {"Name": "all-weapons-dm", "Config": "all-weapons-dm.cfg", "DefaultMap": "de_mirage", "MapGroups": ["mg_dm"]},
            "MapGroupFile": "gamemodes_server.txt",
            "List": [
                {"Name": "all-weapons-dm", "Config": "all-weapons-dm.cfg", "DefaultMap": "de_mirage", "MapGroups": ["mg_dm"]},
                {"Name": "multicfg", "Config": "multicfg.cfg", "DefaultMap": "de_mirage", "MapGroups": ["mg_multicfg"]},
                {"Name": "retake", "Config": "retake.cfg", "DefaultMap": "de_mirage", "MapGroups": ["mg_retake"]},
            ],
        },
    }
    rendered = "// Managed by cs2-platform.\n" + json.dumps(desired, indent=2, sort_keys=False) + "\n"
    if path.exists() and path.read_text() == rendered:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered)
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


def _remove_disabled_plugins(csgo_root: Path, disabled_plugins: tuple[str, ...]) -> int:
    removed = 0
    plugins_root = csgo_root / "addons" / "counterstrikesharp" / "plugins"
    for plugin_name in disabled_plugins:
        if not plugin_name or "/" in plugin_name or ".." in plugin_name:
            continue
        path = plugins_root / plugin_name
        if path.exists():
            shutil.rmtree(path)
            removed += 1
    return removed
