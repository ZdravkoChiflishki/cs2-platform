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

## Update checker

`cs2-update-checker` polls Valve `UpToDateCheck` every 15 minutes. It owns the mutable `cs2-version-tracker` ConfigMap; do not add that tracker as a GitOps-managed ConfigMap because Argo self-heal would reset the handled version.

The checker patches the tracker only after rollout plus appmanifest verification succeeds:

```text
buildid == TargetBuildID
buildid != 0
TargetBuildID != 0
StateFlags == 4
UpdateResult == 0
```

Manual health probe:

```bash
JOB=cs2-update-checker-manual-$(date +%s)
kubectl -n cs2-servers create job --from=cronjob/cs2-update-checker "$JOB"
kubectl -n cs2-servers wait --for=condition=complete "job/$JOB" --timeout=240s
kubectl -n cs2-servers logs "job/$JOB" --all-containers=true
```

Healthy no-op output should include `already handled and manifest is ready` and must not restart the pod.

## Deploy workflow

Normal development flow is Git plus Argo Workflows, not local Docker push:

```bash
git commit
git push origin main
kubectl -n argo-workflows create -f - <<'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: cs2-platform-build-deploy-
  namespace: argo-workflows
spec:
  workflowTemplateRef:
    name: cs2-platform-build-deploy
  arguments:
    parameters:
      - name: dry-run
        value: "false"
EOF
```

The workflow builds `zizobg/cs2-server`, pushes the image, commits the pinned digest to `homelab-gitops`, and ArgoCD deploys `Application/cs2-platform`.

## Crash triage

1. Check pod restart count.
2. Read previous container logs.
3. Check final `ClientPutInServer`, plugin, or map messages.
4. Disable only one suspect plugin/profile at a time.
5. Keep production rollback to previous image digest and config commit.

Detailed runbooks:

- `docs/runbooks/production-rollout.md`
- `docs/runbooks/add-server.md`
- `docs/runbooks/server-generator.md`
- `docs/runbooks/download-cache.md`
- `docs/runbooks/plugin-manifest.md`
- `docs/runbooks/minimal-plugin-runtime.md`
- `docs/runbooks/crash-loop.md`
- `docs/runbooks/plugin-upgrade.md`

## Final image contents

The runtime image intentionally copies only:

```text
pyproject.toml
README.md
src/
configs/
image/entrypoint.sh
image/scripts/
```

Repository tests remain in Git for development and CI, but they are not copied into the production image.
