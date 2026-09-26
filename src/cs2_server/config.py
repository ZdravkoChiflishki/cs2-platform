from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    """Raised when server runtime configuration is invalid."""


@dataclass(frozen=True)
class ServerConfig:
    server_id: str
    mode: str
    map: str
    port: int
    maxplayers: int
    tickrate: int
    rcon_password: str
    steam_account: str
    api_key: str
    server_password: str
    lan: int
    cs2_root: Path
    config_root: Path
    exec_cfg: str
    game_type: int = 0
    game_mode: int = 0
    map_group: str = "mg_active"
    cache_root: Path | None = None
    steam_update_policy: str = "always"
    plugin_runtime_enabled: bool = False
    plugin_runtime_root: Path = Path("/opt/cs2-platform/plugin-runtime")
    disabled_plugins: tuple[str, ...] = ()
    admin_steam_ids: tuple[str, ...] = ()
    admin_flags: tuple[str, ...] = ("@css/rcon",)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ServerConfig":
        values: Mapping[str, str] = env if env is not None else os.environ
        required = ["RCON_PASSWORD", "STEAM_ACCOUNT", "API_KEY"]
        missing = [name for name in required if not values.get(name)]
        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

        mode = values.get("CS2_MODE", values.get("MODE", "multicfg"))
        return cls(
            server_id=values.get("SERVER_ID", "cs2-server"),
            mode=mode,
            map=values.get("MAP", "de_mirage"),
            port=_int_env(values, "PORT", 27015),
            maxplayers=_int_env(values, "MAXPLAYERS", 24),
            tickrate=_int_env(values, "TICKRATE", 128),
            rcon_password=values["RCON_PASSWORD"],
            steam_account=values["STEAM_ACCOUNT"],
            api_key=values["API_KEY"],
            server_password=values.get("SERVER_PASSWORD", ""),
            lan=_int_env(values, "LAN", 0),
            cs2_root=Path(values.get("CS2_ROOT", "/home/steam/cs2")),
            config_root=Path(values.get("CONFIG_ROOT", "/opt/cs2-platform/configs")),
            exec_cfg=values.get("EXEC", f"{mode}.cfg"),
            game_type=_int_env(values, "GAME_TYPE", 0),
            game_mode=_int_env(values, "GAME_MODE", 0),
            map_group=values.get("MAP_GROUP", "mg_active"),
            cache_root=_optional_path(values.get("CS2_CACHE_ROOT")),
            steam_update_policy=values.get("STEAM_UPDATE_POLICY", "always"),
            plugin_runtime_enabled=_bool_env(values, "ENABLE_PLUGIN_RUNTIME", False),
            plugin_runtime_root=Path(values.get("PLUGIN_RUNTIME_ROOT", "/opt/cs2-platform/plugin-runtime")),
            disabled_plugins=_csv_env(values.get("CS2_DISABLED_PLUGINS")),
            admin_steam_ids=_csv_env(values.get("CS2_ADMIN_STEAM_IDS")),
            admin_flags=_csv_env(values.get("CS2_ADMIN_FLAGS")) or ("@css/rcon",),
        )


def _optional_path(value: str | None) -> Path | None:
    if value is None or value == "":
        return None
    return Path(value)


def _csv_env(value: str | None) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _bool_env(env: Mapping[str, str], name: str, default: bool) -> bool:
    value = env.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(env: Mapping[str, str], name: str, default: int) -> int:
    value = env.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {value!r}") from exc
