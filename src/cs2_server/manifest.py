from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SteamManifest:
    path: Path
    buildid: str | None
    target_buildid: str | None
    state_flags: str | None
    update_result: str | None

    @classmethod
    def read(cls, path: Path) -> "SteamManifest":
        text = path.read_text(errors="replace")
        return cls(
            path=path,
            buildid=_read_value(text, "buildid"),
            target_buildid=_read_value(text, "TargetBuildID"),
            state_flags=_read_value(text, "StateFlags"),
            update_result=_read_value(text, "UpdateResult"),
        )

    @property
    def is_ready(self) -> bool:
        return bool(
            self.buildid
            and self.target_buildid
            and self.buildid != "0"
            and self.target_buildid != "0"
            and self.buildid == self.target_buildid
            and self.update_result in (None, "0")
        )

    @property
    def needs_repair(self) -> bool:
        if not self.buildid or not self.target_buildid:
            return False
        if self.buildid == "0" and self.target_buildid != "0":
            return False
        return self.buildid != self.target_buildid


def _read_value(text: str, key: str) -> str | None:
    match = re.search(rf'"{re.escape(key)}"\s+"([^"]*)"', text)
    return match.group(1) if match else None
