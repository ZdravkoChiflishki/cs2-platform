from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ALLOWED_PHASES = {"planned", "disabled", "staged", "enabled"}
ALLOWED_LOADERS = {"counterstrikesharp", "metamod", "native", "config-only"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PluginManifestError(ValueError):
    """Raised when the plugin manifest is invalid."""


@dataclass(frozen=True)
class PluginDefinition:
    name: str
    display_name: str
    phase: str
    loader: str
    enabled_by_default: bool
    source: str
    version: str
    sha256: str
    entrypoint: str
    notes: str = ""


@dataclass(frozen=True)
class PluginCatalog:
    plugins: dict[str, PluginDefinition]
    path: Path

    @classmethod
    def load(cls, path: Path = Path("plugins/plugins.yaml")) -> "PluginCatalog":
        data = yaml.safe_load(path.read_text()) or {}
        raw_plugins = data.get("plugins")
        if not isinstance(raw_plugins, dict):
            raise PluginManifestError(f"{path}: missing plugins map")
        plugins = {name: _parse_plugin(path, name, raw) for name, raw in raw_plugins.items()}
        return cls(plugins=plugins, path=path)

    def require(self, name: str) -> PluginDefinition:
        try:
            return self.plugins[name]
        except KeyError as exc:
            raise PluginManifestError(f"{self.path}: unknown plugin {name}") from exc


def _parse_plugin(path: Path, name: str, raw: Any) -> PluginDefinition:
    if not isinstance(raw, dict):
        raise PluginManifestError(f"{path}: plugin {name} must be a map")
    required = ["displayName", "phase", "loader", "enabledByDefault", "source", "version", "sha256", "entrypoint"]
    missing = [key for key in required if key not in raw]
    if missing:
        raise PluginManifestError(f"{path}: plugin {name} missing required keys: {', '.join(missing)}")

    phase = str(raw["phase"])
    if phase not in ALLOWED_PHASES:
        raise PluginManifestError(f"{path}: plugin {name} phase must be one of {', '.join(sorted(ALLOWED_PHASES))}")
    loader = str(raw["loader"])
    if loader not in ALLOWED_LOADERS:
        raise PluginManifestError(f"{path}: plugin {name} loader must be one of {', '.join(sorted(ALLOWED_LOADERS))}")
    sha256 = str(raw["sha256"])
    if not SHA256_RE.match(sha256):
        raise PluginManifestError(f"{path}: plugin {name} sha256 must be 64 lowercase hex characters")

    return PluginDefinition(
        name=str(name),
        display_name=str(raw["displayName"]),
        phase=phase,
        loader=loader,
        enabled_by_default=bool(raw["enabledByDefault"]),
        source=str(raw["source"]),
        version=str(raw["version"]),
        sha256=sha256,
        entrypoint=str(raw["entrypoint"]),
        notes=str(raw.get("notes", "")),
    )


def _dump_catalog(catalog: PluginCatalog) -> str:
    lines = []
    for name in sorted(catalog.plugins):
        plugin = catalog.plugins[name]
        lines.append(f"ok {plugin.name} phase={plugin.phase} loader={plugin.loader} default={str(plugin.enabled_by_default).lower()}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the CS2 plugin manifest/lock")
    parser.add_argument("manifest", nargs="?", type=Path, default=Path("plugins/plugins.yaml"))
    args = parser.parse_args(argv)

    catalog = PluginCatalog.load(args.manifest)
    print(_dump_catalog(catalog))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
