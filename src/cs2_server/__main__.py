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
from .steam import SteamInstall


def log(event: str, **fields: object) -> None:
    payload = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    print(json.dumps(payload, sort_keys=True), flush=True)


def main() -> int:
    config = ServerConfig.from_env()
    log("config_loaded", server_id=config.server_id, mode=config.mode, map=config.map, port=config.port)

    steam = SteamInstall(config.cs2_root)
    steam_plan = steam.ensure_updated()
    log("steam_update_checked", reason=steam_plan.reason, run_update=steam_plan.run_update, repaired=steam_plan.repair_stale_manifest)

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
