from pathlib import Path

import pytest
import yaml

from cs2_tools.validate_mode import validate_mode_file, ValidationError


def test_validate_mode_accepts_minimal_multicfg_profile(tmp_path):
    mode = tmp_path / "mode.yaml"
    mode.write_text(yaml.safe_dump({
        "name": "multicfg",
        "displayName": "Multi-CFG",
        "defaultMap": "de_mirage",
        "exec": "multicfg.cfg",
        "maxPlayers": 24,
        "plugins": {"enabled": ["cs2rcon"]},
    }))
    (tmp_path / "cfg").mkdir()
    (tmp_path / "cfg" / "multicfg.cfg").write_text("echo multicfg")

    result = validate_mode_file(mode)

    assert result.name == "multicfg"
    assert result.exec_cfg == "multicfg.cfg"


def test_repository_contains_valid_all_weapons_dm_profile():
    result = validate_mode_file(Path("configs/modes/all-weapons-dm/mode.yaml"))

    assert result.name == "all-weapons-dm"
    assert result.exec_cfg == "all-weapons-dm.cfg"
    assert result.max_players == 24


def test_all_weapons_dm_includes_post_gamemode_override():
    cfg = Path("configs/modes/all-weapons-dm/cfg/gamemode_deathmatch_server.cfg")

    assert cfg.exists()
    text = cfg.read_text()
    assert "bot_quota 0" in text
    assert "bot_join_after_player 1" in text


def test_repository_contains_valid_retake_profile():
    result = validate_mode_file(Path("configs/modes/retake/mode.yaml"))

    assert result.name == "retake"
    assert result.exec_cfg == "retake.cfg"
    assert result.max_players == 10


def test_retake_mode_stays_plugin_free_and_uses_valve_retake_skirmish():
    cfg = Path("configs/modes/retake/cfg/retake.cfg")

    assert cfg.exists()
    text = cfg.read_text()
    assert "sv_skirmish_id 12" in text
    assert "bot_quota 0" in text
    assert "css_plugins load" not in text


def test_validate_mode_rejects_banned_base_plugins(tmp_path):
    mode = tmp_path / "mode.yaml"
    mode.write_text(yaml.safe_dump({
        "name": "bad",
        "displayName": "Bad",
        "defaultMap": "de_mirage",
        "exec": "bad.cfg",
        "maxPlayers": 24,
        "plugins": {"enabled": ["InventorySimulator"]},
    }))
    (tmp_path / "cfg").mkdir()
    (tmp_path / "cfg" / "bad.cfg").write_text("echo bad")

    with pytest.raises(ValidationError, match="InventorySimulator"):
        validate_mode_file(mode)


def test_validate_mode_rejects_unknown_plugins(tmp_path):
    catalog = tmp_path / "plugins.yaml"
    catalog.write_text(yaml.safe_dump({"plugins": {}}))
    mode = tmp_path / "mode.yaml"
    mode.write_text(yaml.safe_dump({
        "name": "unknown",
        "displayName": "Unknown",
        "defaultMap": "de_mirage",
        "exec": "unknown.cfg",
        "maxPlayers": 24,
        "plugins": {"enabled": ["not-real"]},
    }))
    (tmp_path / "cfg").mkdir()
    (tmp_path / "cfg" / "unknown.cfg").write_text("echo unknown")

    with pytest.raises(ValidationError, match="unknown plugin not-real"):
        validate_mode_file(mode, plugin_catalog_path=catalog)


def test_validate_mode_rejects_disabled_plugins_from_manifest(tmp_path):
    catalog = tmp_path / "plugins.yaml"
    catalog.write_text(yaml.safe_dump({
        "plugins": {
            "heavy": {
                "displayName": "Heavy",
                "phase": "disabled",
                "loader": "counterstrikesharp",
                "enabledByDefault": False,
                "source": "pending",
                "version": "pending",
                "sha256": "2" * 64,
                "entrypoint": "heavy.dll",
            }
        }
    }))
    mode = tmp_path / "mode.yaml"
    mode.write_text(yaml.safe_dump({
        "name": "bad",
        "displayName": "Bad",
        "defaultMap": "de_mirage",
        "exec": "bad.cfg",
        "maxPlayers": 24,
        "plugins": {"enabled": ["heavy"]},
    }))
    (tmp_path / "cfg").mkdir()
    (tmp_path / "cfg" / "bad.cfg").write_text("echo bad")

    with pytest.raises(ValidationError, match="disabled plugin enabled: heavy"):
        validate_mode_file(mode, plugin_catalog_path=catalog)


def test_validate_mode_returns_safe_disabled_runtime_plugin_folders(tmp_path):
    mode = tmp_path / "mode.yaml"
    mode.write_text(yaml.safe_dump({
        "name": "contained",
        "displayName": "Contained",
        "defaultMap": "de_mirage",
        "exec": "contained.cfg",
        "maxPlayers": 24,
        "plugins": {"disabledRuntime": ["GameModeManager", "MenuManagerAPI"]},
    }))
    (tmp_path / "cfg").mkdir()
    (tmp_path / "cfg" / "contained.cfg").write_text("echo contained")

    result = validate_mode_file(mode)

    assert result.disabled_plugins == ("GameModeManager", "MenuManagerAPI")


def test_validate_mode_rejects_unsafe_disabled_runtime_plugin_name(tmp_path):
    mode = tmp_path / "mode.yaml"
    mode.write_text(yaml.safe_dump({
        "name": "bad",
        "displayName": "Bad",
        "defaultMap": "de_mirage",
        "exec": "bad.cfg",
        "maxPlayers": 24,
        "plugins": {"disabledRuntime": ["../MenuManagerAPI"]},
    }))
    (tmp_path / "cfg").mkdir()
    (tmp_path / "cfg" / "bad.cfg").write_text("echo bad")

    with pytest.raises(ValidationError, match="unsafe disabledRuntime plugin name"):
        validate_mode_file(mode)

