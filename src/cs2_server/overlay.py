from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OverlayStep:
    layer: str
    source: Path
    destination: Path


@dataclass(frozen=True)
class OverlayPlan:
    steps: list[OverlayStep]

    @classmethod
    def from_roots(
        cls,
        *,
        config_root: Path,
        mode: str,
        server_id: str,
        target_root: Path,
    ) -> "OverlayPlan":
        layers = [
            ("base", config_root / "base"),
            ("mode", config_root / "modes" / mode),
            ("server", config_root / "servers" / server_id),
        ]
        steps: list[OverlayStep] = []
        for layer, root in layers:
            if not root.exists():
                continue
            for source in sorted(p for p in root.rglob("*") if p.is_file()):
                relative = source.relative_to(root)
                if relative.parts and relative.parts[0] == "cfg":
                    relative = Path(*relative.parts[1:])
                steps.append(OverlayStep(layer=layer, source=source, destination=target_root / "cfg" / relative))
        return cls(steps=steps)

    def apply(self) -> None:
        for step in self.steps:
            step.destination.parent.mkdir(parents=True, exist_ok=True)
            step.destination.write_bytes(step.source.read_bytes())
