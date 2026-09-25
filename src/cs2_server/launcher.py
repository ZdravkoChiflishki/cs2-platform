from __future__ import annotations

from .config import ServerConfig


def build_launch_command(config: ServerConfig) -> list[str]:
    binary = config.cs2_root / "game" / "bin" / "linuxsteamrt64" / "cs2"
    return [
        str(binary),
        "-dedicated",
        "-console",
        "-usercon",
        "-disable_workshop_command_filtering",
        "-tickrate",
        str(config.tickrate),
        "-port",
        str(config.port),
        "-maxplayers_override",
        str(config.maxplayers),
        "+map",
        config.map,
        "+sv_visiblemaxplayers",
        str(config.maxplayers),
        "-authkey",
        config.api_key,
        "+sv_setsteamaccount",
        config.steam_account,
        "+game_type",
        str(config.game_type),
        "+game_mode",
        str(config.game_mode),
        "+mapgroup",
        config.map_group,
        "+sv_lan",
        str(config.lan),
        "+sv_password",
        config.server_password,
        "+rcon_password",
        config.rcon_password,
        "+exec",
        config.exec_cfg,
    ]
