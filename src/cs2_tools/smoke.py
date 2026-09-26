from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass

from .query_server import ServerInfo, query_a2s_info


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    ok: bool
    detail: str


def evaluate_server_info(info: ServerInfo, *, expected_max_players: int, expected_bots: int) -> list[SmokeCheck]:
    return [
        SmokeCheck("a2s_online", True, f"{info.name} {info.map} {info.players}/{info.max_players}"),
        SmokeCheck(
            "max_players",
            info.max_players == expected_max_players,
            f"expected {expected_max_players}, got {info.max_players}",
        ),
        SmokeCheck("bots", info.bots == expected_bots, f"expected {expected_bots}, got {info.bots}"),
    ]


def run_kubectl_check(namespace: str, selector: str, deployment: str) -> list[SmokeCheck]:
    checks: list[SmokeCheck] = []
    pod_json = _kubectl_json("get", "pod", "-n", namespace, "-l", selector, "-o", "json")
    pods = pod_json.get("items", [])
    if not pods:
        return [SmokeCheck("pod_exists", False, f"no pod matched {selector}")]
    pod = pods[0]
    pod_name = pod["metadata"]["name"]
    statuses = pod.get("status", {}).get("containerStatuses", [])
    restarts = sum(int(status.get("restartCount", 0)) for status in statuses)
    ready = all(bool(status.get("ready")) for status in statuses) and bool(statuses)
    checks.append(SmokeCheck("pod_ready", ready, pod_name))
    checks.append(SmokeCheck("pod_restarts", restarts == 0, f"restarts={restarts}"))

    deploy_json = _kubectl_json("get", "deploy", deployment, "-n", namespace, "-o", "json")
    available = int(deploy_json.get("status", {}).get("availableReplicas", 0))
    checks.append(SmokeCheck("deployment_available", available >= 1, f"available={available}"))

    logs = _kubectl_text("logs", pod_name, "-n", namespace, "--tail=600")
    checks.append(evaluate_logs(logs))
    return checks


def evaluate_logs(logs: str) -> SmokeCheck:
    bad_terms = [
        "Segmentation fault",
        "FATAL ERROR",
        "NETWORK_DISCONNECT_LOOPSHUTDOWN",
        "Error invoking callback",
        "Schema target points to null",
    ]
    found = [term for term in bad_terms if term in logs]
    return SmokeCheck("no_fatal_logs", not found, ", ".join(found) if found else "none")


def _kubectl_json(*args: str) -> dict:
    return json.loads(_kubectl_text(*args))


def _kubectl_text(*args: str) -> str:
    return subprocess.check_output(["kubectl", *args], text=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the staging CS2 server.")
    parser.add_argument("--host", default="192.168.0.8")
    parser.add_argument("--port", type=int, default=26001)
    parser.add_argument("--namespace", default="cs2-servers")
    parser.add_argument("--selector", default="zizo.gg/server-id=staging-mirage-multicfg-01")
    parser.add_argument("--deployment", default="staging-mirage-multicfg-01")
    parser.add_argument("--expected-max-players", type=int, default=24)
    parser.add_argument("--expected-bots", type=int, default=0)
    args = parser.parse_args(argv)

    info = query_a2s_info(args.host, args.port)
    checks = evaluate_server_info(info, expected_max_players=args.expected_max_players, expected_bots=args.expected_bots)
    checks.extend(run_kubectl_check(args.namespace, args.selector, args.deployment))
    payload = {"server": info.to_dict(), "checks": [asdict(check) for check in checks], "ok": all(check.ok for check in checks)}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
