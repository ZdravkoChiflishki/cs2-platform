from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


PINNED_IMAGE_RE = re.compile(r"^zizobg/cs2-server@sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProductionCheck:
    name: str
    ok: bool
    detail: str


def run_production_checks(root: Path = Path(".")) -> list[ProductionCheck]:
    root = root.resolve()
    checks: list[ProductionCheck] = []
    kustomization = _load_yaml(root / "k8s" / "kustomization.yaml")
    resources = list(map(str, kustomization.get("resources", []) or []))
    checks.append(
        ProductionCheck(
            "update_checker_present",
            "base/update-checker.yaml" in resources and (root / "k8s" / "base" / "update-checker.yaml").exists(),
            "base/update-checker.yaml" if "base/update-checker.yaml" in resources else "missing from kustomization",
        )
    )

    deployment_path = root / "k8s" / "servers" / "staging-mirage-multicfg-01-deployment.yaml"
    deployment = _load_yaml(deployment_path)
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    env = _env_map(container.get("env", []))
    image = str(container.get("image", ""))
    checks.append(ProductionCheck("image_pinned", bool(PINNED_IMAGE_RE.match(image)), image or "missing image"))
    checks.append(ProductionCheck("steam_update_policy", env.get("STEAM_UPDATE_POLICY") == "always", env.get("STEAM_UPDATE_POLICY", "missing")))
    checks.append(ProductionCheck("plugin_runtime_enabled", env.get("ENABLE_PLUGIN_RUNTIME") == "true", env.get("ENABLE_PLUGIN_RUNTIME", "missing")))
    checks.append(_service_port_check(root, deployment, env))
    checks.append(_resources_check(container))
    checks.append(_security_context_check(deployment, container))
    checks.append(_data_permission_repair_check(deployment))

    mode_name = env.get("CS2_MODE", "")
    mode_path = root / "configs" / "modes" / mode_name / "mode.yaml"
    if mode_path.exists():
        mode = _load_yaml(mode_path)
        expected_group = str(mode.get("mapGroup", ""))
        actual_group = env.get("MAP_GROUP", "")
        checks.append(ProductionCheck("map_group_matches_mode", actual_group == expected_group, f"deployment={actual_group} mode={expected_group}"))
        expected_map = str(mode.get("defaultMap", ""))
        actual_map = env.get("MAP", "")
        annotation_map = str(deployment.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {}).get("zizo.gg/map", ""))
        checks.append(
            ProductionCheck(
                "map_matches_mode_default",
                actual_map == expected_map and annotation_map == expected_map,
                f"deployment={actual_map} annotation={annotation_map} mode={expected_map}",
            )
        )
        expected_display = str(mode.get("displayName", ""))
        configmap = _load_yaml(root / "k8s" / "servers" / "staging-mirage-multicfg-01-configmap.yaml")
        hostname = _extract_hostname(str(configmap.get("data", {}).get("server.cfg", "")))
        checks.append(
            ProductionCheck(
                "hostname_contains_mode_display",
                bool(expected_display) and expected_display in hostname,
                f"hostname={hostname} mode_display={expected_display}",
            )
        )
        expected_disabled = _csv_join(mode.get("plugins", {}).get("disabledRuntime", []) or [])
        actual_disabled = env.get("CS2_DISABLED_PLUGINS", "")
        checks.append(
            ProductionCheck(
                "disabled_plugins_match_mode",
                actual_disabled == expected_disabled,
                f"deployment={actual_disabled} mode={expected_disabled}",
            )
        )
    else:
        checks.append(ProductionCheck("map_group_matches_mode", False, f"missing mode file for {mode_name!r}"))
        checks.append(ProductionCheck("map_matches_mode_default", False, f"missing mode file for {mode_name!r}"))
        checks.append(ProductionCheck("hostname_contains_mode_display", False, f"missing mode file for {mode_name!r}"))
        checks.append(ProductionCheck("disabled_plugins_match_mode", False, f"missing mode file for {mode_name!r}"))

    if checks[0].ok:
        update_checker_docs = list(yaml.safe_load_all((root / "k8s" / "base" / "update-checker.yaml").read_text()))
        cronjob = next((doc for doc in update_checker_docs if doc and doc.get("kind") == "CronJob"), None)
        schedule = cronjob.get("spec", {}).get("schedule", "") if cronjob else "missing"
        checks.append(ProductionCheck("update_checker_schedule", schedule == "*/15 * * * *", str(schedule)))
        checks.append(_update_checker_hardened_check(update_checker_docs))
    else:
        checks.append(ProductionCheck("update_checker_schedule", False, "update checker missing"))
        checks.append(ProductionCheck("update_checker_hardened", False, "update checker missing"))

    return checks


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text()) or {}


