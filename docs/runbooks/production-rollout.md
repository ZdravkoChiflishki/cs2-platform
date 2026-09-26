# Production Rollout Runbook

## Scope

Promote one CS2 server profile from staging to a production/live listing after it passes smoke and manual gameplay checks.

## Gate 1: source validation

Run from `cs2-platform`:

```bash
pytest -q
PYTHONPATH=src python -m cs2_tools.validate_mode \
  configs/modes/multicfg/mode.yaml \
  configs/modes/all-weapons-dm/mode.yaml \
  configs/modes/retake/mode.yaml
PYTHONPATH=src python -m cs2_tools.plugin_manifest plugins/plugins.yaml
PYTHONPATH=src python -m cs2_tools.server_generator profiles/servers/retake-01.yaml --validate-only
PYTHONPATH=src python -m cs2_tools.production_check
```

Expected:

```text
all tests passed
all mode files report ok
```

## Gate 2: build/deploy through Argo

Commit and push source changes:

```bash
git status --short
git add <changed-files>
git commit -m "type: clear message"
git push origin main
```

Submit the in-cluster image workflow:

```bash
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

Wait for success:

```bash
kubectl -n argo-workflows get workflows --sort-by=.metadata.creationTimestamp
```

Expected:

```text
latest cs2-platform-build-deploy-* is Succeeded
homelab-gitops receives a pinned image digest commit
```

## Gate 3: ArgoCD health

```bash
kubectl -n argocd annotate application cs2-platform argocd.argoproj.io/refresh=hard --overwrite
kubectl -n argocd get application cs2-platform
kubectl -n cs2-servers rollout status deploy/staging-mirage-multicfg-01 --timeout=300s
```

Expected:

```text
cs2-platform Synced Healthy
rollout successful
```

## Gate 4: smoke check

```bash
PYTHONPATH=src python -m cs2_tools.smoke \
  --expected-name-contains "All Weapons DM" \
  --expected-map de_mirage \
  --expected-max-players 24 \
  --expected-bots 0
```

Expected:

```text
ok: true
max_players: expected value
bots: expected value
pod_restarts: 0
no_fatal_logs: none
```

## Gate 5: updater health check

The update checker must not mark a Valve `required_version` handled until the live Steam appmanifest is healthy.

```bash
JOB=cs2-update-checker-manual-$(date +%s)
BEFORE_UID=$(kubectl -n cs2-servers get pod -l zizo.gg/server-id=staging-mirage-multicfg-01 -o jsonpath='{.items[0].metadata.uid}')
kubectl -n cs2-servers create job --from=cronjob/cs2-update-checker "$JOB"
kubectl -n cs2-servers wait --for=condition=complete "job/$JOB" --timeout=240s
kubectl -n cs2-servers logs "job/$JOB" --all-containers=true
AFTER_UID=$(kubectl -n cs2-servers get pod -l zizo.gg/server-id=staging-mirage-multicfg-01 -o jsonpath='{.items[0].metadata.uid}')
test "$BEFORE_UID" = "$AFTER_UID"
```

Expected on a healthy, already-current server:

```text
already handled and manifest is ready: <buildid>:<TargetBuildID>:4:0
pod UID unchanged
```

## Gate 6: manual gameplay check

For every mode promoted, a human should test:

- connect from LAN with `connect 192.168.0.8:26001`
- join a team
- shoot/buy/respawn behavior matches the mode
- disconnect and reconnect
- RCON command works on the game port
- pod remains `restarts=0`

## Rollback

Rollback is GitOps-first:

1. Find the previous good image digest in `homelab-gitops` history.
2. Revert the GitOps digest commit or restore the previous image line.
3. Push `homelab-gitops`.
4. Force ArgoCD refresh/sync.
5. Run smoke check.

Do not delete the game data PVC during rollback unless the Steam install itself is corrupted.