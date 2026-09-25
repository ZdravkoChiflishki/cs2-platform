from pathlib import Path
import json

from cs2_server.plugin_runtime import PluginRuntime, PluginRuntimePlan


def test_plugin_runtime_disabled_without_flag(tmp_path):
    runtime = PluginRuntime(source_root=tmp_path / "runtime", csgo_root=tmp_path / "csgo", enabled=False)

    assert runtime.apply() == PluginRuntimePlan(enabled=False, copied=0, reason="disabled")


def test_plugin_runtime_copies_metamod_and_counterstrikesharp_files(tmp_path):
    source = tmp_path / "runtime"
    csgo = tmp_path / "csgo"
    (source / "addons" / "metamod").mkdir(parents=True)
    (source / "addons" / "metamod" / "metaplugins.ini").write_text("plugins")
    (source / "addons" / "counterstrikesharp" / "bin" / "linuxsteamrt64").mkdir(parents=True)
    (source / "addons" / "counterstrikesharp" / "bin" / "linuxsteamrt64" / "counterstrikesharp.so").write_text("so")
    (source / "addons" / "metamod_x64.vdf").write_text("vdf")
    csgo.mkdir(parents=True)
    (csgo / "gameinfo.gi").write_text(
        '"GameInfo"\n{\n\tFileSystem\n\t{\n\t\tSearchPaths\n\t\t{\n\t\t\tGame_LowViolence\tcsgo_lv // Perfect World content override\n\t\t\tGame\tcsgo\n\t\t}\n\t}\n}\n'
    )

    runtime = PluginRuntime(source_root=source, csgo_root=csgo, enabled=True)
    plan = runtime.apply()

    assert plan == PluginRuntimePlan(enabled=True, copied=7, reason="applied")
    assert (csgo / "addons" / "metamod" / "metaplugins.ini").read_text() == "plugins"
    assert (csgo / "addons" / "counterstrikesharp" / "bin" / "linuxsteamrt64" / "counterstrikesharp.so").read_text() == "so"
    assert '"addons/metamod/bin/server"' in (csgo / "addons" / "metamod_x64.vdf").read_text()
    assert "Game\tcsgo/addons/metamod" in (csgo / "gameinfo.gi").read_text()
    assert '"mg_active"' in (csgo / "gamemodes_server.txt").read_text()
    gmm_config = csgo / "addons" / "counterstrikesharp" / "configs" / "plugins" / "GameModeManager" / "GameModeManager.json"
    assert '"MinPlayers": 1' in gmm_config.read_text()
    assert '"Name": "all-weapons-dm"' in gmm_config.read_text()


def test_plugin_runtime_fails_when_enabled_but_missing(tmp_path):
    runtime = PluginRuntime(source_root=tmp_path / "missing", csgo_root=tmp_path / "csgo", enabled=True)

    plan = runtime.apply()

    assert plan == PluginRuntimePlan(enabled=True, copied=0, reason="source_missing")


def test_plugin_runtime_writes_css_admins_for_rcon_permission(tmp_path):
    source = tmp_path / "runtime"
    csgo = tmp_path / "csgo"
    source.mkdir()

    runtime = PluginRuntime(
        source_root=source,
        csgo_root=csgo,
        enabled=True,
        admin_steam_ids=("76561199127257988",),
        admin_flags=("@css/rcon", "@css/root"),
    )
    plan = runtime.apply()

    admins = json.loads((csgo / "addons" / "counterstrikesharp" / "configs" / "admins.json").read_text())
    assert plan.copied == 4
    assert admins["admin-1"]["identity"] == "76561199127257988"
    assert admins["admin-1"]["flags"] == ["@css/rcon", "@css/root"]
