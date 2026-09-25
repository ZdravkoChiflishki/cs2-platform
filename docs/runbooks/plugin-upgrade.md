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

## Verification

```bash
PYTHONPATH=src python -m cs2_tools.smoke
kubectl -n cs2-servers logs deploy/staging-mirage-multicfg-01 --tail=500 | grep -Ei 'exception|fatal|segmentation|plugin|counterstrikesharp'
```

Plugin-specific verification should be written in the mode docs before promotion.

## Rollback

Remove the plugin load from the mode config and redeploy. If the crash continues, roll back the image digest too.

Do not debug by copying DLLs into a live pod; changes must be Git-backed and repeatable.