def _update_checker_hardened_check(docs: list[dict[str, Any] | None]) -> ProductionCheck:
    cronjob = next((doc for doc in docs if doc and doc.get("kind") == "CronJob"), None)
    role = next((doc for doc in docs if doc and doc.get("kind") == "Role"), None)
    missing: list[str] = []

    if not cronjob:
        missing.append("CronJob")
        script = ""
        backoff_limit = "missing"
    else:
        job_spec = cronjob.get("spec", {}).get("jobTemplate", {}).get("spec", {}) or {}
        backoff_limit = job_spec.get("backoffLimit", "missing")
        if backoff_limit != 0:
            missing.append("backoffLimit=0")
        containers = job_spec.get("template", {}).get("spec", {}).get("containers", []) or []
        script = str((containers[0].get("args", []) or [""])[0]) if containers else ""

    if not re.search(r"\n\s*verify_manifest_ready\s*\n\s*kubectl patch configmap", script):
        missing.append("verify_manifest_before_tracker_patch")

    role_rules = role.get("rules", []) if role else []
    if "watch" not in _verbs_for_resource(role_rules, "apps", "deployments"):
        missing.append("deployments.watch")
    if "create" not in _verbs_for_resource(role_rules, "", "pods/exec"):
        missing.append("pods/exec.create")

    if missing:
        return ProductionCheck("update_checker_hardened", False, "missing: " + ", ".join(missing))
    return ProductionCheck(
        "update_checker_hardened",
        True,
        "rollout waits for ready appmanifest before tracker patch; rbac includes deployments watch and pods/exec",
    )


def _verbs_for_resource(rules: list[dict[str, Any]], api_group: str, resource: str) -> set[str]:
    verbs: set[str] = set()
    for rule in rules:
        if api_group not in [str(group) for group in rule.get("apiGroups", []) or []]:
            continue
        if resource not in [str(item) for item in rule.get("resources", []) or []]:
            continue
        verbs.update(str(verb) for verb in rule.get("verbs", []) or [])
    return verbs


def _env_map(env: list[dict[str, Any]]) -> dict[str, str]:
    return {str(item["name"]): str(item.get("value", "")) for item in env if "name" in item and "value" in item}


def _service_port_check(root: Path, deployment: dict[str, Any], env: dict[str, str]) -> ProductionCheck:
    service = _load_yaml(root / "k8s" / "servers" / "staging-mirage-multicfg-01-service.yaml")
    service_ports = {str(port.get("name", "")): str(port.get("port", "")) for port in service.get("spec", {}).get("ports", [])}
    env_port = env.get("PORT", "")
    public_address = str(
        deployment.get("spec", {})
        .get("template", {})
        .get("metadata", {})
        .get("annotations", {})
        .get("zizo.gg/public-address", "")
    )
    public_port = _extract_public_port(public_address)
    tcp_port = service_ports.get("game-tcp", "missing")
    udp_port = service_ports.get("game-udp", "missing")
    detail = f"env={env_port} public={public_port} service_tcp={tcp_port} service_udp={udp_port}"
    return ProductionCheck(
        "service_port_matches_deployment",
        bool(env_port) and env_port == public_port == tcp_port == udp_port,
        detail,
    )


