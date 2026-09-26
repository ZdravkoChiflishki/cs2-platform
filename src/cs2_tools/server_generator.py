from __future__ import annotations

import argparse
import re
from dataclasses import MISSING, dataclass, fields
from pathlib import Path
from typing import Any

import yaml

from .mode_settings import load_mode_settings


DNS_LABEL_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
PINNED_IMAGE_RE = re.compile(r"^[\w./-]+@sha256:[a-f0-9]{64}$")
PUBLIC_ADDRESS_RE = re.compile(r"^[A-Za-z0-9.-]+:(\d{1,5})$")


class ServerProfileValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ServerProfile:
    server_id: str
    namespace: str
    mode: str
    display_name: str
    map: str
    port: int
    public_address: str
    node: str
    image: str
    pvc_size: str = "120Gi"
    cache_root: str | None = None
    cpu_request: str = "1000m"
    cpu_limit: str = "4000m"
    memory_request: str = "2Gi"
    memory_limit: str = "8Gi"
    steam_update_policy: str = "always"
    plugin_runtime_enabled: bool = True
    admin_steam_ids: tuple[str, ...] = ()
    admin_flags: tuple[str, ...] = ("@css/rcon",)


def load_server_profile(path: Path) -> ServerProfile:
    data = yaml.safe_load(path.read_text()) or {}
    valid = {field.name for field in fields(ServerProfile)}
    unknown = sorted(set(data) - valid)
    if unknown:
        raise ValueError(f"unknown server profile fields in {path}: {', '.join(unknown)}")
    missing = [field.name for field in fields(ServerProfile) if field.default is MISSING and field.default_factory is MISSING and field.name not in data]
    if missing:
        raise ValueError(f"missing server profile fields in {path}: {', '.join(missing)}")
    for key in ("admin_steam_ids", "admin_flags"):
        if key in data:
            data[key] = tuple(str(item).strip() for item in data[key] or [] if str(item).strip())
    return ServerProfile(**data)


def validate_server_profile(profile: ServerProfile) -> ServerProfile:
    errors: list[str] = []
    if not DNS_LABEL_RE.fullmatch(profile.server_id):
        errors.append("server_id must be a lowercase DNS label")
    if not DNS_LABEL_RE.fullmatch(profile.namespace):
        errors.append("namespace must be a lowercase DNS label")
    if not (1024 <= profile.port <= 65535):
        errors.append("port must be between 1024 and 65535")
    if not PINNED_IMAGE_RE.fullmatch(profile.image):
        errors.append("image must be pinned by sha256 digest")
    public_address = PUBLIC_ADDRESS_RE.fullmatch(profile.public_address)
    if not public_address:
        errors.append("public_address must be host:port")
    elif int(public_address.group(1)) != profile.port:
        errors.append(f"public_address port {public_address.group(1)} must match port {profile.port}")
    if profile.cache_root is not None and not profile.cache_root.startswith("/"):
        errors.append("cache_root must be an absolute path when set")
    if errors:
        raise ServerProfileValidationError("; ".join(errors))
    return profile


