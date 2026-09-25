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
```

Mode-derived fields come from `configs/modes/<mode>/mode.yaml`:

```text
EXEC
MAXPLAYERS
GAME_TYPE
GAME_MODE
MAP_GROUP
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

Before committing generated manifests:

```bash
kubectl apply --dry-run=server -f /tmp/retake-01
```

Then add them to the target `kustomization.yaml` and run:

```bash
kubectl kustomize k8s >/tmp/cs2-platform-rendered.yaml
kubectl apply --dry-run=server -f /tmp/cs2-platform-rendered.yaml
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