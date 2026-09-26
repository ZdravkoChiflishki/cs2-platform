from pathlib import Path

import yaml

import pytest

from cs2_tools.server_generator import ServerProfile, ServerProfileValidationError, load_server_profile, render_server_manifests, validate_server_profile


def test_render_server_manifests_uses_profile_and_mode_defaults(tmp_path):
    mode = tmp_path / "configs" / "modes" / "retake" / "mode.yaml"
    mode.parent.mkdir(parents=True)
    mode.write_text(
        """
name: retake
displayName: Retake
defaultMap: de_mirage
exec: retake.cfg
maxPlayers: 10
gameType: 0
gameMode: 0
mapGroup: mg_active
plugins:
  enabled:
    - cs2rcon
  disabledRuntime:
    - GameModeManager
    - MenuManagerAPI
""".strip()
    )
    profile = ServerProfile(
        server_id="retake-01",
        namespace="cs2-servers",
        mode="retake",
        display_name="ZIZO.GG Retake 01",
        map="de_inferno",
        port=26002,
        public_address="zizogaming.duckdns.org:26002",
        node="k0s-slave5",
        image="zizobg/cs2-server@sha256:" + "a" * 64,
        pvc_size="120Gi",
        cache_root=None,
        cpu_request="1000m",
        cpu_limit="4000m",
        memory_request="2Gi",
        memory_limit="8Gi",
        admin_steam_ids=("76561199127257988",),
        admin_flags=("@css/rcon", "@css/root"),
    )

    rendered = render_server_manifests(profile, config_root=tmp_path / "configs")

    assert set(rendered) == {
        "retake-01-configmap.yaml",
        "retake-01-deployment.yaml",
        "retake-01-pvc.yaml",
        "retake-01-service.yaml",
    }
    deployment = yaml.safe_load(rendered["retake-01-deployment.yaml"])
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    env = {entry["name"]: entry.get("value") for entry in container["env"] if "value" in entry}

    assert deployment["metadata"]["labels"]["zizo.gg/mode"] == "retake"
    assert deployment["spec"]["template"]["spec"]["nodeSelector"]["kubernetes.io/hostname"] == "k0s-slave5"
    assert container["image"] == "zizobg/cs2-server@sha256:" + "a" * 64
    assert env["CS2_MODE"] == "retake"
    assert env["MAP"] == "de_inferno"
    assert env["PORT"] == "26002"
    assert env["MAXPLAYERS"] == "10"
    assert env["EXEC"] == "retake.cfg"
    assert env["GAME_TYPE"] == "0"
    assert env["GAME_MODE"] == "0"
    assert env["MAP_GROUP"] == "mg_active"
    assert env["STEAM_UPDATE_POLICY"] == "always"
    assert env["ENABLE_PLUGIN_RUNTIME"] == "true"
    assert env["CS2_ADMIN_STEAM_IDS"] == "76561199127257988"
    assert env["CS2_ADMIN_FLAGS"] == "@css/rcon,@css/root"
    assert env["CS2_DISABLED_PLUGINS"] == "GameModeManager,MenuManagerAPI"
    assert "CS2_CACHE_ROOT" not in env

    service = yaml.safe_load(rendered["retake-01-service.yaml"])
    assert service["spec"]["ports"][0]["port"] == 26002
    assert service["spec"]["ports"][1]["protocol"] == "UDP"


def test_render_server_manifests_can_mount_cache(tmp_path):
    mode = tmp_path / "configs" / "modes" / "all-weapons-dm" / "mode.yaml"
    mode.parent.mkdir(parents=True)
    mode.write_text(
        """
name: all-weapons-dm
displayName: All Weapons DM
defaultMap: de_mirage
exec: all-weapons-dm.cfg
maxPlayers: 24
gameType: 1
gameMode: 2
mapGroup: mg_active
plugins:
  enabled:
    - cs2rcon
""".strip()
    )
    profile = ServerProfile(
        server_id="dm-01",
        namespace="cs2-servers",
        mode="all-weapons-dm",
        display_name="ZIZO.GG DM 01",
        map="de_mirage",
        port=26003,
        public_address="zizogaming.duckdns.org:26003",
        node="k0s-slave5",
        image="zizobg/cs2-server@sha256:" + "b" * 64,
        pvc_size="120Gi",
        cache_root="/cache/cs2",
    )

    rendered = render_server_manifests(profile, config_root=tmp_path / "configs")
    deployment = yaml.safe_load(rendered["dm-01-deployment.yaml"])
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    env = {entry["name"]: entry.get("value") for entry in container["env"] if "value" in entry}
    mounts = {mount["name"]: mount["mountPath"] for mount in container["volumeMounts"]}

    assert env["CS2_CACHE_ROOT"] == "/cache/cs2"
    assert mounts["cs2-cache"] == "/cache/cs2"
    assert any(volume["name"] == "cs2-cache" for volume in deployment["spec"]["template"]["spec"]["volumes"])


def test_load_server_profile_reads_hardening_fields(tmp_path):
    profile_path = tmp_path / "server.yaml"
    profile_path.write_text(
        yaml.safe_dump(
            {
                "server_id": "dm-01",
                "namespace": "cs2-servers",
                "mode": "all-weapons-dm",
                "display_name": "ZIZO.GG DM 01",
                "map": "de_mirage",
                "port": 26003,
                "public_address": "zizogaming.duckdns.org:26003",
                "node": "k0s-slave5",
                "image": "zizobg/cs2-server@sha256:" + "b" * 64,
                "steam_update_policy": "always",
                "plugin_runtime_enabled": True,
                "admin_steam_ids": ["76561199127257988"],
                "admin_flags": ["@css/rcon", "@css/root"],
            },
            sort_keys=False,
        )
    )

    profile = load_server_profile(profile_path)

    assert profile.steam_update_policy == "always"
    assert profile.plugin_runtime_enabled is True
    assert profile.admin_steam_ids == ("76561199127257988",)
    assert profile.admin_flags == ("@css/rcon", "@css/root")


def test_validate_server_profile_accepts_pinned_profile():
    profile = ServerProfile(
        server_id="retake-01",
        namespace="cs2-servers",
        mode="retake",
        display_name="ZIZO.GG Retake 01",
        map="de_mirage",
        port=26002,
        public_address="zizogaming.duckdns.org:26002",
        node="k0s-slave5",
        image="zizobg/cs2-server@sha256:" + "a" * 64,
    )

    assert validate_server_profile(profile) == profile


def test_validate_server_profile_rejects_unsafe_unpinned_or_mismatched_profiles():
    base = dict(
        server_id="retake-01",
        namespace="cs2-servers",
        mode="retake",
        display_name="ZIZO.GG Retake 01",
        map="de_mirage",
        port=26002,
        public_address="zizogaming.duckdns.org:26002",
        node="k0s-slave5",
        image="zizobg/cs2-server@sha256:" + "a" * 64,
    )

    for bad_update, expected in [
        ({"server_id": "Retake_01"}, "server_id"),
        ({"namespace": "CS2 Servers"}, "namespace"),
        ({"image": "zizobg/cs2-server:latest"}, "image must be pinned"),
        ({"public_address": "zizogaming.duckdns.org:27015"}, "public_address port"),
        ({"port": 1023}, "port"),
        ({"cache_root": "cache/cs2"}, "cache_root"),
    ]:
        data = {**base, **bad_update}
        with pytest.raises(ServerProfileValidationError, match=expected):
            validate_server_profile(ServerProfile(**data))
