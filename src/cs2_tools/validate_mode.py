from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import yaml


BANNED_DEFAULT_PLUGINS = {
    "InventorySimulator",
    "GameCMS",
    "GameCMS.ORG",
    "DiscordStatus",
    "Ranks",
    "[Ranks] Core",
}


class ValidationError(ValueError):
    """Raised when a mode profile is invalid."""


@dataclass(frozen=True)
class ModeValidationResult:
    name: str
    exec_cfg: str
    max_players: int


def validate_mode_file(path: Path) -> ModeValidationResult:
    data = yaml.safe_load(path.read_text()) or {}
    for key in ("name", "displayName", "defaultMap", "exec", "maxPlayers"):
        if key not in data:
            raise ValidationError(f"{path}: missing required key {key}")

    exec_cfg = str(data["exec"])
    cfg_path = path.parent / "cfg" / exec_cfg
    if not cfg_path.exists():
        raise ValidationError(f"{path}: exec cfg does not exist: {cfg_path}")

    plugins = data.get("plugins", {}).get("enabled", []) or []
    banned = sorted(set(map(str, plugins)) & BANNED_DEFAULT_PLUGINS)
    if banned:
        raise ValidationError(f"{path}: banned default plugins enabled: {', '.join(banned)}")

    return ModeValidationResult(name=str(data["name"]), exec_cfg=exec_cfg, max_players=int(data["maxPlayers"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode_files", nargs="+")
    args = parser.parse_args(argv)
    for filename in args.mode_files:
        result = validate_mode_file(Path(filename))
        print(f"ok {result.name} exec={result.exec_cfg} maxPlayers={result.max_players}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
