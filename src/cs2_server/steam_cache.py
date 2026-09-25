from __future__ import annotations

import fcntl
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .manifest import SteamManifest


@dataclass(frozen=True)
class SteamCachePlan:
    action: str
    reason: str


@dataclass(frozen=True)
class SteamCache:
    cs2_root: Path
    cache_root: Path | None

    @property
    def server_manifest_path(self) -> Path:
        return self.cs2_root / "steamapps" / "appmanifest_730.acf"

    @property
    def cache_manifest_path(self) -> Path | None:
        if self.cache_root is None:
            return None
        return self.cache_root / "steamapps" / "appmanifest_730.acf"

    def plan_seed(self) -> SteamCachePlan:
        if self.cache_root is None:
            return SteamCachePlan(action="disabled", reason="cache_root_unset")
        if not self.cache_manifest_path or not self.cache_manifest_path.exists():
            return SteamCachePlan(action="skipped", reason="cache_manifest_missing")
        cache_manifest = SteamManifest.read(self.cache_manifest_path)
        if not cache_manifest.is_ready:
            return SteamCachePlan(action="skipped", reason="cache_not_ready")
        if self.server_manifest_path.exists() and SteamManifest.read(self.server_manifest_path).is_ready:
            return SteamCachePlan(action="skipped", reason="server_already_ready")
        return SteamCachePlan(action="seed", reason="server_missing_or_not_ready")

    def seed_from_cache_if_available(self) -> SteamCachePlan:
        plan = self.plan_seed()
        if plan.action != "seed" or self.cache_root is None:
            return plan
        with self._lock():
            plan = self.plan_seed()
            if plan.action != "seed":
                return plan
            self.cs2_root.mkdir(parents=True, exist_ok=True)
            _rsync_tree(self.cache_root, self.cs2_root)
            return SteamCachePlan(action="seeded", reason=plan.reason)

    def sync_to_cache_if_needed(self) -> SteamCachePlan:
        if self.cache_root is None:
            return SteamCachePlan(action="disabled", reason="cache_root_unset")
        if not self.server_manifest_path.exists():
            return SteamCachePlan(action="skipped", reason="server_manifest_missing")
        server_manifest = SteamManifest.read(self.server_manifest_path)
        if not server_manifest.is_ready:
            return SteamCachePlan(action="skipped", reason="server_not_ready")

        with self._lock():
            self.cache_root.mkdir(parents=True, exist_ok=True)
            cache_manifest_path = self.cache_manifest_path
            if cache_manifest_path and cache_manifest_path.exists():
                cache_manifest = SteamManifest.read(cache_manifest_path)
                if cache_manifest.is_ready and cache_manifest.buildid == server_manifest.buildid:
                    return SteamCachePlan(action="skipped", reason="cache_current")
                reason = "cache_different_build"
            else:
                reason = "cache_missing_or_not_ready"

            _rsync_tree(self.cs2_root, self.cache_root)
            return SteamCachePlan(action="synced", reason=reason)

    @contextmanager
    def _lock(self) -> Iterator[None]:
        if self.cache_root is None:
            yield
            return
        lock_dir = self.cache_root.parent
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_path = lock_dir / ".cs2-cache.lock"
        with lock_path.open("w") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _rsync_tree(source: Path, target: Path) -> None:
    source = source.resolve()
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    if shutil.which("rsync"):
        subprocess.run(
            [
                "rsync",
                "-a",
                "--delete",
                f"{source}/",
                f"{target}/",
            ],
            check=True,
        )
        return
    _copy_tree_with_delete(source, target)


def _copy_tree_with_delete(source: Path, target: Path) -> None:
    source_names = {child.name for child in source.iterdir()}
    for child in target.iterdir():
        if child.name not in source_names:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    for child in source.iterdir():
        destination = target / child.name
        if child.is_dir():
            destination.mkdir(exist_ok=True)
            _copy_tree_with_delete(child, destination)
        else:
            shutil.copy2(child, destination)
