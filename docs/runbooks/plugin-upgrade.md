# Plugin Upgrade Runbook

## Policy

Default platform policy is no heavy global plugin stack.

Do not add these to base/default startup:

```text
Ranks
Inventory/skins
DiscordStatus
GameCMS
legacy Deathmatch mega-plugin stack
multiple menu/vote systems
experimental movement/native plugins
```

A plugin must belong to exactly one mode or one clearly named platform feature.

## Before adding a plugin

Answer:

1. Which mode needs it?
2. What problem does it solve that config/RCON cannot solve?
3. Does it hook player connect/spawn/team changes?
4. Is rollback just removing the plugin from that mode?
5. What is the pinned release/hash?

## Staging process

1. Add plugin binary/metadata to a manifest/lock file once plugin management exists.
2. Load it only from the target mode config.
3. Run source validation.
4. Deploy through Argo.
5. Test one human connect/disconnect.
6. Test the plugin feature.
7. Watch pod restart count and logs.

## Containment for broken dependency stacks

If smoke/logs show CounterStrikeSharp callback spam such as:

```text
(cssharp:Core) Error invoking callback
Schema target points to null
MenuManagerAPI.Core.PlayerInfo.OnTick
```

then treat the affected dependency stack as unsafe for this CS2/CSS build. First check upstream releases, then contain through the mode profile instead of live-pod deletion:

1. Add the affected folder names to `plugins.disabledRuntime` in the mode profile.
2. Ensure the rendered Deployment has matching `CS2_DISABLED_PLUGINS`.
3. Deploy through the normal Argo/GitOps path.
4. Verify `PYTHONPATH=src python -m cs2_tools.smoke` reports `no_fatal_logs: none`.
5. Verify the live plugin folders and `css_plugins list` show only the intended plugin set.

For the current All Weapons DM containment baseline, only `CS2Rcon` should remain loaded until MenuManagerAPI/GameModeManager compatibility is fixed.

## Verification

```bash
PYTHONPATH=src python -m cs2_tools.smoke
kubectl -n cs2-servers logs deploy/staging-mirage-multicfg-01 --tail=500 | grep -Ei 'exception|fatal|segmentation|plugin|counterstrikesharp'
```

Plugin-specific verification should be written in the mode docs before promotion.

## Rollback

Remove the plugin load from the mode config and redeploy. If the crash continues, roll back the image digest too.

Do not debug by copying DLLs into a live pod; changes must be Git-backed and repeatable.