def _extract_public_port(public_address: str) -> str:
    match = re.search(r":(\d{1,5})$", public_address)
    return match.group(1) if match else "missing"


def _resources_check(container: dict[str, Any]) -> ProductionCheck:
    resources = container.get("resources", {}) or {}
    requests = resources.get("requests", {}) or {}
    limits = resources.get("limits", {}) or {}
    request_cpu = str(requests.get("cpu", "missing"))
    request_memory = str(requests.get("memory", "missing"))
    limit_cpu = str(limits.get("cpu", "missing"))
    limit_memory = str(limits.get("memory", "missing"))
    detail = (
        f"requests.cpu={request_cpu} requests.memory={request_memory} "
        f"limits.cpu={limit_cpu} limits.memory={limit_memory}"
    )
    return ProductionCheck(
        "resources_declared",
        all(value != "missing" for value in (request_cpu, request_memory, limit_cpu, limit_memory)),
        detail,
    )


def _security_context_check(deployment: dict[str, Any], container: dict[str, Any]) -> ProductionCheck:
    pod_context = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("securityContext", {}) or {}
    container_context = container.get("securityContext", {}) or {}
    drops = container_context.get("capabilities", {}).get("drop", []) or []
    drop_detail = ",".join(map(str, drops))
    detail = (
        f"pod.fsGroup={pod_context.get('fsGroup', 'missing')} "
        f"pod.fsGroupChangePolicy={pod_context.get('fsGroupChangePolicy', 'missing')} "
        f"container.runAsUser={container_context.get('runAsUser', 'missing')} "
        f"container.runAsGroup={container_context.get('runAsGroup', 'missing')} "
        f"allowPrivilegeEscalation={container_context.get('allowPrivilegeEscalation', 'missing')} "
        f"capabilities.drop={drop_detail}"
    )
    ok = (
        pod_context.get("fsGroup") == 1000
        and pod_context.get("fsGroupChangePolicy") == "OnRootMismatch"
        and container_context.get("runAsUser") == 1000
        and container_context.get("runAsGroup") == 1000
        and container_context.get("allowPrivilegeEscalation") is False
        and "ALL" in drops
    )
    return ProductionCheck("security_context_hardened", ok, detail)


def _data_permission_repair_check(deployment: dict[str, Any]) -> ProductionCheck:
    pod_spec = deployment.get("spec", {}).get("template", {}).get("spec", {}) or {}
    init_containers = pod_spec.get("initContainers", []) or []
    repair = next((container for container in init_containers if container.get("name") == "repair-cs2-data-permissions"), None)
    if not repair:
        return ProductionCheck("data_permission_repair_present", False, "missing repair-cs2-data-permissions")

    args = " ".join(map(str, repair.get("args", []) or []))
    mounts = {str(mount.get("name", "")): str(mount.get("mountPath", "")) for mount in repair.get("volumeMounts", []) or []}
    ok = (
        repair.get("image") == "busybox:1.36"
        and repair.get("command") == ["sh", "-c"]
        and "chown -R 1000:1000 /home/steam/cs2" in args
        and mounts.get("cs2-data") == "/home/steam/cs2"
    )
    detail = "repair-cs2-data-permissions chown=1000:1000 mount=/home/steam/cs2" if ok else (
        f"image={repair.get('image', 'missing')} args={args or 'missing'} mount={mounts.get('cs2-data', 'missing')}"
    )
    return ProductionCheck("data_permission_repair_present", ok, detail)


def _csv_join(values: list[Any]) -> str:
    return ",".join(str(value).strip() for value in values if str(value).strip())


def _extract_hostname(server_cfg: str) -> str:
    for line in server_cfg.splitlines():
        stripped = line.strip()
        if not stripped.startswith("hostname"):
            continue
        value = stripped.removeprefix("hostname").strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            return value[1:-1]
        return value
    return "missing"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run static production-readiness checks for cs2-platform.")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    checks = run_production_checks(args.root)
    payload = {"ok": all(check.ok for check in checks), "checks": [asdict(check) for check in checks]}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
