# CS2 Platform

Python-first CS2 server platform for running small, scalable, PRACC-like servers on Kubernetes.

## MVP scope

- Fresh minimal CS2 runtime image.
- Python startup application instead of a large shell entrypoint.
- One pod = one CS2 server instance.
- First server mode: `multicfg` on `de_mirage`.
- Second mode profile: `all-weapons-dm` as a plugin-free Valve Deathmatch baseline, not deployed until the first server soak is accepted.
- GitOps/Kubernetes-ready manifests.
- Explicit plugin policy: no ranks, skins, GameCMS, DiscordStatus, or large global plugin stacks by default.

## Runtime entrypoint

The container runs:

```bash
python -m cs2_server
```

The Python runtime:

1. loads environment/config
2. validates required secrets
3. applies base + mode + server overlays
4. builds a deterministic CS2 launch command
5. starts CS2 as a child process
6. logs structured JSON lifecycle events

## Local validation

```bash
pytest -q
PYTHONPATH=src python -m cs2_tools.validate_mode configs/modes/multicfg/mode.yaml
PYTHONPATH=src python -m cs2_tools.query_server 192.168.0.8:26001
PYTHONPATH=src python -m cs2_tools.smoke
kubectl kustomize k8s >/tmp/cs2-platform.yaml
```
