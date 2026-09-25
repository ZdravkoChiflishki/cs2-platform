from cs2_server.runtime_files import prepare_steamclient_libraries


def test_prepare_steamclient_libraries_copies_sdk_files(tmp_path):
    steamcmd = tmp_path / "steamcmd"
    home = tmp_path / "home"
    (steamcmd / "linux64").mkdir(parents=True)
    (steamcmd / "linux32").mkdir(parents=True)
    (steamcmd / "linux64" / "steamclient.so").write_text("64")
    (steamcmd / "linux32" / "steamclient.so").write_text("32")

    copied = prepare_steamclient_libraries(steamcmd, home)

    assert copied == 2
    assert (home / ".steam" / "sdk64" / "steamclient.so").read_text() == "64"
    assert (home / ".steam" / "sdk32" / "steamclient.so").read_text() == "32"
