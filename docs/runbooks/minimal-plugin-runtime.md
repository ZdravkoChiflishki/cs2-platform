# Minimal Plugin Runtime

This layer makes MetaMod:Source and CounterStrikeSharp available in the image without loading them on the live server by default.

## Runtime artifacts in image

Pinned downloads in `image/Dockerfile`:

```text
MetaMod:Source 2.0.0-git1467 linux
CounterStrikeSharp v1.0.375 with runtime linux
```

Both archives are SHA256-verified during image build.

They are extracted to:

```text
/opt/cs2-platform/plugin-runtime
```

## Runtime activation

Plugin runtime is disabled unless this env var is set on a server Deployment:

```text
ENABLE_PLUGIN_RUNTIME=true
```

Optional source override:

```text
PLUGIN_RUNTIME_ROOT=/opt/cs2-platform/plugin-runtime
```

When enabled, the Python entrypoint copies the runtime tree into:

```text
/home/steam/cs2/game/csgo
```

Expected copied paths include:

```text
addons/metamod_x64.vdf
addons/metamod/
addons/counterstrikesharp/
```

## Current live policy

The live staging server currently leaves `ENABLE_PLUGIN_RUNTIME` unset. This keeps All Weapons DM plugin-free while the runtime layer is built and tested in the image.

Next live gate before enabling:

1. Enable runtime with no extra community plugin.
2. Verify server starts, Steam/GC connects, pod restarts stay zero.
3. Verify logs show MetaMod/CSSSharp loaded without .NET/ICU errors.
4. Human connect/disconnect test.
5. Only then add one small admin/RCON plugin candidate.

## Rollback

Unset `ENABLE_PLUGIN_RUNTIME` and redeploy. The entrypoint will stop copying MetaMod/CSSSharp into the server PVC on future starts. If files already copied need removal, use a Git-backed cleanup step or targeted maintenance command; do not hand-edit a running pod as the durable fix.