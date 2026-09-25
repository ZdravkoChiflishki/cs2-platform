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
        "+map",
        config.map,
        "+sv_visiblemaxplayers",
        str(config.maxplayers),
        "-authkey",
        config.api_key,
        "+sv_setsteamaccount",
        config.steam_account,
        "+game_type",
        "0",
        "+game_mode",
        "0",
        "+mapgroup",
        "mg_active",
        "+sv_lan",
        str(config.lan),
        "+sv_password",
        config.server_password,
        "+rcon_password",
        config.rcon_password,
        "+exec",
        config.exec_cfg,
    ]
