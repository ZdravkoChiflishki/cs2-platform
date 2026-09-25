from cs2_server.runtime_files import prepare_server_libraries


def test_prepare_server_libraries_copies_linuxsteamrt64_shared_objects(tmp_path):
    cs2_root = tmp_path / "cs2"
    source = cs2_root / "game" / "bin" / "linuxsteamrt64"
    target = cs2_root / "game" / "csgo" / "bin" / "linuxsteamrt64"
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    (source / "libv8.so").write_text("v8")
    (source / "libtier0.so").write_text("tier0")
    (source / "not-a-library.txt").write_text("ignore")

    copied = prepare_server_libraries(cs2_root)

    assert copied == 2
    assert (target / "libv8.so").read_text() == "v8"
    assert (target / "libtier0.so").read_text() == "tier0"
    assert not (target / "not-a-library.txt").exists()