def render_server_manifests(profile: ServerProfile, config_root: Path = Path("configs")) -> dict[str, str]:
    validate_server_profile(profile)
    mode = load_mode_settings(config_root / "modes" / profile.mode / "mode.yaml")
    labels = {
        "app.kubernetes.io/name": "cs2-server",
        "zizo.gg/server-id": profile.server_id,
        "zizo.gg/mode": profile.mode,
        "zizo.gg/region": "eu",
    }

    configmap = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": f"{profile.server_id}-config", "namespace": profile.namespace},
        "data": {
            "server.cfg": f'hostname "{profile.display_name}"\nsv_cheats 0\nsv_lan 0\nbot_quota 0\n'
        },
    }
    pvc = {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {"name": f"{profile.server_id}-data", "namespace": profile.namespace},
        "spec": {
            "accessModes": ["ReadWriteOnce"],
            "storageClassName": "local-path",
            "resources": {"requests": {"storage": profile.pvc_size}},
        },
    }
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": profile.server_id, "namespace": profile.namespace, "labels": labels},
        "spec": {
            "type": "LoadBalancer",
            "externalTrafficPolicy": "Local",
            "selector": {
                "app.kubernetes.io/name": "cs2-server",
                "zizo.gg/server-id": profile.server_id,
            },
            "ports": [
                {"name": "game-tcp", "port": profile.port, "targetPort": "game-tcp", "protocol": "TCP"},
                {"name": "game-udp", "port": profile.port, "targetPort": "game-udp", "protocol": "UDP"},
            ],
        },
    }

    env: list[dict[str, Any]] = [
        {"name": "SERVER_ID", "value": profile.server_id},
        {"name": "CS2_MODE", "value": profile.mode},
        {"name": "MAP", "value": profile.map or mode.default_map},
        {"name": "PORT", "value": str(profile.port)},
        {"name": "MAXPLAYERS", "value": str(mode.max_players)},
        {"name": "TICKRATE", "value": "128"},
        {"name": "EXEC", "value": mode.exec_cfg},
        {"name": "GAME_TYPE", "value": str(mode.game_type)},
        {"name": "GAME_MODE", "value": str(mode.game_mode)},
        {"name": "MAP_GROUP", "value": mode.map_group},
        {"name": "CONFIG_ROOT", "value": "/opt/cs2-platform/configs"},
        {"name": "CS2_ROOT", "value": "/home/steam/cs2"},
        {"name": "STEAM_UPDATE_POLICY", "value": profile.steam_update_policy},
        {"name": "ENABLE_PLUGIN_RUNTIME", "value": str(profile.plugin_runtime_enabled).lower()},
    ]
    if profile.admin_steam_ids:
        env.append({"name": "CS2_ADMIN_STEAM_IDS", "value": ",".join(profile.admin_steam_ids)})
    if profile.admin_flags:
        env.append({"name": "CS2_ADMIN_FLAGS", "value": ",".join(profile.admin_flags)})
    if mode.disabled_plugins:
        env.append({"name": "CS2_DISABLED_PLUGINS", "value": ",".join(mode.disabled_plugins)})
    if profile.cache_root:
        env.append({"name": "CS2_CACHE_ROOT", "value": profile.cache_root})
    env.extend(
        [
            _secret_env("RCON_PASSWORD", "RCON_PASSWORD"),
            _secret_env("STEAM_ACCOUNT", "STEAM_ACCOUNT"),
            _secret_env("API_KEY", "API_KEY"),
            _secret_env("SERVER_PASSWORD", "SERVER_PASSWORD", optional=True),
        ]
    )

    volume_mounts = [
        {"name": "cs2-data", "mountPath": "/home/steam/cs2"},
        {"name": "server-config", "mountPath": f"/opt/cs2-platform/configs/servers/{profile.server_id}/cfg"},
    ]
    volumes = [
        {"name": "cs2-data", "persistentVolumeClaim": {"claimName": f"{profile.server_id}-data"}},
        {"name": "server-config", "configMap": {"name": f"{profile.server_id}-config"}},
    ]
    if profile.cache_root:
        volume_mounts.insert(1, {"name": "cs2-cache", "mountPath": profile.cache_root})
        volumes.insert(1, {"name": "cs2-cache", "persistentVolumeClaim": {"claimName": f"cs2-node-cache-{profile.node.removeprefix('k0s-')}"}})

    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": profile.server_id, "namespace": profile.namespace, "labels": labels},
        "spec": {
            "replicas": 1,
            "strategy": {"type": "Recreate"},
            "selector": {"matchLabels": {"app.kubernetes.io/name": "cs2-server", "zizo.gg/server-id": profile.server_id}},
            "template": {
                "metadata": {
                    "labels": labels,
                    "annotations": {
                        "zizo.gg/display-name": profile.display_name,
                        "zizo.gg/map": profile.map,
                        "zizo.gg/public-address": profile.public_address,
                    },
                },
                "spec": {
                    "serviceAccountName": "cs2-server",
                    "nodeSelector": {"kubernetes.io/hostname": profile.node},
                    "containers": [
                        {
                            "name": "cs2",
                            "image": profile.image,
                            "imagePullPolicy": "Always",
                            "stdin": True,
                            "tty": True,
                            "env": env,
                            "ports": [
                                {"name": "game-tcp", "containerPort": profile.port, "protocol": "TCP"},
                                {"name": "game-udp", "containerPort": profile.port, "protocol": "UDP"},
                            ],
                            "volumeMounts": volume_mounts,
                            "resources": {
                                "requests": {"cpu": profile.cpu_request, "memory": profile.memory_request},
                                "limits": {"cpu": profile.cpu_limit, "memory": profile.memory_limit},
                            },
                        }
                    ],
                    "volumes": volumes,
                },
            },
        },
    }

    return {
        f"{profile.server_id}-configmap.yaml": _dump(configmap),
        f"{profile.server_id}-pvc.yaml": _dump(pvc),
        f"{profile.server_id}-deployment.yaml": _dump(deployment),
        f"{profile.server_id}-service.yaml": _dump(service),
    }


def write_server_manifests(profile_path: Path, out_dir: Path, config_root: Path = Path("configs")) -> list[Path]:
    profile = validate_server_profile(load_server_profile(profile_path))
    rendered = render_server_manifests(profile, config_root=config_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, content in rendered.items():
        path = out_dir / name
        path.write_text(content)
        paths.append(path)
    return paths


def _secret_env(name: str, key: str, optional: bool = False) -> dict[str, Any]:
    ref: dict[str, Any] = {"name": "cs2-secrets", "key": key}
    if optional:
        ref["optional"] = True
    return {"name": name, "valueFrom": {"secretKeyRef": ref}}


def _dump(value: dict[str, Any]) -> str:
    return yaml.safe_dump(value, sort_keys=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate CS2 server Kubernetes manifests from a declarative profile")
    parser.add_argument("profile", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("k8s/servers"))
    parser.add_argument("--config-root", type=Path, default=Path("configs"))
    parser.add_argument("--validate-only", action="store_true", help="validate the profile and mode reference without writing manifests")
    args = parser.parse_args(argv)

    if args.validate_only:
        profile = validate_server_profile(load_server_profile(args.profile))
        load_mode_settings(args.config_root / "modes" / profile.mode / "mode.yaml")
        print(f"ok {args.profile} server_id={profile.server_id} mode={profile.mode} port={profile.port}")
        return 0

    paths = write_server_manifests(args.profile, args.out_dir, args.config_root)
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
