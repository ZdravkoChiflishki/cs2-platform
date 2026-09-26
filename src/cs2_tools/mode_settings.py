from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ModeSettings:
    name: str
    display_name: str
    default_map: str
    exec_cfg: str
    max_players: int
    game_type: int
    game_mode: int
    map_group: str
    disabled_plugins: tuple[str, ...] = ()


def _plugin_list(data: dict, key: str) -> tuple[str, ...]:
    plugins = data.get("plugins", {}) or {}
    return tuple(str(item).strip() for item in plugins.get(key, []) or [] if str(item).strip())


def load_mode_settings(path: Path) -> ModeSettings:
    data = yaml.safe_load(path.read_text()) or {}
    return ModeSettings(
        name=str(data["name"]),
        display_name=str(data["displayName"]),
        default_map=str(data["defaultMap"]),
        exec_cfg=str(data["exec"]),
        max_players=int(data["maxPlayers"]),
        game_type=int(data.get("gameType", 0)),
        game_mode=int(data.get("gameMode", 0)),
        map_group=str(data.get("mapGroup", "mg_active")),
        disabled_plugins=_plugin_list(data, "disabledRuntime"),
    )
