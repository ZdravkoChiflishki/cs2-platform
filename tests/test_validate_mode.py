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
