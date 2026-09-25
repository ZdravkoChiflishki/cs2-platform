from pathlib import Path

import pytest

from cs2_server.config import ServerConfig, ConfigError
from cs2_server.manifest import SteamManifest
from cs2_server.overlay import OverlayPlan
from cs2_server.launcher import build_launch_command


def test_server_config_reads_required_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("SERVER_ID", "staging-mirage-multicfg-01")
    monkeypatch.setenv("CS2_MODE", "multicfg")
    monkeypatch.setenv("MAP", "de_mirage")
    monkeypatch.setenv("PORT", "26001")
    monkeypatch.setenv("MAXPLAYERS", "24")
    monkeypatch.setenv("TICKRATE", "128")
    monkeypatch.setenv("RCON_PASSWORD", "secret")
    monkeypatch.setenv("STEAM_ACCOUNT", "token")
    monkeypatch.setenv("API_KEY", "apikey")
    monkeypatch.setenv("CS2_ROOT", str(tmp_path / "cs2"))
    monkeypatch.setenv("CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("CS2_CACHE_ROOT", str(tmp_path / "cache"))

    cfg = ServerConfig.from_env()

    assert cfg.server_id == "staging-mirage-multicfg-01"
    assert cfg.mode == "multicfg"
    assert cfg.map == "de_mirage"
    assert cfg.port == 26001
    assert cfg.maxplayers == 24
    assert cfg.tickrate == 128
    assert cfg.rcon_password == "secret"
    assert cfg.game_type == 0
    assert cfg.game_mode == 0
    assert cfg.map_group == "mg_active"
    assert cfg.cs2_root == tmp_path / "cs2"
    assert cfg.config_root == tmp_path / "config"
    assert cfg.cache_root == tmp_path / "cache"
    assert cfg.plugin_runtime_enabled is False
    assert cfg.plugin_runtime_root == Path("/opt/cs2-platform/plugin-runtime")


def test_server_config_reads_game_mode_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("RCON_PASSWORD", "secret")
    monkeypatch.setenv("STEAM_ACCOUNT", "token")
    monkeypatch.setenv("API_KEY", "apikey")
    monkeypatch.setenv("GAME_TYPE", "1")
    monkeypatch.setenv("GAME_MODE", "2")
    monkeypatch.setenv("MAP_GROUP", "mg_active")
    monkeypatch.setenv("CS2_ROOT", str(tmp_path / "cs2"))
    monkeypatch.setenv("CONFIG_ROOT", str(tmp_path / "config"))

    cfg = ServerConfig.from_env()

    assert cfg.game_type == 1
    assert cfg.game_mode == 2
    assert cfg.map_group == "mg_active"


def test_server_config_reads_plugin_runtime_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("RCON_PASSWORD", "secret")
    monkeypatch.setenv("STEAM_ACCOUNT", "token")
    monkeypatch.setenv("API_KEY", "apikey")
    monkeypatch.setenv("ENABLE_PLUGIN_RUNTIME", "true")
    monkeypatch.setenv("PLUGIN_RUNTIME_ROOT", str(tmp_path / "plugin-runtime"))

    cfg = ServerConfig.from_env()

    assert cfg.plugin_runtime_enabled is True
    assert cfg.plugin_runtime_root == tmp_path / "plugin-runtime"


def test_server_config_fails_when_required_secret_missing(monkeypatch):
    monkeypatch.delenv("RCON_PASSWORD", raising=False)

    with pytest.raises(ConfigError, match="RCON_PASSWORD"):
        ServerConfig.from_env()


def test_steam_manifest_detects_ready_and_stale_states(tmp_path):
    manifest = tmp_path / "appmanifest_730.acf"
    manifest.write_text('''"AppState"\n{\n  "appid" "730"\n  "buildid" "24701871"\n  "TargetBuildID" "24701871"\n  "StateFlags" "4"\n  "UpdateResult" "0"\n}\n''')

    ready = SteamManifest.read(manifest)
    assert ready.is_ready
    assert not ready.needs_repair

    manifest.write_text('''"AppState"\n{\n  "appid" "730"\n  "buildid" "24700000"\n  "TargetBuildID" "24701871"\n  "StateFlags" "6"\n  "UpdateResult" "0"\n}\n''')

    stale = SteamManifest.read(manifest)
    assert not stale.is_ready
    assert stale.needs_repair


def test_overlay_plan_orders_base_mode_then_server(tmp_path):
    root = tmp_path / "config"
    (root / "base").mkdir(parents=True)
    (root / "modes" / "multicfg").mkdir(parents=True)
    (root / "servers" / "staging").mkdir(parents=True)
    (root / "base" / "server.cfg").write_text("base")
    (root / "modes" / "multicfg" / "multicfg.cfg").write_text("mode")
    (root / "servers" / "staging" / "server.cfg").write_text("server")

    plan = OverlayPlan.from_roots(
        config_root=root,
        mode="multicfg",
        server_id="staging",
        target_root=tmp_path / "cs2" / "game" / "csgo",
    )

    assert [step.source.name for step in plan.steps] == ["server.cfg", "multicfg.cfg", "server.cfg"]
    assert plan.steps[0].layer == "base"
    assert plan.steps[1].layer == "mode"
    assert plan.steps[2].layer == "server"


def test_build_launch_command_preserves_explicit_values(tmp_path):
    cfg = ServerConfig(
        server_id="staging",
        mode="multicfg",
        map="de_mirage",
        port=26001,
        maxplayers=24,
        tickrate=128,
        rcon_password="secret",
        steam_account="steam-token",
        api_key="api-key",
        server_password="",
        lan=0,
        cs2_root=tmp_path / "cs2",
        config_root=tmp_path / "config",
        exec_cfg="multicfg.cfg",
    )

    command = build_launch_command(cfg)

    assert command[0] == str(tmp_path / "cs2" / "game" / "bin" / "linuxsteamrt64" / "cs2")
    assert "-dedicated" in command
    assert command[command.index("-port") + 1] == "26001"
    assert command[command.index("-maxplayers_override") + 1] == "24"
    assert command[command.index("+sv_visiblemaxplayers") + 1] == "24"
    assert command[command.index("+map") + 1] == "de_mirage"
    assert command[command.index("+exec") + 1] == "multicfg.cfg"
    assert command[command.index("+game_type") + 1] == "0"
    assert command[command.index("+game_mode") + 1] == "0"
    assert command[command.index("+mapgroup") + 1] == "mg_active"
    assert command[command.index("+sv_setsteamaccount") + 1] == "steam-token"


def test_build_launch_command_uses_explicit_game_mode_values(tmp_path):
    cfg = ServerConfig(
        server_id="dm",
        mode="all-weapons-dm",
        map="de_mirage",
        port=26002,
        maxplayers=24,
        tickrate=128,
        rcon_password="secret",
        steam_account="steam-token",
        api_key="api-key",
        server_password="",
        lan=0,
        cs2_root=tmp_path / "cs2",
        config_root=tmp_path / "config",
        exec_cfg="all-weapons-dm.cfg",
        game_type=1,
        game_mode=2,
        map_group="mg_active",
    )

    command = build_launch_command(cfg)

    assert command[command.index("+game_type") + 1] == "1"
    assert command[command.index("+game_mode") + 1] == "2"
    assert command[command.index("+mapgroup") + 1] == "mg_active"
