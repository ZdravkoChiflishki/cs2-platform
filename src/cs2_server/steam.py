from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .manifest import SteamManifest


@dataclass(frozen=True)
class SteamUpdatePlan:
    repair_stale_manifest: bool
    run_update: bool
    reason: str


@dataclass(frozen=True)
class SteamInstall:
    cs2_root: Path
    steamcmd: Path = Path("/opt/steamcmd/steamcmd.sh")

    @property
    def manifest_path(self) -> Path:
        return self.cs2_root / "steamapps" / "appmanifest_730.acf"

    def plan_update(self) -> SteamUpdatePlan:
        if not self.manifest_path.exists():
            return SteamUpdatePlan(repair_stale_manifest=False, run_update=True, reason="missing_manifest")

        manifest = SteamManifest.read(self.manifest_path)
        if manifest.is_ready:
            return SteamUpdatePlan(repair_stale_manifest=False, run_update=False, reason="already_ready")
        if manifest.needs_repair:
            return SteamUpdatePlan(repair_stale_manifest=True, run_update=True, reason="stale_manifest")
        return SteamUpdatePlan(repair_stale_manifest=False, run_update=True, reason="incomplete_or_missing")

    def update_command(self) -> list[str]:
        return [
            str(self.steamcmd),
            "+@sSteamCmdForcePlatformType",
            "linux",
            "+@sSteamCmdForcePlatformBitness",
            "64",
            "+force_install_dir",
            str(self.cs2_root),
            "+login",
            "anonymous",
            "+app_update",
            "730",
            "+quit",
        ]

    def repair_stale_state(self) -> None:
        self.manifest_path.unlink(missing_ok=True)
        shutil.rmtree(self.cs2_root / "steamapps" / "downloading" / "730", ignore_errors=True)
        shutil.rmtree(self.cs2_root / "steamapps" / "temp" / "730", ignore_errors=True)

    def ensure_updated(self) -> SteamUpdatePlan:
        plan = self.plan_update()
        if plan.repair_stale_manifest:
            self.repair_stale_state()
        if plan.run_update:
            self.cs2_root.mkdir(parents=True, exist_ok=True)
            subprocess.run(self.update_command(), check=True)
        return plan
