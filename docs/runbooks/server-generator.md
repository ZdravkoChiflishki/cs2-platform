# Server Generator

The generator creates Kubernetes manifests from a declarative server profile plus a mode profile.

It is the preferred path for adding new servers instead of hand-copying YAML.

## Profile fields

```yaml
server_id: retake-01
namespace: cs2-servers
mode: retake
display_name: ZIZO.GG Retake 01
map: de_mirage
port: 26002
public_address: zizogaming.duckdns.org:26002
node: k0s-slave5
image: zizobg/cs2-server@sha256:<digest>
pvc_size: 120Gi
cache_root: null
cpu_request: 1000m
cpu_limit: 4000m
memory_request: 2Gi
memory_limit: 8Gi
steam_update_policy: always
plugin_runtime_enabled: true
admin_steam_ids:
  - "76561199127257988"
admin_flags:
  - "@css/rcon"
  - "@css/root"
```

Mode-derived fields come from `configs/modes/<mode>/mode.yaml`:

```text
EXEC
MAXPLAYERS
GAME_TYPE
GAME_MODE
MAP_GROUP
CS2_DISABLED_PLUGINS from plugins.disabledRuntime
```

Server-profile hardening fields render to:

```text
STEAM_UPDATE_POLICY
ENABLE_PLUGIN_RUNTIME
CS2_ADMIN_STEAM_IDS
CS2_ADMIN_FLAGS
```

## Generate manifests

```bash
PYTHONPATH=src python -m cs2_tools.server_generator profiles/servers/retake-01.yaml --out-dir /tmp/retake-01
```

The command writes:

```text
<server-id>-configmap.yaml
<server-id>-pvc.yaml
<server-id>-deployment.yaml
<server-id>-service.yaml
```

## Validation

Before committing generated manifests, validate the profile itself:

```bash
PYTHONPATH=src python -m cs2_tools.server_generator profiles/servers/retake-01.yaml --validate-only
```

This fails if the profile uses unsafe identifiers, an unpinned image tag, a mismatched `public_address` port, an out-of-range game port, or a relative `cache_root`.

Then validate rendered Kubernetes:

```bash
kubectl apply --dry-run=server -f /tmp/retake-01
```

Then add them to the target `kustomization.yaml` and run:

```bash
kubectl kustomize k8s >/tmp/cs2-platform-rendered.yaml
kubectl apply --dry-run=server -f /tmp/cs2-platform-rendered.yaml
```

## Runtime plugin containment

When a plugin dependency becomes unsafe on the current CS2/CounterStrikeSharp build, do not hand-edit the live pod. Declare the containment in the mode profile:

```yaml
plugins:
  enabled:
    - cs2rcon
  disabledRuntime:
    - CS2-SimpleAdmin
    - CS2-CustomVotes
    - GameModeManager
    - MenuManagerAPI
    - MenuManagerCore
    - PlayerSettings
```

The generator and production checks should keep the Deployment env in sync:

```text
CS2_DISABLED_PLUGINS=CS2-SimpleAdmin,CS2-CustomVotes,GameModeManager,MenuManagerAPI,MenuManagerCore,PlayerSettings
```

At runtime the Python entrypoint copies the pinned plugin bundle, then removes these plugin folders from `addons/counterstrikesharp/plugins/`. Verify the result before promotion:

```bash
kubectl -n cs2-servers exec deploy/staging-mirage-multicfg-01 -- \
  bash -lc 'find /home/steam/cs2/game/csgo/addons/counterstrikesharp/plugins -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort'
PYTHONPATH=src python -m cs2_tools.smoke
```

Expected for the contained All Weapons DM baseline:

```text
CS2Rcon
no_fatal_logs: none
```

## Cache field

`cache_root` is optional. Leave it `null` unless the node has enough local disk for both the per-server PVC and the node cache PVC.

When set, the generator adds:

```text
CS2_CACHE_ROOT=<cache_root>
cs2-cache volume mount
cs2-node-cache-<node suffix> PVC reference
```

The cache PVC itself is intentionally a separate template so enabling it remains a deliberate storage decision.