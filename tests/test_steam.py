from pathlib import Path

from cs2_server.config import ServerConfig
from cs2_server.steam import SteamInstall, SteamUpdatePlan


def test_steam_update_plan_repairs_nonzero_mismatched_manifest(tmp_path):
    cs2_root = tmp_path / "cs2"
    manifest = cs2_root / "steamapps" / "appmanifest_730.acf"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('''"AppState"\n{\n  "buildid" "24700000"\n  "TargetBuildID" "24701871"\n}\n''')
    (cs2_root / "steamapps" / "downloading" / "730").mkdir(parents=True)
    (cs2_root / "steamapps" / "temp" / "730").mkdir(parents=True)

    install = SteamInstall(cs2_root=cs2_root, steamcmd=tmp_path / "steamcmd.sh")
    plan = install.plan_update()

    assert plan == SteamUpdatePlan(repair_stale_manifest=True, run_update=True, reason="stale_manifest")


def test_steam_update_plan_preserves_buildid_zero_download(tmp_path):
    cs2_root = tmp_path / "cs2"
    manifest = cs2_root / "steamapps" / "appmanifest_730.acf"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('''"AppState"\n{\n  "buildid" "0"\n  "TargetBuildID" "24701871"\n}\n''')

    install = SteamInstall(cs2_root=cs2_root, steamcmd=tmp_path / "steamcmd.sh")
    plan = install.plan_update()

    assert plan == SteamUpdatePlan(repair_stale_manifest=False, run_update=True, reason="incomplete_or_missing")


def test_steam_update_command_uses_app_730_and_install_dir(tmp_path):
    install = SteamInstall(cs2_root=tmp_path / "cs2", steamcmd=tmp_path / "steamcmd.sh")

    command = install.update_command()

    assert str(tmp_path / "steamcmd.sh") == command[0]
    assert "+force_install_dir" in command
    assert command[command.index("+force_install_dir") + 1] == str(tmp_path / "cs2")
    assert command[command.index("+app_update") + 1] == "730"
    assert command[-1] == "+quit"


def test_steam_update_policy_always_runs_app_update_for_ready_manifest(tmp_path):
    cs2_root = tmp_path / "cs2"
    manifest = cs2_root / "steamapps" / "appmanifest_730.acf"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('''"AppState"\n{\n  "buildid" "25515854"\n  "TargetBuildID" "25515854"\n}\n''')

    install = SteamInstall(cs2_root=cs2_root, steamcmd=tmp_path / "steamcmd.sh", update_policy="always")
    plan = install.plan_update()

    assert plan == SteamUpdatePlan(repair_stale_manifest=False, run_update=True, reason="policy_always")


def test_steam_update_policy_manifest_skips_ready_manifest(tmp_path):
    cs2_root = tmp_path / "cs2"
    manifest = cs2_root / "steamapps" / "appmanifest_730.acf"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('''"AppState"\n{\n  "buildid" "25515854"\n  "TargetBuildID" "25515854"\n}\n''')

    install = SteamInstall(cs2_root=cs2_root, steamcmd=tmp_path / "steamcmd.sh", update_policy="manifest")
    plan = install.plan_update()

    assert plan == SteamUpdatePlan(repair_stale_manifest=False, run_update=False, reason="already_ready")
