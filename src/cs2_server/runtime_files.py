from __future__ import annotations

import shutil
from pathlib import Path


def prepare_steamclient_libraries(steamcmd_root: Path = Path("/opt/steamcmd"), home: Path = Path.home()) -> int:
    """Install SteamCMD steamclient.so files where CS2 expects them."""
    copies = [
        (steamcmd_root / "linux64" / "steamclient.so", home / ".steam" / "sdk64" / "steamclient.so"),
        (steamcmd_root / "linux32" / "steamclient.so", home / ".steam" / "sdk32" / "steamclient.so"),
    ]
    copied = 0
    for source, target in copies:
        if not source.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    return copied


def prepare_server_libraries(cs2_root: Path) -> int:
    """Copy CS2 engine shared libraries where libserver.so expects them.

    Valve's dedicated server can leave libraries such as libv8.so under
    game/bin/linuxsteamrt64 while libserver.so is loaded from
    game/csgo/bin/linuxsteamrt64. The legacy startup script copied these .so
    files before launch; keep that behavior explicitly in Python.
    """
    source = cs2_root / "game" / "bin" / "linuxsteamrt64"
    target = cs2_root / "game" / "csgo" / "bin" / "linuxsteamrt64"
    if not source.exists():
        return 0
    target.mkdir(parents=True, exist_ok=True)
    copied = 0
    for library in sorted(source.glob("*.so")):
        shutil.copy2(library, target / library.name)
        copied += 1
    return copied
