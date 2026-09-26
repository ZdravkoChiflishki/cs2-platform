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
    else:
        checks.append(ProductionCheck("update_checker_schedule", False, "update checker missing"))

    return checks


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text()) or {}


def _env_map(env: list[dict[str, Any]]) -> dict[str, str]:
    return {str(item["name"]): str(item.get("value", "")) for item in env if "name" in item and "value" in item}


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
