from pathlib import Path

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

    runtime = PluginRuntime(source_root=source, csgo_root=csgo, enabled=True)
    plan = runtime.apply()

    assert plan == PluginRuntimePlan(enabled=True, copied=4, reason="applied")
    assert (csgo / "addons" / "metamod" / "metaplugins.ini").read_text() == "plugins"
    assert (csgo / "addons" / "counterstrikesharp" / "bin" / "linuxsteamrt64" / "counterstrikesharp.so").read_text() == "so"
    assert '"addons/metamod/bin/server"' in (csgo / "addons" / "metamod_x64.vdf").read_text()


def test_plugin_runtime_fails_when_enabled_but_missing(tmp_path):
    runtime = PluginRuntime(source_root=tmp_path / "missing", csgo_root=tmp_path / "csgo", enabled=True)

    plan = runtime.apply()

    assert plan == PluginRuntimePlan(enabled=True, copied=0, reason="source_missing")
