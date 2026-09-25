# CS2 Download Cache

## Purpose

Avoid a full SteamCMD download for every new server PVC on the same Kubernetes node.

Current implementation is node-local and simple:

```text
per-server PVC: /home/steam/cs2
node cache PVC: /cache/cs2
lock file: /cache/.cs2-cache.lock
```

When `CS2_CACHE_ROOT=/cache/cs2` is set, startup does this before launching CS2:

1. If the server PVC is missing/not ready and the cache has a ready Steam manifest, rsync cache -> server PVC.
2. Run the normal Steam update/repair logic on the server PVC.
3. If the server PVC is ready and the cache is missing/stale, rsync server PVC -> cache.
4. Continue with Steam client/runtime library prep and launch.

The lock serializes cache writes so multiple server pods on the same node do not update the cache at the same time.

## Current homelab staging cache

```text
node: k0s-slave5
PVC: cs2-node-cache-slave5
mount: /cache/cs2
size: 120Gi
server using it: staging-mirage-multicfg-01
```

## Behavior

First server on a node:

```text
cache empty -> server SteamCMD update/download -> server copies ready install into cache
```

Next server on the same node:

```text
cache ready -> rsync cache into new server PVC -> SteamCMD verifies small delta -> launch
```

This is intentionally not shared over NFS and does not make multiple pods write the same CS2 install directory. Each live server still gets its own writable game PVC.

## Verification

Check runtime logs:

```bash
kubectl -n cs2-servers logs deploy/staging-mirage-multicfg-01 --tail=200 \
  | grep -E 'steam_cache_(seed|sync)_checked|steam_update_checked'
```

Expected examples:

```text
steam_cache_seed_checked action=skipped reason=cache_manifest_missing
steam_cache_sync_checked action=synced reason=cache_missing_or_not_ready
```

or after cache is warm:

```text
steam_cache_seed_checked action=skipped reason=server_already_ready
steam_cache_sync_checked action=skipped reason=cache_current
```

Check cache manifest:

```bash
kubectl -n cs2-servers exec deploy/staging-mirage-multicfg-01 -- \
  bash -lc 'grep -E "buildid|TargetBuildID|UpdateResult" /cache/cs2/steamapps/appmanifest_730.acf'
```

## Limits

- The first cache warm-up may take time because it copies the existing CS2 install into the cache PVC.
- A cache PVC is node-local. A server scheduled to another node needs that node's cache PVC or a future cache seeding job.
- The cache is an optimization only. If it is empty or stale, the server still falls back to SteamCMD update on its own PVC.