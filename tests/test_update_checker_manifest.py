from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml_documents(path: Path) -> list[dict]:
    return [doc for doc in yaml.safe_load_all(path.read_text()) if doc]


def test_update_checker_cronjob_is_included_in_kustomization():
    kustomization = yaml.safe_load((ROOT / "k8s" / "kustomization.yaml").read_text())

    assert "base/update-checker.yaml" in kustomization["resources"]


def test_update_checker_restarts_staging_deployment_on_new_valve_version():
    docs = load_yaml_documents(ROOT / "k8s" / "base" / "update-checker.yaml")
    cronjob = next(doc for doc in docs if doc["kind"] == "CronJob")
    script = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]["args"][0]

    assert cronjob["metadata"]["name"] == "cs2-update-checker"
    assert "UpToDateCheck/v1/?appid=730&version=0" in script
    assert "deployment/staging-mirage-multicfg-01" in script
    assert "kubectl rollout restart" in script
    assert "kubectl rollout status" in script
    assert "cs2-version-tracker" in script


def test_update_checker_rbac_can_patch_deployments_and_configmaps():
    docs = load_yaml_documents(ROOT / "k8s" / "base" / "update-checker.yaml")
    role = next(doc for doc in docs if doc["kind"] == "Role")
    rules = role["rules"]

    deployment_rule = next(rule for rule in rules if rule["resources"] == ["deployments"])
    configmap_rule = next(rule for rule in rules if rule["resources"] == ["configmaps"])

    assert {"get", "patch", "watch"}.issubset(set(deployment_rule["verbs"]))
    assert {"get", "create", "patch"}.issubset(set(configmap_rule["verbs"]))
