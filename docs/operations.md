# Operations

## First staging target

```text
server id: staging-mirage-multicfg-01
mode: multicfg
map: de_mirage
slots: 24
port: 26001
namespace: cs2-servers
```

## Startup validation

The Python entrypoint fails early if required secrets are missing:

- `RCON_PASSWORD`
- `STEAM_ACCOUNT`
- `API_KEY`

## Steam data strategy

MVP uses a per-server `local-path` PVC. The PVC should not be deleted during normal deployments, avoiding repeated 70GB downloads.

Phase 2 should introduce a node-local CS2 cache and updater Job per node.

## Crash triage

1. Check pod restart count.
2. Read previous container logs.
3. Check final `ClientPutInServer`, plugin, or map messages.
4. Disable only one suspect plugin/profile at a time.
5. Keep production rollback to previous image digest and config commit.
