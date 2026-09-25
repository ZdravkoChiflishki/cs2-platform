from pathlib import Path

from cs2_server.runtime_files import steamcmd_needs_bootstrap


def test_steamcmd_needs_bootstrap_when_64_bit_steamclient_missing(tmp_path: Path):
    steamcmd = tmp_path / "steamcmd"
    (steamcmd / "linux32").mkdir(parents=True)
    (steamcmd / "linux32" / "steamclient.so").write_text("32")

    assert steamcmd_needs_bootstrap(steamcmd) is True


def test_steamcmd_does_not_need_bootstrap_when_both_steamclients_exist(tmp_path: Path):
    steamcmd = tmp_path / "steamcmd"
    (steamcmd / "linux32").mkdir(parents=True)
    (steamcmd / "linux64").mkdir(parents=True)
    (steamcmd / "linux32" / "steamclient.so").write_text("32")
    (steamcmd / "linux64" / "steamclient.so").write_text("64")

    assert steamcmd_needs_bootstrap(steamcmd) is False
