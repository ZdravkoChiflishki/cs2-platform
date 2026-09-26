from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from .query_server import ServerInfo, query_a2s_info


@dataclass(frozen=True)
class DisruptionCheck:
    ok: bool
    human_players: int
    detail: str


def evaluate_disruption_guard(info: ServerInfo, *, allow_active_players: bool = False) -> DisruptionCheck:
    human_players = max(int(info.players) - int(info.bots), 0)
    if human_players == 0:
        return DisruptionCheck(True, human_players, "safe: no human players connected")
    if allow_active_players:
        return DisruptionCheck(True, human_players, f"override: {human_players} human players connected")
    return DisruptionCheck(False, human_players, f"blocked: {human_players} human players connected")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refuse disruptive CS2 operations while human players are connected.")
    parser.add_argument("--host", default="192.168.0.8")
    parser.add_argument("--port", type=int, default=26001)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument(
        "--allow-active-players",
        action="store_true",
        help="Explicit operator override: allow the disruptive action even when human players are connected.",
    )
    args = parser.parse_args(argv)

    info = query_a2s_info(args.host, args.port, args.timeout)
    check = evaluate_disruption_guard(info, allow_active_players=args.allow_active_players)
    payload = {
        "ok": check.ok,
        "detail": check.detail,
        "human_players": check.human_players,
        "server": info.to_dict(),
        "check": asdict(check),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if check.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
