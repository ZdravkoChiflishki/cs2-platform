from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone

from .config import ServerConfig
from .launcher import build_launch_command
from .overlay import OverlayPlan
from .plugin_runtime import PluginRuntime
from .runtime_files import bootstrap_steamcmd, prepare_server_libraries, prepare_steamclient_libraries
from .steam import SteamInstall
from .steam_cache import SteamCache


def log(event: str, **fields: object) -> None:
    payload = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    print(json.dumps(payload, sort_keys=True), flush=True)


def main() -> int:
    config = ServerConfig.from_env()
    log("config_loaded", server_id=config.server_id, mode=config.mode, map=config.map, port=config.port)

    cache = SteamCache(config.cs2_root, config.cache_root)
    seed_plan = cache.seed_from_cache_if_available()
    log("steam_cache_seed_checked", action=seed_plan.action, reason=seed_plan.reason)

    steam = SteamInstall(config.cs2_root, update_policy=config.steam_update_policy)
    steam_plan = steam.ensure_updated()
    log("steam_update_checked", reason=steam_plan.reason, run_update=steam_plan.run_update, repaired=steam_plan.repair_stale_manifest)

    sync_plan = cache.sync_to_cache_if_needed()
    log("steam_cache_sync_checked", action=sync_plan.action, reason=sync_plan.reason)

    steamcmd_bootstrapped = bootstrap_steamcmd()
    log("steamcmd_bootstrapped", changed=steamcmd_bootstrapped)

    copied_steamclients = prepare_steamclient_libraries()
    log("steamclient_libraries_prepared", copied=copied_steamclients)

    copied_libraries = prepare_server_libraries(config.cs2_root)
    log("server_libraries_prepared", copied=copied_libraries)

    plugin_plan = PluginRuntime(
        source_root=config.plugin_runtime_root,
        csgo_root=config.cs2_root / "game" / "csgo",
        enabled=config.plugin_runtime_enabled,
        admin_steam_ids=config.admin_steam_ids,
        admin_flags=config.admin_flags,
        disabled_plugins=config.disabled_plugins,
    ).apply()
    log("plugin_runtime_checked", enabled=plugin_plan.enabled, copied=plugin_plan.copied, reason=plugin_plan.reason)

    plan = OverlayPlan.from_roots(
        config_root=config.config_root,
        mode=config.mode,
        server_id=config.server_id,
        target_root=config.cs2_root / "game" / "csgo",
    )
    plan.apply()
    log("config_overlay_applied", files=len(plan.steps))

    command = build_launch_command(config)
    log("cs2_starting", argv=[_redact(arg, config) for arg in command])
    process = subprocess.Popen(command, env=os.environ.copy())

    def stop(_signum: int, _frame: object) -> None:
        log("termination_signal_received", pid=process.pid)
        process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    return process.wait()


def _redact(value: str, config: ServerConfig) -> str:
    if value in {config.rcon_password, config.steam_account, config.api_key, config.server_password} and value:
        return "[REDACTED]"
    return value


if __name__ == "__main__":
    raise SystemExit(main())
