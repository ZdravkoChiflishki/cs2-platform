# Add Server Runbook

## Purpose

Create another CS2 server instance from an existing mode profile.

Current constraint: until node-local download cache exists, a new server normally means a new per-server PVC and another large CS2 install. Prefer switching/testing the existing staging server unless the new instance is truly needed.

## Required fields

Each server must define:

```text
server id
mode
map
port
max players
hostname/display name
public address
PVC name
node selector
image digest
```

## Port rules

- use one TCP and one UDP port with the same external port
- avoid collisions with existing services
- recommended staging allocation starts at `26001`

Check existing ports:

```bash
kubectl -n cs2-servers get svc -o wide
```

## Create manifests

For now, copy the staging manifest set and edit the copied server id/port/PVC:

```text
k8s/servers/<server-id>-deployment.yaml
k8s/servers/<server-id>-service.yaml
k8s/servers/<server-id>-pvc.yaml
k8s/servers/<server-id>-configmap.yaml
```

Also add all new files to:

```text
k8s/kustomization.yaml
```

## Mode-specific env

### Multi-CFG

```text
CS2_MODE=multicfg
EXEC=multicfg.cfg
GAME_TYPE=0
GAME_MODE=0
MAP_GROUP=mg_active
MAXPLAYERS=24
```

### All Weapons DM

```text
CS2_MODE=all-weapons-dm
EXEC=all-weapons-dm.cfg
GAME_TYPE=1
GAME_MODE=2
MAP_GROUP=mg_active
MAXPLAYERS=24
```

### Retake

```text
CS2_MODE=retake
EXEC=retake.cfg
GAME_TYPE=0
GAME_MODE=0
MAP_GROUP=mg_active
MAXPLAYERS=10
```

## Validate

```bash
kubectl kustomize k8s >/tmp/cs2-platform-rendered.yaml
kubectl apply --dry-run=client -f /tmp/cs2-platform-rendered.yaml
```

If the manifests are copied into `homelab-gitops`, run server dry-run there too:

```bash
kubectl kustomize gitops/apps/cs2-platform/k8s >/tmp/cs2-platform-gitops.yaml
kubectl apply --dry-run=server -f /tmp/cs2-platform-gitops.yaml
```

## Deploy

Commit/push `cs2-platform`, then update/copy manifests into `homelab-gitops`, commit/push, refresh ArgoCD, and wait for rollout.

## Acceptance

- LoadBalancer has the expected external IP/port
- `PYTHONPATH=src python -m cs2_tools.query_server <ip:port>` returns `online=true`
- expected max players are reported
- bots are expected count
- pod restart count stays zero
- human connect/disconnect succeeds