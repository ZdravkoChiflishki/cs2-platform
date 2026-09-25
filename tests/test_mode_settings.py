from pathlib import Path

from cs2_tools.mode_settings import ModeSettings, load_mode_settings


def test_load_mode_settings_reads_retake_profile():
    settings = load_mode_settings(Path("configs/modes/retake/mode.yaml"))

    assert settings == ModeSettings(
        name="retake",
        display_name="Retake",
        default_map="de_mirage",
        exec_cfg="retake.cfg",
        max_players=10,
        game_type=0,
        game_mode=0,
        map_group="mg_active",
    )


def test_load_mode_settings_reads_all_weapons_dm_profile():
    settings = load_mode_settings(Path("configs/modes/all-weapons-dm/mode.yaml"))

    assert settings.game_type == 1
    assert settings.game_mode == 2
    assert settings.max_players == 24
