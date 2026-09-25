from pathlib import Path

from cs2_server.steam_cache import SteamCache, SteamCachePlan


def write_manifest(root: Path, buildid: str = "24701871", target: str = "24701871") -> None:
    manifest = root / "steamapps" / "appmanifest_730.acf"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        f'''"AppState"\n{{\n  "buildid" "{buildid}"\n  "TargetBuildID" "{target}"\n  "UpdateResult" "0"\n}}\n'''
    )


def test_cache_disabled_without_root(tmp_path):
    cache = SteamCache(cs2_root=tmp_path / "server", cache_root=None)

    assert cache.plan_seed() == SteamCachePlan(action="disabled", reason="cache_root_unset")


def test_seed_from_ready_cache_when_server_manifest_missing(tmp_path):
    server = tmp_path / "server"
    cache_root = tmp_path / "cache"
    write_manifest(cache_root)
    (cache_root / "game" / "csgo").mkdir(parents=True)
    (cache_root / "game" / "csgo" / "marker.txt").write_text("cached")

    cache = SteamCache(cs2_root=server, cache_root=cache_root)
    plan = cache.seed_from_cache_if_available()

    assert plan == SteamCachePlan(action="seeded", reason="server_missing_or_not_ready")
    assert (server / "game" / "csgo" / "marker.txt").read_text() == "cached"
    assert (server / "steamapps" / "appmanifest_730.acf").exists()


def test_seed_skips_when_cache_not_ready(tmp_path):
    server = tmp_path / "server"
    cache_root = tmp_path / "cache"
    write_manifest(cache_root, buildid="0", target="24701871")

    cache = SteamCache(cs2_root=server, cache_root=cache_root)
    plan = cache.seed_from_cache_if_available()

    assert plan == SteamCachePlan(action="skipped", reason="cache_not_ready")
    assert not server.exists()


def test_sync_to_cache_when_server_ready_and_cache_missing(tmp_path):
    server = tmp_path / "server"
    cache_root = tmp_path / "cache"
    write_manifest(server)
    (server / "game" / "csgo").mkdir(parents=True)
    (server / "game" / "csgo" / "server.txt").write_text("ready")

    cache = SteamCache(cs2_root=server, cache_root=cache_root)
    plan = cache.sync_to_cache_if_needed()

    assert plan == SteamCachePlan(action="synced", reason="cache_missing_or_not_ready")
    assert (cache_root / "game" / "csgo" / "server.txt").read_text() == "ready"
    assert (cache_root / "steamapps" / "appmanifest_730.acf").exists()


def test_sync_skips_when_cache_same_build(tmp_path):
    server = tmp_path / "server"
    cache_root = tmp_path / "cache"
    write_manifest(server)
    write_manifest(cache_root)

    cache = SteamCache(cs2_root=server, cache_root=cache_root)
    plan = cache.sync_to_cache_if_needed()

    assert plan == SteamCachePlan(action="skipped", reason="cache_current")
